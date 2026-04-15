"""Tests for n-round repeated-play analysis (composite + conditional stats)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ".src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from engine import GameEngine  # noqa: E402
from nash_repeated_analysis import analyze_repeated_play  # noqa: E402
from strategies import (  # noqa: E402
    AlwaysStayStrategy,
    AlwaysSwerveStrategy,
    merge_strategy_preferences,
)


def _merged(p1, p2):
    base = GameEngine().get_gamestate()
    return merge_strategy_preferences(base, p1, p2)


class TestRepeatedPlayAlwaysStaySwerve:
    def test_rounds_match_max_and_joint_cell(self):
        p1 = AlwaysStayStrategy("p1")
        p2 = AlwaysSwerveStrategy("p2")
        r = analyze_repeated_play(p1, p2, _merged(p1, p2), max_rounds=4)
        assert r.rounds_played == 4
        assert len(r.records) == 4
        # P1 stay, P2 swerve every round
        key = (1, 0)  # Stay, Swerve
        assert r.joint_cells[key].count == 4
        assert r.joint_cells[key].sum_delta_p1 == 40  # 4 * 10

    def test_conditional_has_prev_stay_swerve(self):
        p1 = AlwaysStayStrategy("p1")
        p2 = AlwaysSwerveStrategy("p2")
        # Keep total resilience diff below tap-out (|diff| < 100): 4 rounds → diff 80.
        r = analyze_repeated_play(p1, p2, _merged(p1, p2), max_rounds=4)
        prev = (1, 0)
        assert prev in r.conditional_prev_to_next
        # Next round is identical; mean next delta should match one-round delta
        agg = r.conditional_prev_to_next[prev]
        assert agg.count == 3  # (r1→r2), (r2→r3), (r3→r4) given identical joint actions
        assert agg.mean_delta_p1 == 10.0
        assert agg.mean_delta_p2 == -10.0


class TestGameOverEarly:
    def test_fewer_records_if_tapout(self):
        pytest.importorskip("strategies")
        from strategies import MinimaxStrategy  # noqa: E402

        p1 = MinimaxStrategy("p1", depth=1)
        p2 = MinimaxStrategy("p2", depth=1)
        merged = _merged(p1, p2)
        # Large horizon; game may end early on resilience
        r = analyze_repeated_play(p1, p2, merged, max_rounds=500)
        assert r.rounds_played >= 1
        assert r.rounds_played <= 500
        assert len(r.records) == r.rounds_played
