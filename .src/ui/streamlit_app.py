"""
Streamlit UI for Chickenizer.

Run:
  python -m streamlit run .src/ui/streamlit_app.py
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
import html
import inspect
import json
import os
import signal
from pathlib import Path
import sys
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple, Type

import streamlit as st
import streamlit.components.v1 as components


# Ensure the repo's ".src" directory is importable when Streamlit executes this file.
try:
    from bootstrap_dot_src import add_dot_src_to_path  # type: ignore
except Exception:  # pragma: no cover - streamlit sometimes runs with odd CWD
    add_dot_src_to_path = None  # type: ignore

DOT_SRC = Path(__file__).resolve().parents[1]
if add_dot_src_to_path is not None:
    add_dot_src_to_path(root=DOT_SRC.parent)
elif str(DOT_SRC) not in sys.path:
    sys.path.insert(0, str(DOT_SRC))

from engine import GameEngine  # type: ignore  # noqa: E402
from match_session import MatchSession, advance_one_round, init_match_session  # type: ignore  # noqa: E402
from ui.arena_view import render_arena as _render_arena  # type: ignore  # noqa: E402
from ui.loading_indicator import loading_row  # type: ignore  # noqa: E402
from ui.panel_hypothesis_final import (  # type: ignore  # noqa: E402
    StrategyUIPick,
    render_hypothesis_vs_final_panel as _render_hypothesis_final_panel,
)
from ql_strategy import QLearningStrategy  # type: ignore  # noqa: E402
from train_ql import run_greedy_evaluation_episodes, train_ql_agent  # type: ignore  # noqa: E402
from ui.panel_qlearning import render_qlearning_panel as _render_qlearning_panel  # type: ignore  # noqa: E402
from strategies import (  # type: ignore  # noqa: E402
    Strategy,
    AlwaysStayStrategy,
    AlwaysSwerveStrategy,
    TitForTatStrategy,
    FollowerStrategy,
    RandomStrategy,
    HPThresholdStrategy,
    AggressiveStrategy,
    DefensiveStrategy,
    EntertainerStrategy,
    ReputationStrategy,
    MinimaxStrategy,
)

# Q-learning online training (sidebar match) — same schedule as offline panel defaults.
_QL_TRAIN_EPS_START = 0.25
_QL_TRAIN_EPS_END = 0.05

PREFERENCE_KEYS: Tuple[str, ...] = (
    "round_win",
    "round_loss",
    "tie",
    "crash",
    "hp_delta",
    "reputation_delta",
)

# MatchSession / engine ``game_over_reason`` strings → user-facing copy.
_GAME_OVER_REASON_LABELS: Dict[str, str] = {
    "max_rounds_reached": "Max rounds reached (round limit).",
    "both_hp_zero": "Both players ran out of HP.",
    "p1_hp_zero": "Player 1 ran out of HP.",
    "p2_hp_zero": "Player 2 ran out of HP.",
    "p2_resilience_tapout": "Player 2 tapped out (resilience fell too far behind).",
    "p1_resilience_tapout": "Player 1 tapped out (resilience fell too far behind).",
    "game_over": "Engine signaled game over.",
}


def _format_game_over_reason(reason: Optional[str]) -> str:
    if not reason:
        return "The match ended."
    return _GAME_OVER_REASON_LABELS.get(reason, reason.replace("_", " ").strip().title())


@dataclass(frozen=True)
class StrategyChoice:
    label: str
    cls: Type[Strategy]


STRATEGIES: List[StrategyChoice] = [
    StrategyChoice("Always Stay", AlwaysStayStrategy),
    StrategyChoice("Always Swerve", AlwaysSwerveStrategy),
    StrategyChoice("Tit For Tat", TitForTatStrategy),
    StrategyChoice("Follower (lock in after opp stay)", FollowerStrategy),
    StrategyChoice("Random", RandomStrategy),
    StrategyChoice("HP Threshold", HPThresholdStrategy),
    StrategyChoice("Aggressive (HP)", AggressiveStrategy),
    StrategyChoice("Defensive (HP)", DefensiveStrategy),
    StrategyChoice("Entertainer (spectacle / stay)", EntertainerStrategy),
    StrategyChoice("Reputation (crowd meter)", ReputationStrategy),
    StrategyChoice("Minimax (resilience diff)", MinimaxStrategy),
    StrategyChoice("Q-learning (tabular)", QLearningStrategy),
]


@dataclass(frozen=True)
class MatchSidebarInput:
    """Widget values collected from the match sidebar (one Screenlit run)."""

    max_rounds: int
    p1_choice: StrategyChoice
    p2_choice: StrategyChoice
    p1_params: Dict[str, Any]
    p2_params: Dict[str, Any]
    p1_prefs: Dict[str, int]
    p2_prefs: Dict[str, int]
    animate_arena: bool
    animation_speed: int
    return_hold_ms: int
    return_speed_ms: int
    start_new: bool
    step_once: bool
    autorun: bool


# Auto-run chain: scale sidebar arena timings (~50% duration ⇒ ~2× faster motion + rerun cadence).
_AUTORUN_ARENA_TIME_SCALE = 0.5


def _arena_timings_for_autorun(sb: MatchSidebarInput, autorun_chain_active: bool) -> Tuple[int, int, int]:
    """Return (duration_ms, hold_ms, return_ms); shorter when auto-run is stepping the match."""
    d, h, r = sb.animation_speed, sb.return_hold_ms, sb.return_speed_ms
    if not autorun_chain_active:
        return d, h, r
    k = _AUTORUN_ARENA_TIME_SCALE
    return max(120, int(d * k)), max(100, int(h * k)), max(100, int(r * k))


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


def _render_strategy_reference_list() -> None:
    """Strategy names with hover docstrings (render inside a parent expander)."""
    items: List[str] = []
    for sc in STRATEGIES:
        t = _html_title_attr(_strategy_class_doc(sc.cls))
        label = html.escape(sc.label)
        items.append(
            f'<li style="margin:0.25rem 0"><abbr title="{t}" style="cursor:help">{label}</abbr></li>'
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

    if cls is EntertainerStrategy:
        params["stay_bias"] = float(
            st.slider(
                f"{label_prefix} entertainer stay bias",
                min_value=0.0,
                max_value=1.0,
                value=0.72,
                step=0.01,
                key=f"{label_prefix}_entertainer_stay_bias",
            )
        )
        use_seed = st.checkbox(
            f"{label_prefix} entertainer use seed",
            value=False,
            key=f"{label_prefix}_entertainer_use_seed",
        )
        seed = (
            int(
                st.number_input(
                    f"{label_prefix} entertainer seed",
                    min_value=0,
                    value=0,
                    step=1,
                    key=f"{label_prefix}_entertainer_seed",
                )
            )
            if use_seed
            else 0
        )
        params["seed"] = int(seed) if use_seed else None

    if cls is ReputationStrategy:
        params["behind_stay_bias"] = float(
            st.slider(
                f"{label_prefix} rep: P(stay) when behind on reputation",
                min_value=0.0,
                max_value=1.0,
                value=0.78,
                step=0.01,
                key=f"{label_prefix}_rep_behind",
            )
        )
        params["tie_stay_bias"] = float(
            st.slider(
                f"{label_prefix} rep: P(stay) when tied",
                min_value=0.0,
                max_value=1.0,
                value=0.50,
                step=0.01,
                key=f"{label_prefix}_rep_tie",
            )
        )
        params["ahead_stay_bias"] = float(
            st.slider(
                f"{label_prefix} rep: P(stay) when ahead on reputation",
                min_value=0.0,
                max_value=1.0,
                value=0.36,
                step=0.01,
                key=f"{label_prefix}_rep_ahead",
            )
        )
        use_seed = st.checkbox(
            f"{label_prefix} reputation strategy: fix random seed",
            value=False,
            key=f"{label_prefix}_rep_use_seed",
        )
        seed = (
            int(
                st.number_input(
                    f"{label_prefix} reputation seed",
                    min_value=0,
                    value=0,
                    step=1,
                    key=f"{label_prefix}_rep_seed",
                )
            )
            if use_seed
            else 0
        )
        params["seed"] = int(seed) if use_seed else None

    if cls is QLearningStrategy:
        st.caption(
            "On **New game**: trains vs the other player’s strategy, short greedy eval, then **greedy** live play."
        )
        params["ql_training_episodes"] = int(
            st.number_input(
                f"{label_prefix} QL training episodes",
                min_value=10,
                max_value=2000,
                value=120,
                step=10,
                key=f"{label_prefix}_ql_train_eps",
            )
        )
        params["ql_training_max_rounds"] = int(
            st.number_input(
                f"{label_prefix} QL max rounds per training game",
                min_value=3,
                max_value=40,
                value=12,
                step=1,
                key=f"{label_prefix}_ql_train_max_r",
            )
        )
        params["ql_greedy_eval_episodes"] = int(
            st.number_input(
                f"{label_prefix} QL greedy eval episodes (post-train)",
                min_value=0,
                max_value=200,
                value=15,
                step=1,
                key=f"{label_prefix}_ql_eval_eps",
            )
        )
        params["ql_seed"] = int(
            st.number_input(
                f"{label_prefix} QL RNG seed",
                min_value=0,
                value=0,
                step=1,
                key=f"{label_prefix}_ql_seed",
            )
        )
        params["ql_minimax_depth"] = int(
            st.number_input(
                f"{label_prefix} QL training minimax depth (if opponent is minimax)",
                min_value=1,
                max_value=6,
                value=2,
                step=1,
                key=f"{label_prefix}_ql_mm_depth",
                help="Used only when the other player uses Minimax; otherwise ignored.",
            )
        )

    return params


def _preferences_ui(player: str, base: Dict[str, int]) -> Dict[str, int]:
    """Vertical inputs for resilience preference weights (fits narrow sidebar)."""
    prefs: Dict[str, int] = {}
    for key in PREFERENCE_KEYS:
        prefs[key] = int(
            st.number_input(
                f"{player} · {key}",
                value=int(base.get(key, 0)),
                step=1,
                key=f"{player}_pref_{key}",
            )
        )
    return prefs


def _build_strategy(choice: StrategyUIPick, player: str, params: Dict[str, Any]) -> Strategy:
    """Builds a strategy from a choice and parameters.
    Args:
        choice: The strategy choice.
        player: The player identifier.
        params: The parameters for the strategy.

    Returns:
        A strategy.
    """
    if choice.cls is QLearningStrategy:
        return QLearningStrategy(player, seed=int(params.get("ql_seed", 0)))
    return choice.cls(player, **params)


def _minimax_depth_for_train_ql(opponent: Strategy, fallback: int) -> int:
    if isinstance(opponent, MinimaxStrategy):
        return int(getattr(opponent, "depth", fallback))
    return int(fallback)


def _train_and_eval_ql_for_live_match(
    agent: QLearningStrategy,
    opponent: Strategy,
    *,
    agent_plays_p1: bool,
    agent_params: Dict[str, Any],
) -> None:
    """Train tabular Q vs the fixed opponent, optional greedy eval, then freeze for live engine."""
    episodes = int(agent_params.get("ql_training_episodes", 120))
    max_tr = int(agent_params.get("ql_training_max_rounds", 12))
    eval_eps = int(agent_params.get("ql_greedy_eval_episodes", 15))
    seed = int(agent_params.get("ql_seed", 0))
    md = _minimax_depth_for_train_ql(
        opponent, int(agent_params.get("ql_minimax_depth", 2))
    )
    train_ql_agent(
        agent,
        opponent,
        episodes=episodes,
        max_rounds=max_tr,
        agent_plays_p1=agent_plays_p1,
        epsilon_start=_QL_TRAIN_EPS_START,
        epsilon_end=_QL_TRAIN_EPS_END,
        minimax_depth=md,
        random_seed=seed,
    )
    if eval_eps > 0:
        run_greedy_evaluation_episodes(
            agent,
            opponent,
            episodes=eval_eps,
            max_rounds=max_tr,
            agent_plays_p1=agent_plays_p1,
            minimax_depth=md,
            random_seed=seed,
        )
    agent.learn = False
    agent.epsilon = 0.0
    agent.reset_episode()


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
    if isinstance(p1_strategy, QLearningStrategy) and isinstance(p2_strategy, QLearningStrategy):
        st.error(
            "Only one player can use Q-learning in a match. Pick a built-in strategy for the other player, "
            "then click **Start New Game** again."
        )
        return
    if isinstance(p1_strategy, QLearningStrategy):
        with loading_row("Training P1 Q-learning vs P2 (then greedy eval)…"):
            _train_and_eval_ql_for_live_match(
                p1_strategy, p2_strategy, agent_plays_p1=True, agent_params=p1_params
            )
    if isinstance(p2_strategy, QLearningStrategy):
        with loading_row("Training P2 Q-learning vs P1 (then greedy eval)…"):
            _train_and_eval_ql_for_live_match(
                p2_strategy, p1_strategy, agent_plays_p1=False, agent_params=p2_params
            )
    st.session_state["match"] = init_match_session(
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy,
        p1_cares=p1_prefs,
        p2_cares=p2_prefs,
        max_rounds=max_rounds,
    )
    # Unique per match so the arena iframe never reuses DOM / keyframe names after New game.
    st.session_state["_arena_frame_id"] = int(st.session_state.get("_arena_frame_id", 0)) + 1


def _advance_one_round() -> None:
    """Advances the match by one round."""
    match: Optional[MatchSession] = st.session_state.get("match")
    if match is None:
        return
    st.session_state["match"] = advance_one_round(match)


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
        if rnd <= 0:
            continue
        p1_hist = state.get("p1_action_history", [])
        p2_hist = state.get("p2_action_history", [])
        score = state.get("score", [])
        # Only keep snapshots that represent a fully completed round.
        if len(p1_hist) == rnd and len(p2_hist) == rnd and len(score) == rnd:
            by_round[rnd] = state

    rows: List[Dict[str, Any]] = []
    for round_num in sorted(by_round):
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


def _build_strategy_for_ne_panel(
    pick: StrategyUIPick, player: str, params: Dict[str, Any]
) -> Strategy:
    """Use trained Q-learning instances from the live match when the sidebar choice matches."""
    match: Optional[MatchSession] = st.session_state.get("match")
    if match is not None and pick.cls is QLearningStrategy:
        inst = match.p1_strategy if player == "p1" else match.p2_strategy
        if isinstance(inst, QLearningStrategy) and inst.player == player:
            return inst
    return _build_strategy(pick, player, params)


def _render_hypothesis_vs_final_panel(
    p1_choice: StrategyChoice,
    p2_choice: StrategyChoice,
    p1_params: Dict[str, Any],
    p2_params: Dict[str, Any],
    p1_prefs: Dict[str, int],
    p2_prefs: Dict[str, int],
) -> None:
    """Hypothesis vs final NE (same story as ASCII helpers) using live match state when available."""
    match: Optional[MatchSession] = st.session_state.get("match")
    live_base: Optional[Dict[str, Any]] = None
    if match is not None:
        live_base = match.engine.get_gamestate()
    _render_hypothesis_final_panel(
        p1_choice,
        p2_choice,
        p1_params,
        p2_params,
        p1_prefs,
        p2_prefs,
        build_strategy=_build_strategy_for_ne_panel,
        live_base_gamestate=live_base,
    )


def _render_match_state(engine: GameEngine, p1_strategy: Strategy, p2_strategy: Strategy, last_round: Dict[str, Any]) -> None:
    """Compact scoreboard + player strip (HP bars and last outcome)."""
    gs = engine.get_gamestate()
    p1_hp = int(gs.get("p1_hp", 0))
    p2_hp = int(gs.get("p2_hp", 0))
    max_hp = int(GameEngine.DEFAULT_HP)
    round_num = int(gs.get("round", 0))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Round", round_num)
    m2.metric("P1 HP", f"{p1_hp}/{max_hp}")
    m3.metric("P2 HP", f"{p2_hp}/{max_hp}")
    m4.metric("Resilience Δ", int(gs.get("resilience_diff", 0)))

    p1_col, mid_col, p2_col = st.columns([1.15, 1, 1.15])
    with p1_col:
        st.markdown("**P1** 🚗")
        st.caption(p1_strategy.__class__.__name__)
        st.caption(f"Last: **{last_round.get('p1_action') or '—'}**")
        st.progress(max(0.0, min(1.0, p1_hp / max_hp)))
    with mid_col:
        outcome = last_round.get("outcome")
        st.caption("Last outcome")
        if outcome is None:
            st.markdown("#### —")
            st.caption("No rounds yet")
        elif outcome == "CRASH":
            st.markdown("#### 💥 **Crash**")
        elif outcome == "TIE":
            st.markdown("#### **Tie**")
        elif outcome == "P1":
            st.markdown("#### **P1 wins**")
        elif outcome == "P2":
            st.markdown("#### **P2 wins**")
        else:
            st.markdown(f"#### **{html.escape(str(outcome))}**")
    with p2_col:
        st.markdown("**P2** 🏎️")
        st.caption(p2_strategy.__class__.__name__)
        st.caption(f"Last: **{last_round.get('p2_action') or '—'}**")
        st.progress(max(0.0, min(1.0, p2_hp / max_hp)))

    with st.expander("Resilience weight dicts (merged cares)", expanded=False):
        st.json(
            {
                "p1_preferences": gs.get("p1_preferences", {}),
                "p2_preferences": gs.get("p2_preferences", {}),
            }
        )


def _render_game_over_callout(reason: Optional[str]) -> None:
    """Prominent, colored banner so the match outcome is easy to spot on the Arena tab."""
    reason_html = html.escape(_format_game_over_reason(reason))
    st.markdown(
        f"""
<div style="
  background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 42%, #4c1d95 78%, #78350f 100%);
  border: 2px solid #fbbf24;
  border-radius: 14px;
  padding: 1.05rem 1.3rem;
  margin: 0.65rem 0 1rem 0;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(251, 191, 36, 0.25) inset;
">
  <div style="
    color: #fef08a;
    font-size: 1.5rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
    margin-bottom: 0.4rem;
    font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  ">Game over</div>
  <div style="
    color: #e2e8f0;
    font-size: 1.05rem;
    font-weight: 600;
    line-height: 1.5;
    font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  ">{reason_html}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


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


def _render_match_sidebar() -> MatchSidebarInput:
    """Collect match controls in a grouped, scroll-friendly sidebar."""
    with st.sidebar:
        st.header("Match")
        max_rounds = int(
            st.slider(
                "Round limit",
                min_value=1,
                max_value=50,
                value=10,
                help="Maximum completed rounds per game.",
            )
        )

        tp1, tp2 = st.tabs(["Player 1", "Player 2"])
        with tp1:
            p1_choice = st.selectbox(
                "Strategy",
                options=STRATEGIES,
                format_func=lambda c: c.label,
                index=2,
                key="p1_strategy_choice",
            )
            _strategy_doc_hint(p1_choice)
            p1_params = _strategy_params_ui("P1", p1_choice)
        with tp2:
            p2_choice = st.selectbox(
                "Strategy",
                options=STRATEGIES,
                format_func=lambda c: c.label,
                index=2,
                key="p2_strategy_choice",
            )
            _strategy_doc_hint(p2_choice)
            p2_params = _strategy_params_ui("P2", p2_choice)

        with st.expander("Resilience weights (cares)", expanded=False):
            st.caption("Per-round contributions to resilience (see `GameEngine.DEFAULT_GAMESTATE`).")
            defaults = GameEngine.DEFAULT_GAMESTATE
            pc1, pc2 = st.columns(2)
            with pc1:
                st.markdown("**P1**")
                p1_prefs = _preferences_ui("p1", defaults.get("p1_preferences", {}))
            with pc2:
                st.markdown("**P2**")
                p2_prefs = _preferences_ui("p2", defaults.get("p2_preferences", {}))

        with st.expander("Arena motion", expanded=False):
            animate_arena = st.checkbox("Animate arena", value=True, key="animate_arena")
            animation_speed = 700
            return_hold_ms = 1200
            return_speed_ms = 350
            if animate_arena:
                animation_speed = int(
                    st.slider("Speed (ms)", 200, 1500, 700, 50, key="arena_anim_ms")
                )
                return_hold_ms = int(
                    st.slider("Hold (ms)", 0, 2500, 1200, 100, key="arena_hold_ms")
                )
                return_speed_ms = int(
                    st.slider("Return (ms)", 100, 1200, 350, 50, key="arena_return_ms")
                )

        with st.expander("Strategy catalog", expanded=False):
            _render_strategy_reference_list()

        st.divider()
        # Read ``start_new`` before auto-init so ``_init_match`` does not run twice when ``match`` is
        # None and **New game** is clicked on the same rerun (duplicate training / session churn).
        autorun = st.checkbox(
            "Auto-run to end",
            value=False,
            key="autorun_to_end",
            help="Play button runs all remaining rounds in one go.",
        )
        play_label = "Run to end" if autorun else "Next round"
        b1, b2 = st.columns(2)
        with b1:
            start_new = st.button("New game", type="primary", use_container_width=True)
        if st.session_state.get("match") is None and not start_new:
            _init_match(
                p1_choice,
                p2_choice,
                p1_params,
                p2_params,
                p1_prefs,
                p2_prefs,
                max_rounds,
            )

        match_for_step: Optional[MatchSession] = st.session_state.get("match")
        step_disabled = bool(
            match_for_step is None
            or (bool(match_for_step.game_over) and not start_new)
        )
        with b2:
            step_once = st.button(play_label, use_container_width=True, disabled=step_disabled)

        with st.expander("Shutdown", expanded=False):
            allow_shutdown = st.checkbox("Confirm exit", value=False, key="allow_shutdown")
            shutdown_now = st.button("Quit app", type="secondary", use_container_width=True)
            if shutdown_now and allow_shutdown:
                _m = st.session_state.get("match")
                if _m is not None:
                    st.session_state["match"] = replace(_m, shutdown_requested=True)
                _close_ui()
            elif shutdown_now and not allow_shutdown:
                st.caption("Check **Confirm exit** first.")

    return MatchSidebarInput(
        max_rounds=max_rounds,
        p1_choice=p1_choice,
        p2_choice=p2_choice,
        p1_params=p1_params,
        p2_params=p2_params,
        p1_prefs=p1_prefs,
        p2_prefs=p2_prefs,
        animate_arena=animate_arena,
        animation_speed=animation_speed,
        return_hold_ms=return_hold_ms,
        return_speed_ms=return_speed_ms,
        start_new=start_new,
        step_once=step_once,
        autorun=autorun,
    )


def main() -> None:
    st.set_page_config(page_title="Chickenizer Live Match", layout="wide")
    # Old sessions may hold a stale ``st.empty()`` ref; never reuse it across runs.
    st.session_state.pop("_arena_iframe_slot", None)
    st.title("Chickenizer")
    st.caption("Sequential Chicken · one round per step · Nash snapshot updates with live state.")

    sb = _render_match_sidebar()

    if sb.start_new:
        st.session_state.pop("_autorun_chain", None)
        _init_match(
            sb.p1_choice,
            sb.p2_choice,
            sb.p1_params,
            sb.p2_params,
            sb.p1_prefs,
            sb.p2_prefs,
            sb.max_rounds,
        )

    if sb.step_once:
        if sb.autorun:
            st.session_state["_autorun_chain"] = True
        else:
            _advance_one_round()

    match2: Optional[MatchSession] = st.session_state.get("match")
    if match2 is None:
        st.error(
            "No active match. If both players were Q-learning, pick a fixed strategy for one side, "
            "then click **New game**."
        )
        return

    # Auto-run: one round per Streamlit run so the arena iframe reloads and animates each step.
    if st.session_state.get("_autorun_chain"):
        if not sb.autorun:
            st.session_state.pop("_autorun_chain", None)
        elif match2.game_over:
            st.session_state.pop("_autorun_chain", None)
        else:
            st.session_state["match"] = advance_one_round(match2)
            match2 = st.session_state.get("match")

    if match2 is None:
        st.error(
            "No active match. If both players were Q-learning, pick a fixed strategy for one side, "
            "then click **New game**."
        )
        return
    engine: GameEngine = match2.engine
    p1_strategy: Strategy = match2.p1_strategy
    p2_strategy: Strategy = match2.p2_strategy
    last_round = match2.last_round

    _autorun_chain_active = bool(st.session_state.get("_autorun_chain") and sb.autorun)
    arena_dur_ms, arena_hold_ms, arena_ret_ms = _arena_timings_for_autorun(sb, _autorun_chain_active)

    tab_arena, tab_nash, tab_charts = st.tabs(["Arena", "Nash & joint play", "History & charts"])
    with tab_arena:
        _render_match_state(engine, p1_strategy, p2_strategy, last_round)
        if sb.animate_arena:
            _render_arena(
                last_round=last_round,
                game_over=bool(match2.game_over),
                duration_ms=arena_dur_ms,
                hold_ms=arena_hold_ms,
                return_ms=arena_ret_ms,
                action_nonce=int(match2.arena_action_nonce),
                frame_id=int(st.session_state.get("_arena_frame_id", 0)),
            )
        if match2.game_over:
            _render_game_over_callout(match2.game_over_reason)
        elif sb.autorun:
            st.caption(
                "Run to end plays one round at a time with arena animation until the match stops. "
                "Uncheck Auto-run to end to step manually."
            )
        else:
            st.caption("Use **Next round** in the sidebar to advance one round.")

    with tab_nash:
        _render_hypothesis_vs_final_panel(
            sb.p1_choice,
            sb.p2_choice,
            sb.p1_params,
            sb.p2_params,
            sb.p1_prefs,
            sb.p2_prefs,
        )

    with tab_charts:
        rows = _round_rows(engine)
        st.subheader("Round log")
        st.dataframe(rows, use_container_width=True, hide_index=True)
        if rows:
            st.subheader("Trends")
            c_hp, c_res = st.columns(2)
            with c_hp:
                st.line_chart(rows, x="round", y=["p1_hp", "p2_hp"])
            with c_res:
                st.line_chart(rows, x="round", y=["p1_resilience", "p2_resilience", "resilience_diff"])
        _render_qlearning_panel()

    if (
        st.session_state.get("_autorun_chain")
        and sb.autorun
        and match2 is not None
        and not match2.game_over
    ):
        # Let the browser finish one full arena cycle before the next rerun (matches scaled timings above).
        delay_s = (arena_dur_ms + arena_hold_ms + arena_ret_ms) / 1000.0
        time.sleep(max(0.05, delay_s))
        st.rerun()


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