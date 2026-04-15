"""Integration: Module 2 (minimax) -> simulation -> Module 5 repeated-play analysis."""

from __future__ import annotations

from bootstrap_dot_src import add_dot_src_to_path

add_dot_src_to_path()

from engine import GameEngine  # noqa: E402
from nash_repeated_analysis import analyze_repeated_play  # noqa: E402
from strategies import AlwaysSwerveStrategy, MinimaxStrategy, merge_strategy_preferences  # noqa: E402


def test_module2_minimax_feeds_module5_repeated_play_contracts():
    # Module 2: minimax strategy instance (search-driven actions).
    p1 = MinimaxStrategy("p1", depth=2)
    p2 = AlwaysSwerveStrategy("p2")

    # Ensure preferences are merged as in normal simulation pipelines.
    base = GameEngine().get_gamestate()
    merged = merge_strategy_preferences(base, p1, p2)

    # Module 5: repeated-play analysis uses engine simulation under the hood.
    r = analyze_repeated_play(p1, p2, merged, max_rounds=6)

    # Integration assertions: mostly shape/consistency, not brittle exact numbers.
    assert r.rounds_played >= 1
    assert r.rounds_played <= 6
    assert len(r.records) == r.rounds_played
    assert isinstance(r.match_end_reason, str)

    # Aggregates should be present (some joint action must have occurred).
    assert sum(cell.count for cell in r.joint_cells.values()) == r.rounds_played
