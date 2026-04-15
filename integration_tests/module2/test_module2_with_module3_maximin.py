"""Integration: Module 2 (minimax search) cross-check with Module 3 normal form.

We treat Module 2's implemented search as ``MinimaxStrategy`` in ``strategies.py``.
For depth=1, minimax should pick the maximin action using the one-shot induced
normal-form utilities.
"""

from __future__ import annotations

from bootstrap_dot_src import add_dot_src_to_path

add_dot_src_to_path()

from engine import GameEngine  # noqa: E402
from nash_normal_form import build_payoff_matrices  # noqa: E402
from strategies import AlwaysSwerveStrategy, MinimaxStrategy  # noqa: E402


def _maximin_row_index(diff_matrix: list[list[int]]) -> int:
    """Return row i maximizing min_j diff[i][j]. Ties choose the first."""
    row_mins = [min(row) for row in diff_matrix]
    best = max(row_mins)
    return row_mins.index(best)


def test_module2_depth1_matches_module3_maximin_action_on_default_state():
    # Module 3: build one-shot payoffs for a concrete opponent strategy.
    #
    # We choose a fixed P2 strategy to make the induced matrix stable, but note:
    # the matrix enumerates BOTH actions for each player (Swerve/Stay), so the
    # strategy choice here primarily affects preferences (if any).
    p1_dummy = AlwaysSwerveStrategy("p1")
    p2 = AlwaysSwerveStrategy("p2")
    p1_pay, p2_pay = build_payoff_matrices(p1_dummy, p2)

    # Convert Module 3 per-player payoffs to Module 2 utility (resilience_diff).
    diff = [[p1_pay[i][j] - p2_pay[i][j] for j in range(2)] for i in range(2)]
    best_i = _maximin_row_index(diff)  # 0 = swerve, 1 = stay
    expected_action = True if best_i == 1 else False

    # Module 2: minimax action at depth=1 should match that maximin choice.
    engine = GameEngine()
    gs = engine.get_gamestate()
    mm = MinimaxStrategy("p1", depth=1)
    chosen = mm(gs)
    assert chosen == expected_action
