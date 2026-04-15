"""
Streamlit UI for Chickenizer.

Run:
  python -m streamlit run .src/ui/streamlit_app.py
"""

from __future__ import annotations

from dataclasses import dataclass
import html
import inspect
import json
import os
import signal
from pathlib import Path
import sys
import time
import traceback
from typing import Any, Dict, List, Tuple, Type

import streamlit as st
import streamlit.components.v1 as components


# Ensure the repo's ".src" directory is importable when Streamlit executes this file.
DOT_SRC = Path(__file__).resolve().parents[1]
if str(DOT_SRC) not in sys.path:
    sys.path.insert(0, str(DOT_SRC))

from engine import GameEngine  # type: ignore  # noqa: E402
from ql_strategy import QLearningStrategy  # type: ignore  # noqa: E402
from train_ql import OPPONENT_CHOICES, train_ql_agent  # type: ignore  # noqa: E402
from strategies import (  # type: ignore  # noqa: E402
    Strategy,
    AlwaysStayStrategy,
    AlwaysSwerveStrategy,
    TitForTatStrategy,
    RandomStrategy,
    HPThresholdStrategy,
    AggressiveStrategy,
    DefensiveStrategy,
    MinimaxStrategy,
    merge_strategy_preferences,
)

PREFERENCE_KEYS: Tuple[str, ...] = ("round_win", "round_loss", "tie", "crash", "hp_delta")


@dataclass(frozen=True)
class StrategyChoice:
    label: str
    cls: Type[Strategy]


STRATEGIES: List[StrategyChoice] = [
    StrategyChoice("Always Stay", AlwaysStayStrategy),
    StrategyChoice("Always Swerve", AlwaysSwerveStrategy),
    StrategyChoice("Tit For Tat", TitForTatStrategy),
    StrategyChoice("Random", RandomStrategy),
    StrategyChoice("HP Threshold", HPThresholdStrategy),
    StrategyChoice("Aggressive (HP)", AggressiveStrategy),
    StrategyChoice("Defensive (HP)", DefensiveStrategy),
    StrategyChoice("Minimax (resilience diff)", MinimaxStrategy),
]


def _strategy_class_doc(cls: Type[Strategy]) -> str:
    """Return the class docstring for UI tooltips (matches in-code documentation)."""
    doc = inspect.getdoc(cls)
    if doc and doc.strip():
        return doc.strip()
    return "No description available."


def _html_title_attr(text: str, max_len: int = 1800) -> str:
    """Escape text for use in an HTML ``title`` / ``abbr`` attribute."""
    stripped = text.strip()
    if len(stripped) > max_len:
        stripped = stripped[: max_len - 1] + "…"
    return html.escape(stripped, quote=True).replace("\n", "&#10;")


def _strategy_doc_hint(choice: StrategyChoice) -> None:
    """Small hover hint for the strategy currently selected in the adjacent selectbox."""
    title = _html_title_attr(_strategy_class_doc(choice.cls))
    st.markdown(
        f'<p style="font-size:0.78rem;color:#9a9a9a;margin:-0.35rem 0 0.5rem 0;">'
        f'<abbr title="{title}" style="cursor:help;text-decoration:underline dotted;text-underline-offset:2px;">'
        "ℹ️ Strategy description (hover)"
        "</abbr></p>",
        unsafe_allow_html=True,
    )


def _strategy_reference_expander() -> None:
    """List every strategy with a native browser tooltip (class docstring)."""
    with st.expander("All strategies — hover a name for its description", expanded=False):
        items: List[str] = []
        for sc in STRATEGIES:
            t = _html_title_attr(_strategy_class_doc(sc.cls))
            label = html.escape(sc.label)
            items.append(
                f'<li style="margin:0.3rem 0"><abbr title="{t}" style="cursor:help">{label}</abbr></li>'
            )
        st.markdown(
            "<ul style='list-style:none;padding-left:0;margin:0'>" + "".join(items) + "</ul>",
            unsafe_allow_html=True,
        )


def _strategy_params_ui(label_prefix: str, choice: StrategyChoice) -> Dict[str, Any]:
    """
    Creates UI for strategy parameters.

    Args:
        label_prefix: Prefix for the label.
        choice: The strategy choice.

    Returns:
        A dictionary of parameters for given strategy.
    """
    cls = choice.cls
    params: Dict[str, Any] = {}

    # Establish Seed param UI
    if cls is RandomStrategy:
        use_seed = st.checkbox(f"{label_prefix} use seed", value=False, key=f"{label_prefix}_random_use_seed")
        seed = (
            int(
                st.number_input(
                    f"{label_prefix} seed (optional)",
                    min_value=0,
                    value=0,
                    step=1,
                    key=f"{label_prefix}_random_seed",
                )
            )
            if use_seed
            else 0
        )
        params["seed"] = int(seed) if use_seed else None

    # Establish HP Threshold param UI
    if cls is HPThresholdStrategy:
        use_custom = st.checkbox(f"{label_prefix} custom HP threshold", value=False, key=f"{label_prefix}_hp_use_custom")
        params["threshold"] = (
            int(st.number_input(f"{label_prefix} HP threshold", min_value=0, value=20, step=1, key=f"{label_prefix}_hp_threshold"))
            if use_custom
            else None
        )

    # Establish Minimax depth param UI
    if cls is MinimaxStrategy:
        params["depth"] = int(
            st.slider(f"{label_prefix} minimax depth (rounds)", min_value=1, max_value=6, value=2, step=1, key=f"{label_prefix}_minimax_depth")
        )
    return params


def _preferences_ui(player: str, base: Dict[str, int]) -> Dict[str, int]:
    """
    Creates UI for player preferences.
    Args:
        player: The player identifier.
        base: The base preferences.

    Returns:
        A dictionary of preferences.
    """
    st.caption(f'{player}\'s preference cares.')
    prefs: Dict[str, int] = {}
    cols = st.columns(5)
    for i, key in enumerate(PREFERENCE_KEYS):
        with cols[i]:
            prefs[key] = int(st.number_input(f"{player} {key}", value=int(base.get(key, 0)), step=1, key=f"{player}_pref_{key}"))
    return prefs


def _build_strategy(choice: StrategyChoice, player: str, params: Dict[str, Any]) -> Strategy:
    """Builds a strategy from a choice and parameters.
    Args:
        choice: The strategy choice.
        player: The player identifier.
        params: The parameters for the strategy.

    Returns:
        A strategy.
    """
    return choice.cls(player, **params)


def _init_match(
    p1_choice: StrategyChoice,
    p2_choice: StrategyChoice,
    p1_params: Dict[str, Any],
    p2_params: Dict[str, Any],
    p1_prefs: Dict[str, int],
    p2_prefs: Dict[str, int],
    max_rounds: int,
) -> None:
    """Initializes a match.
    
    Args:
        p1_choice/p2_choice: The strategy choice for each player.
        p1_params/p2_params: The parameters for the strategy for each player.
        p1_prefs/p2_prefs: The preferences for the player for each player.
        max_rounds: The maximum number of rounds to play.
    """
    p1_strategy = _build_strategy(p1_choice, "p1", p1_params)
    p2_strategy = _build_strategy(p2_choice, "p2", p2_params)

    base = GameEngine().get_gamestate()
    enriched = merge_strategy_preferences(base, p1_strategy, p2_strategy)
    enriched["p1_preferences"] = dict(p1_prefs)
    enriched["p2_preferences"] = dict(p2_prefs)

    engine = GameEngine(gamestate=enriched)
    st.session_state["engine"] = engine
    st.session_state["p1_strategy"] = p1_strategy
    st.session_state["p2_strategy"] = p2_strategy
    st.session_state["max_rounds"] = max_rounds
    st.session_state["game_over"] = False
    st.session_state["game_over_reason"] = None
    st.session_state["last_round"] = {"p1_action": None, "p2_action": None, "outcome": None}
    st.session_state["initialized"] = True
    st.session_state["shutdown_requested"] = False
    # for use in animation, to allow repeat actions to be animated properly
    st.session_state["arena_action_nonce"] = 0


def _advance_one_round() -> None:
    """Advances the match by one round."""
    if not st.session_state.get("initialized"):
        return
    if st.session_state.get("game_over"):
        return

    engine: GameEngine = st.session_state["engine"]
    p1_strategy: Strategy = st.session_state["p1_strategy"]
    p2_strategy: Strategy = st.session_state["p2_strategy"]
    max_rounds = int(st.session_state["max_rounds"])

    # max round cond
    if engine.get_gamestate().get("round", 0) >= max_rounds:
        st.session_state["game_over"] = True
        st.session_state["game_over_reason"] = "max_rounds_reached"
        return

    current = engine.generate_gamestate(increment_round=False)
    p1_action = p1_strategy(current)
    engine.play_action("p1", p1_action)

    current = engine.generate_gamestate(increment_round=False)
    p2_action = p2_strategy(current)
    engine.play_action("p2", p2_action)

    end_state = engine.generate_gamestate(increment_round=True)
    score = end_state.get("score", [])
    outcome = score[-1] if score else None
    # update round state
    st.session_state["last_round"] = {
        "p1_action": "stay" if p1_action else "swerve",
        "p2_action": "stay" if p2_action else "swerve",
        "outcome": outcome,
    }
    st.session_state["arena_action_nonce"] = int(st.session_state.get("arena_action_nonce", 0)) + 1

    # game over cond
    is_over, reason = engine.is_game_over()
    if is_over:
        st.session_state["game_over"] = True
        st.session_state["game_over_reason"] = reason
        return

    # max round cond
    if end_state.get("round", 0) >= max_rounds:
        st.session_state["game_over"] = True
        st.session_state["game_over_reason"] = "max_rounds_reached"
        return

def _round_rows(engine: GameEngine) -> List[Dict[str, Any]]:
    """Creates a list of round rows for the match history interface.
    Args:
        engine: The game engine.

    Returns:
        A list of round rows to be displayed.
    """
    by_round: Dict[int, Dict[str, Any]] = {}
    for state in engine.gamestate_history:
        rnd = int(state.get("round", 0))
        by_round[rnd] = state

    rows: List[Dict[str, Any]] = []
    for round_num in sorted(by_round):
        # skip start round - nothing to display
        if round_num == 0:
            continue
        state = by_round[round_num]
        p1_hist = state.get("p1_action_history", [])
        p2_hist = state.get("p2_action_history", [])
        score = state.get("score", [])
        rows.append(
            {
                "round": round_num,
                "p1_action": p1_hist[-1] if p1_hist else None,
                "p2_action": p2_hist[-1] if p2_hist else None,
                "outcome": score[-1] if score else None,
                "p1_hp": state.get("p1_hp"),
                "p2_hp": state.get("p2_hp"),
                "p1_resilience": state.get("p1_resilience"),
                "p2_resilience": state.get("p2_resilience"),
                "resilience_diff": state.get("resilience_diff"),
            }
        )
    return rows


def _render_match_state(engine: GameEngine, p1_strategy: Strategy, p2_strategy: Strategy, last_round: Dict[str, Any]) -> None:
    """Renders the match state.
    Args:
        engine: The game engine.
        p1_strategy/p2_strategy: The strategies for the players.
        last_round: The last round's action and outcome.
    """
    gs = engine.get_gamestate()
    p1_hp = int(gs.get("p1_hp", 0))
    p2_hp = int(gs.get("p2_hp", 0))
    max_hp = int(GameEngine.DEFAULT_HP)
    round_num = int(gs.get("round", 0))

    # match header display
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current round", round_num)
    c2.metric("P1 HP", p1_hp)
    c3.metric("P2 HP", p2_hp)
    c4.metric("R1-R2", int(gs.get("resilience_diff", 0)))

    # arena display, to be replaced with animation/graphics
    st.subheader("Arena")
    p1_col, mid_col, p2_col = st.columns([3, 2, 3])
    with p1_col:
        st.markdown("### P1")
        st.markdown("🚗")
        st.write(f"Strategy: `{p1_strategy.__class__.__name__}`")
        st.write(f"Last action: `{last_round.get('p1_action') or 'n/a'}`")
        st.progress(max(0.0, min(1.0, p1_hp / max_hp)))
        st.caption(f"HP: {p1_hp}/{max_hp}")
        st.write("Cares:", gs.get("p1_preferences", {}))
    with mid_col:
        st.markdown("### VS")
        st.write("Last round outcome")
        outcome = last_round.get("outcome")
        if outcome is None:
            st.info("No completed rounds yet")
        elif outcome == "CRASH":
            st.error("CRASH")
        elif outcome == "TIE":
            st.warning("TIE")
        else:
            st.success(str(outcome))
    with p2_col:
        st.markdown("### P2")
        st.markdown("🏎️")
        st.write(f"Strategy: `{p2_strategy.__class__.__name__}`")
        st.write(f"Last action: `{last_round.get('p2_action') or 'n/a'}`")
        st.progress(max(0.0, min(1.0, p2_hp / max_hp)))
        st.caption(f"HP: {p2_hp}/{max_hp}")
        st.write("Cares:", gs.get("p2_preferences", {}))

def _render_arena(
    last_round: Dict[str, Any],
    game_over: bool,
    duration_ms: int = 700,
    hold_ms: int = 1200,
    return_ms: int = 350,
    action_nonce: int = 0,
) -> None:
    """Render a simple HTML/CSS animated arena scene."""
    p1_action = last_round.get("p1_action")
    p2_action = last_round.get("p2_action")
    outcome = (last_round.get("outcome") or "").upper()

    nonce_suffix = str(action_nonce)

    flash_class = "flash-crash" if outcome == "CRASH" else ""
    outcome_text = "No completed rounds yet" if not outcome else outcome
    if game_over:
        outcome_text = f"{outcome_text} - GAME OVER"
    delay_ms = duration_ms + hold_ms
    p1_vec = "stay"
    p2_vec = "stay"
    if p1_action == "swerve":
        p1_vec = "swerve"
    if p2_action == "swerve":
        p2_vec = "swerve"
    if outcome == "CRASH":
        p1_vec = "crash"
        p2_vec = "crash"

    arena_html = f"""
    <style>
      .arena {{
        position: relative;
        width: 100%;
        height: 240px;
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #444;
        background:
          linear-gradient(to bottom, #111 0%, #111 48%, #333 48%, #333 52%, #111 52%, #111 100%);
      }}
      .car {{
        position: absolute;
        top: 64px;
        font-size: 64px;
      }}
      .p1 {{ left: 8%; transform: translate(0px, 0px) scaleX(-1); }}
      .p2 {{ right: 8%; transform: translate(0px, 0px); }}
      .outcome {{
        position: absolute;
        left: 50%;
        top: 8px;
        z-index: 2;
        transform: translateX(-50%);
        font-weight: 700;
        font-size: 14px;
        font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
        color: #f5f5f5;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.9);
        background: rgba(0, 0, 0, 0.75);
        border: 1px solid #888;
        border-radius: 999px;
        padding: 6px 14px;
        white-space: nowrap;
      }}
      .flash {{
        position: absolute;
        left: 50%;
        top: 68px;
        transform: translateX(-50%);
        font-size: 44px;
        opacity: 0;
      }}
      .flash-crash {{
        animation: boom {duration_ms}ms ease-in-out 1;
      }}
      @keyframes boom {{
        0% {{ opacity: 0; transform: translateX(-50%) scale(0.2); }}
        40% {{ opacity: 1; transform: translateX(-50%) scale(1.1); }}
        100% {{ opacity: 0; transform: translateX(-50%) scale(1.5); }}
      }}
    </style>

    <div class="arena arena-{action_nonce}" id="arena-{nonce_suffix}">
      <div class="outcome">{outcome_text}</div>
      <div class="car p1" id="p1-{nonce_suffix}">🚗</div>
      <div class="car p2" id="p2-{nonce_suffix}">🏎️</div>
      <div class="flash {flash_class}">💥</div>
    </div>
    <script>
      (() => {{
        const p1 = document.getElementById("p1-{nonce_suffix}");
        const p2 = document.getElementById("p2-{nonce_suffix}");
        const arena = document.getElementById("arena-{nonce_suffix}");
        if (!p1 || !p2 || !arena) return;

        const arenaW = arena.clientWidth;
        const travel = Math.min(arenaW * 0.42, 420);
        const crash = Math.min(arenaW * 0.28, 260);
        const swingY = 34;
        const p1SwerveY = -swingY;
        const p2SwerveY = Math.round(swingY * 1.45);

        const p1Action = "{p1_vec}";
        const p2Action = "{p2_vec}";
        const d1 = p1Action === "crash" ? crash : travel;
        const d2 = p2Action === "crash" ? -crash : -travel;
        const y1 = p1Action === "swerve" ? p1SwerveY : 0;
        const y2 = p2Action === "swerve" ? p2SwerveY : 0;
        const r1 = p1Action === "swerve" ? -12 : (p1Action === "crash" ? -7 : 0);
        const r2 = p2Action === "swerve" ? -12 : (p2Action === "crash" ? 7 : 0);

        const p1End = `translate(${{d1}}px, ${{y1}}px) rotate(${{r1}}deg) scaleX(-1)`;
        const p2End = `translate(${{d2}}px, ${{y2}}px) rotate(${{r2}}deg)`;
        const p1Idle = "translate(0px, 0px) scaleX(-1)";
        const p2Idle = "translate(0px, 0px)";

        p1.animate([{{ transform: p1Idle }}, {{ transform: p1End }}], {{
          duration: {duration_ms},
          easing: "ease-in-out",
          fill: "forwards"
        }});
        p2.animate([{{ transform: p2Idle }}, {{ transform: p2End }}], {{
          duration: {duration_ms},
          easing: "ease-in-out",
          fill: "forwards"
        }});
        setTimeout(() => {{
          p1.animate([{{ transform: p1End }}, {{ transform: p1Idle }}], {{
            duration: {return_ms},
            easing: "ease-in-out",
            fill: "forwards"
          }});
          p2.animate([{{ transform: p2End }}, {{ transform: p2Idle }}], {{
            duration: {return_ms},
            easing: "ease-in-out",
            fill: "forwards"
          }});
        }}, {delay_ms});
      }})();
    </script>
    """
    components.html(arena_html, height=260)


def _close_ui() -> None:
    """Closes the UI, in case of error or shutdown request."""
    # Best-effort: navigate away from Streamlit page first to avoid reconnect UI.
    components.html(
        """
        <script>
            try {
                if (window.top) {
                    window.top.location.replace("about:blank");
                }
            } catch (e) {}
            try {
                window.location.replace("about:blank");
            } catch (e) {}
            try {
                window.open('', '_self');
                window.close();
            } catch (e) {}
        </script>
        """,
        height=0,
    )
    # Give the browser a moment to process navigation/close, then stop server.
    time.sleep(0.7)
    os.kill(os.getpid(), signal.SIGTERM)
    st.stop()


def render_learned_q_table(agent: QLearningStrategy) -> None:
    """Plug-in for Streamlit: show the tabular policy after ``train_ql_agent`` (or any training)."""
    st.subheader("Learned Q-table (RL)")
    st.caption(
        "Each row is a visited state. **q_swerve** / **q_stay** are Q(s, swerve) and Q(s, stay) "
        "(bool actions False / True)."
    )
    st.dataframe(agent.q_table_records(), use_container_width=True, hide_index=True)
    st.download_button(
        label="Download Q-table JSON",
        data=json.dumps(agent.q_table_payload(), indent=2),
        file_name="q_table_payload.json",
        mime="application/json",
        key="download_q_table_json",
    )


def main() -> None:
    st.set_page_config(page_title="Chickenizer Live Match", layout="wide")
    st.title("Chickenizer - Live Match")
    st.write("Run the game one round at a time and watch the players react.")

    with st.sidebar:
        st.header("Match setup")
        max_rounds = int(st.slider("Max rounds", min_value=1, max_value=50, value=10))

        st.subheader("P1 strategy")
        p1_choice = st.selectbox("P1 strategy", options=STRATEGIES, format_func=lambda c: c.label, index=2, key="p1_strategy_choice")
        _strategy_doc_hint(p1_choice)
        p1_params = _strategy_params_ui("P1", p1_choice)

        st.subheader("P2 strategy")
        p2_choice = st.selectbox("P2 strategy", options=STRATEGIES, format_func=lambda c: c.label, index=2, key="p2_strategy_choice")
        _strategy_doc_hint(p2_choice)
        p2_params = _strategy_params_ui("P2", p2_choice)

        _strategy_reference_expander()

        st.subheader("Player preferences (cares)")
        defaults = GameEngine.DEFAULT_GAMESTATE
        p1_prefs = _preferences_ui("p1", defaults.get("p1_preferences", {}))
        p2_prefs = _preferences_ui("p2", defaults.get("p2_preferences", {}))

        animate_arena = st.checkbox("Enable arena animation", value=True, key="animate_arena")
        if animate_arena:
            animation_speed = int(
                st.slider("Animation speed (ms)", min_value=200, max_value=1500, value=700, step=50, key="arena_anim_ms")
            )
            return_hold_ms = int(
                st.slider("Hold at action before reset (ms)", min_value=0, max_value=2500, value=1200, step=100, key="arena_hold_ms")
            )
            return_speed_ms = int(
                st.slider("Return-to-idle speed (ms)", min_value=100, max_value=1200, value=350, step=50, key="arena_return_ms")
            )
        start_new = st.button("Start New Game", type="primary", use_container_width=True)
        step_disabled = bool(
            st.session_state.get("game_over", False)
            or not st.session_state.get("initialized", False)
        )
        step_once = st.button("Play Next Round", use_container_width=True, disabled=step_disabled)

        st.divider()
        # close app section
        st.subheader("App control")
        allow_shutdown = st.checkbox(
            "Please click this checkbox to confirm you're done playing.",
            value=False,
            key="allow_shutdown",
        )
        shutdown_now = st.button("Shutdown App", type="secondary", use_container_width=True)
        if shutdown_now and allow_shutdown:
            st.session_state["shutdown_requested"] = True
            _close_ui()
        elif shutdown_now and not allow_shutdown:
            st.error("Please click the checkbox to confirm you're done playing.")

    if start_new or not st.session_state.get("initialized"):
        _init_match(p1_choice, p2_choice, p1_params, p2_params, p1_prefs, p2_prefs, max_rounds)

    if step_once:
        _advance_one_round()

    engine: GameEngine = st.session_state["engine"]
    p1_strategy: Strategy = st.session_state["p1_strategy"]
    p2_strategy: Strategy = st.session_state["p2_strategy"]
    last_round = st.session_state["last_round"]

    _render_match_state(engine, p1_strategy, p2_strategy, last_round)
    if animate_arena:
        _render_arena(
            last_round=last_round,
            game_over=bool(st.session_state.get("game_over", False)),
            duration_ms=animation_speed,
            hold_ms=return_hold_ms,
            return_ms=return_speed_ms,
            action_nonce=int(st.session_state.get("arena_action_nonce", 0)),
        )

    if st.session_state.get("game_over"):
        st.warning(f"Game over: `{st.session_state.get('game_over_reason')}`")
    else:
        st.info("Press **Play Next Round** to continue.")

    rows = _round_rows(engine)
    st.subheader("Round history")
    st.dataframe(rows, use_container_width=True)
    if rows:
        st.subheader("Trends")
        st.line_chart(rows, x="round", y=["p1_hp", "p2_hp"])
        st.line_chart(rows, x="round", y=["p1_resilience", "p2_resilience", "resilience_diff"])

    with st.expander("Q-learning: train & inspect Q-table", expanded=False):
        st.markdown(
            "Train a tabular Q-agent offline and inspect **Q(s,·)**. In code, use "
            "`agent.q_table_records()` for a list of rows, or `agent.q_table_payload()` for JSON."
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            ql_episodes = st.number_input(
                "Episodes", min_value=5, max_value=2000, value=80, step=5, key="ql_episodes"
            )
        with c2:
            ql_max_rounds = st.number_input(
                "Max rounds / game", min_value=3, max_value=30, value=12, key="ql_max_rounds"
            )
        with c3:
            ql_seed = st.number_input("Agent seed", min_value=0, value=0, key="ql_seed")
        ql_opp = st.selectbox("Opponent", options=OPPONENT_CHOICES, index=0, key="ql_opponent")
        if st.button("Run Q-learning training", key="ql_train_btn"):
            demo = QLearningStrategy("p1", seed=int(ql_seed))
            with st.spinner("Training…"):
                train_ql_agent(
                    demo,
                    opponent=ql_opp,
                    episodes=int(ql_episodes),
                    max_rounds=int(ql_max_rounds),
                    epsilon_start=0.25,
                    epsilon_end=0.05,
                )
            st.session_state["ql_demo_agent"] = demo
        if st.session_state.get("ql_demo_agent") is not None:
            render_learned_q_table(st.session_state["ql_demo_agent"])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Fail-fast: if the UI errors and becomes unusable, terminate the process
        # so the terminal returns cleanly for debugging.
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        _close_ui()