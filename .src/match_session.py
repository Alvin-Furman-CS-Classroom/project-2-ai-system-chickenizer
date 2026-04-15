"""Reusable match/session state model for Chickenizer.

Streamlit keeps state in `st.session_state`, but the actual match lifecycle
(init + step) is UI-agnostic. This module packages that lifecycle so the same
logic can be reused in other frontends (CLI, tests, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Optional

from engine import GameEngine
from strategies import Strategy

from analysis_payloads import merge_gamestate_with_strategy_and_cares


@dataclass(frozen=True)
class MatchSession:
    engine: GameEngine
    p1_strategy: Strategy
    p2_strategy: Strategy
    max_rounds: int

    game_over: bool = False
    game_over_reason: Optional[str] = None
    shutdown_requested: bool = False

    # "Last completed round" summary for UI/animations.
    last_round: Dict[str, Any] = None  # type: ignore[assignment]
    arena_action_nonce: int = 0

    def __post_init__(self) -> None:
        if self.last_round is None:
            object.__setattr__(
                self,
                "last_round",
                {"p1_action": None, "p2_action": None, "outcome": None},
            )


def init_match_session(
    *,
    p1_strategy: Strategy,
    p2_strategy: Strategy,
    p1_cares: Dict[str, int],
    p2_cares: Dict[str, int],
    max_rounds: int,
) -> MatchSession:
    enriched = merge_gamestate_with_strategy_and_cares(
        p1_strategy, p2_strategy, p1_cares, p2_cares
    )
    engine = GameEngine(gamestate=enriched)
    return MatchSession(
        engine=engine,
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy,
        max_rounds=int(max_rounds),
        game_over=False,
        game_over_reason=None,
        shutdown_requested=False,
        last_round={"p1_action": None, "p2_action": None, "outcome": None},
        arena_action_nonce=0,
    )


def advance_one_round(session: MatchSession) -> MatchSession:
    """Advance the match by one full round (P1 act, P2 act, resolve)."""
    if session.game_over:
        return session

    engine = session.engine
    max_rounds = int(session.max_rounds)

    # Round cap check before acting.
    if int(engine.get_gamestate().get("round", 0)) >= max_rounds:
        return replace(session, game_over=True, game_over_reason="max_rounds_reached")

    current = engine.generate_gamestate(increment_round=False)
    p1_action = session.p1_strategy(current)
    engine.play_action("p1", p1_action)

    current = engine.generate_gamestate(increment_round=False)
    p2_action = session.p2_strategy(current)
    engine.play_action("p2", p2_action)

    end_state = engine.generate_gamestate(increment_round=True)
    score = end_state.get("score", [])
    outcome = score[-1] if score else None

    new_last = {
        "p1_action": "stay" if p1_action else "swerve",
        "p2_action": "stay" if p2_action else "swerve",
        "outcome": outcome,
    }
    new_nonce = int(session.arena_action_nonce) + 1

    is_over, reason = engine.is_game_over()
    if is_over:
        return replace(
            session,
            last_round=new_last,
            arena_action_nonce=new_nonce,
            game_over=True,
            game_over_reason=str(reason),
        )

    if int(end_state.get("round", 0)) >= max_rounds:
        return replace(
            session,
            last_round=new_last,
            arena_action_nonce=new_nonce,
            game_over=True,
            game_over_reason="max_rounds_reached",
        )

    return replace(session, last_round=new_last, arena_action_nonce=new_nonce)

