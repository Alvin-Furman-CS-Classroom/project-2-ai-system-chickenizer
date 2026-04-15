"""Integration: Module 4 early termination stays consistent in Module 5 analysis."""

from __future__ import annotations

from copy import deepcopy
from bootstrap_dot_src import add_dot_src_to_path

add_dot_src_to_path()

from engine import GameEngine  # noqa: E402
from nash_repeated_analysis import analyze_repeated_play  # noqa: E402
from strategies import AlwaysStayStrategy, AlwaysSwerveStrategy, merge_strategy_preferences  # noqa: E402


def test_repeated_play_handles_resilience_tapout_early_end():
    p1 = AlwaysStayStrategy("p1")
    p2 = AlwaysSwerveStrategy("p2")

    base = GameEngine().get_gamestate()
    merged = merge_strategy_preferences(base, p1, p2)

    # Force near-threshold resilience so the match should tap out quickly.
    gs = deepcopy(merged)
    gs["p1_resilience"] = 95
    gs["p2_resilience"] = 0
    gs["resilience_diff"] = 95

    r = analyze_repeated_play(p1, p2, gs, max_rounds=50)
    assert 1 <= r.rounds_played < 50
    assert len(r.records) == r.rounds_played
    assert isinstance(r.match_end_reason, str)
    assert r.match_end_reason != ""

    # Aggregate counts should always sum to the number of completed rounds.
    assert sum(cell.count for cell in r.joint_cells.values()) == r.rounds_played
