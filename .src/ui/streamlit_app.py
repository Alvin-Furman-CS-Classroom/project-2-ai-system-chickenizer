"""
Streamlit UI for Chickenizer.

Run:
  python -m streamlit run .src/ui/streamlit_app.py
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Tuple, Type

import streamlit as st
import streamlit.components.v1 as components


# Ensure the repo's ".src" directory is importable when Streamlit executes this file.
DOT_SRC = Path(__file__).resolve().parents[1]
if str(DOT_SRC) not in sys.path:
    sys.path.insert(0, str(DOT_SRC))

from engine import GameEngine  # type: ignore  # noqa: E402
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


def _strategy_params_ui(label_prefix: str, choice: StrategyChoice) -> Dict[str, Any]:
    cls = choice.cls
    params: Dict[str, Any] = {}
    if cls is RandomStrategy:
        seed = st.number_input(
            f"{label_prefix} seed (optional)",
            min_value=0,
            value=0,
            step=1,
            key=f"{label_prefix}_random_seed",
        )
        use_seed = st.checkbox(f"{label_prefix} use seed", value=False, key=f"{label_prefix}_random_use_seed")
        params["seed"] = int(seed) if use_seed else None
    if cls is HPThresholdStrategy:
        use_custom = st.checkbox(f"{label_prefix} custom HP threshold", value=False, key=f"{label_prefix}_hp_use_custom")
        params["threshold"] = (
            int(st.number_input(f"{label_prefix} HP threshold", min_value=0, value=20, step=1, key=f"{label_prefix}_hp_threshold"))
            if use_custom
            else None
        )
    if cls is MinimaxStrategy:
        params["depth"] = int(
            st.slider(f"{label_prefix} minimax depth (rounds)", min_value=1, max_value=6, value=2, step=1, key=f"{label_prefix}_minimax_depth")
        )
    return params


def _preferences_ui(player: str, base: Dict[str, int]) -> Dict[str, int]:
    st.caption('Preference weights ("cares").')
    prefs: Dict[str, int] = {}
    cols = st.columns(5)
    for i, key in enumerate(PREFERENCE_KEYS):
        with cols[i]:
            prefs[key] = int(st.number_input(f"{player} {key}", value=int(base.get(key, 0)), step=1, key=f"{player}_pref_{key}"))
    return prefs


def _build_strategy(choice: StrategyChoice, player: str, params: Dict[str, Any]) -> Strategy:
    return choice.cls(player, **params)  # type: ignore[arg-type]


def _init_match(
    p1_choice: StrategyChoice,
    p1_params: Dict[str, Any],
    p2_choice: StrategyChoice,
    p2_params: Dict[str, Any],
    p1_prefs: Dict[str, int],
    p2_prefs: Dict[str, int],
    max_rounds: int,
) -> None:
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


def _advance_one_round() -> None:
    if not st.session_state.get("initialized"):
        return
    if st.session_state.get("game_over"):
        return

    engine: GameEngine = st.session_state["engine"]
    p1_strategy: Strategy = st.session_state["p1_strategy"]
    p2_strategy: Strategy = st.session_state["p2_strategy"]
    max_rounds = int(st.session_state["max_rounds"])

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
    st.session_state["last_round"] = {
        "p1_action": "stay" if p1_action else "swerve",
        "p2_action": "stay" if p2_action else "swerve",
        "outcome": outcome,
    }

    is_over, reason = engine.is_game_over()
    if is_over:
        st.session_state["game_over"] = True
        st.session_state["game_over_reason"] = reason
        return
    if end_state.get("round", 0) >= max_rounds:
        st.session_state["game_over"] = True
        st.session_state["game_over_reason"] = "max_rounds_reached"


def _round_rows(engine: GameEngine) -> List[Dict[str, Any]]:
    by_round: Dict[int, Dict[str, Any]] = {}
    for state in engine.gamestate_history:
        r = int(state.get("round", 0))
        by_round[r] = state

    rows: List[Dict[str, Any]] = []
    for round_num in sorted(by_round):
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
    gs = engine.get_gamestate()
    p1_hp = int(gs.get("p1_hp", 0))
    p2_hp = int(gs.get("p2_hp", 0))
    max_hp = int(GameEngine.DEFAULT_HP)
    round_num = int(gs.get("round", 0))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current round", round_num)
    c2.metric("P1 HP", p1_hp)
    c3.metric("P2 HP", p2_hp)
    c4.metric("R1-R2", int(gs.get("resilience_diff", 0)))

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


def main() -> None:
    st.set_page_config(page_title="Chickenizer Live Match", layout="wide")
    st.title("Chickenizer - Live Match")
    st.write("Run the game one round at a time and watch the players react.")

    with st.sidebar:
        st.header("Match setup")
        max_rounds = int(st.slider("Max rounds", min_value=1, max_value=50, value=10))

        st.subheader("P1 strategy")
        p1_choice = st.selectbox("P1 strategy", options=STRATEGIES, format_func=lambda c: c.label, index=2, key="p1_strategy_choice")
        p1_params = _strategy_params_ui("P1", p1_choice)

        st.subheader("P2 strategy")
        p2_choice = st.selectbox("P2 strategy", options=STRATEGIES, format_func=lambda c: c.label, index=2, key="p2_strategy_choice")
        p2_params = _strategy_params_ui("P2", p2_choice)

        st.subheader("Player preferences (cares)")
        defaults = GameEngine.DEFAULT_GAMESTATE
        p1_prefs = _preferences_ui("p1", defaults.get("p1_preferences", {}))
        p2_prefs = _preferences_ui("p2", defaults.get("p2_preferences", {}))

        start_new = st.button("Start New Game", type="primary", width="stretch")
        step_disabled = bool(
            st.session_state.get("game_over", False) or not st.session_state.get("initialized", False)
        )
        step_once = st.button("Play Next Round", width="stretch", disabled=step_disabled)

        st.divider()
        st.subheader("App control")
        allow_shutdown = st.checkbox(
            "I understand this will stop the Streamlit application (please do this when you're done playing)",
            value=False,
            key="allow_shutdown",
        )
        shutdown_now = st.button("Shutdown App", type="secondary", width='stretch')
        if shutdown_now and allow_shutdown:
            st.session_state["shutdown_requested"] = True

    if st.session_state.get("shutdown_requested"):
        # Browser security rules may block tab closes in some contexts, but this
        # is the safest best-effort close signal available from the page.
        components.html(
            """
            <script>
                window.open('', '_self');
                window.close();
            </script>
            """,
            height=0,
        )
        # Give the browser a moment to process the close request, then stop server.
        time.sleep(0.35)
        os._exit(0)

    if start_new or not st.session_state.get("initialized"):
        _init_match(p1_choice, p1_params, p2_choice, p2_params, p1_prefs, p2_prefs, max_rounds)

    if step_once:
        _advance_one_round()

    engine: GameEngine = st.session_state["engine"]
    p1_strategy: Strategy = st.session_state["p1_strategy"]
    p2_strategy: Strategy = st.session_state["p2_strategy"]
    last_round = st.session_state["last_round"]

    _render_match_state(engine, p1_strategy, p2_strategy, last_round)

    if st.session_state.get("game_over"):
        st.warning(f"Game over: `{st.session_state.get('game_over_reason')}`")
    else:
        st.info("Press **Play Next Round** to continue.")

    rows = _round_rows(engine)
    st.subheader("Round history")
    st.dataframe(rows, width='stretch')
    if rows:
        st.subheader("Trends")
        st.line_chart(rows, x="round", y=["p1_hp", "p2_hp"])
        st.line_chart(rows, x="round", y=["p1_resilience", "p2_resilience", "resilience_diff"])


if __name__ == "__main__":
    main()

