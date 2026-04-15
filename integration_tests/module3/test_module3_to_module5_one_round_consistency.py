"""Integration: Module 3 normal-form payoffs align with realized one-round engine outcome.

We compute the induced 2×2 payoff matrices at a merged gamestate (Module 3),
then execute one fixed joint action in the engine and verify the resulting
resilience values match the matrix cell.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / ".src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from engine import GameEngine  # noqa: E402
from nash_normal_form import build_payoff_matrices_at_merged_state  # noqa: E402
from strategies import AlwaysStayStrategy, AlwaysSwerveStrategy, merge_strategy_preferences  # noqa: E402


def test_one_shot_matrix_cell_matches_realized_round_outcome_from_same_state():
    p1 = AlwaysStayStrategy("p1")
    p2 = AlwaysSwerveStrategy("p2")

    base = GameEngine().get_gamestate()
    merged = merge_strategy_preferences(base, p1, p2)

    # Module 3: induced payoffs at this exact merged state.
    payoff_p1, payoff_p2 = build_payoff_matrices_at_merged_state(merged)

    # Choose a concrete joint action and execute it in the engine.
    # (row i = P1 action, col j = P2 action; 0 = Swerve, 1 = Stay)
    i, j = 1, 0  # P1 Stay, P2 Swerve
    p1_action = True
    p2_action = False

    eng = GameEngine(gamestate=merged)
    eng.play_action("p1", p1_action)
    eng.play_action("p2", p2_action)
    end_state = eng.generate_gamestate(increment_round=True)

    # The normal-form cell values are cumulative resilience after one round
    # from the baseline in `merged`.
    assert int(end_state["p1_resilience"]) == int(payoff_p1[i][j])
    assert int(end_state["p2_resilience"]) == int(payoff_p2[i][j])
