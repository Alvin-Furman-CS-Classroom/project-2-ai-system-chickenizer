"""Tests for coordination-hypothesis opponent deviation counts."""

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / ".src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hypothesis_coordination_deviation import (  # noqa: E402
    count_opponent_deviations_by_joint_cell,
    expected_opponent_stay,
    hypothesis_deviation_report_from_final_state,
    joint_cell_index,
    opponent_seat_for_agent,
)
from strategies import (  # noqa: E402
    AlwaysStayStrategy,
    AlwaysSwerveStrategy,
    GameSimulator,
)


class TestJointIndex:
    def test_indices_match_swerve_stay_order(self):
        assert joint_cell_index(False, False) == 0
        assert joint_cell_index(False, True) == 1
        assert joint_cell_index(True, False) == 2
        assert joint_cell_index(True, True) == 3


class TestExpectedOpponent:
    def test_p2_follows_opposite_of_p1(self):
        assert expected_opponent_stay("p2", p1_stay=False, p2_stay=True) is True
        assert expected_opponent_stay("p2", p1_stay=True, p2_stay=False) is False

    def test_p1_follows_opposite_of_p2(self):
        assert expected_opponent_stay("p1", p1_stay=True, p2_stay=False) is True
        assert expected_opponent_stay("p1", p1_stay=False, p2_stay=True) is False


class TestCountDeviations:
    def test_no_deviation_when_p2_plays_coordination_vs_swerve_p1(self):
        # P1 always swerve → P2 should always stay; P2 stays → never deviate.
        n = 6
        p1 = ["swerve"] * n
        p2 = ["stay"] * n
        assert count_opponent_deviations_by_joint_cell(p1, p2, "p2") == [0, 0, 0, 0]

    def test_all_deviations_in_swerve_swerve_when_p2_always_swerves(self):
        n = 5
        p1 = ["swerve"] * n
        p2 = ["swerve"] * n
        assert count_opponent_deviations_by_joint_cell(p1, p2, "p2") == [n, 0, 0, 0]

    def test_double_stay_deviation_bucket(self):
        # P1 stay → expect P2 swerve; P2 stays → deviation at (stay, stay).
        assert count_opponent_deviations_by_joint_cell(
            ["stay"], ["stay"], "p2"
        ) == [0, 0, 0, 1]

    def test_opponent_p1_deviation_bucket(self):
        # P2 swerve → expect P1 stay; P1 swerves → deviation at (swerve, swerve).
        assert count_opponent_deviations_by_joint_cell(
            ["swerve"], ["swerve"], "p1"
        ) == [1, 0, 0, 0]


class TestOpponentSeat:
    def test_agent_p1_implies_opponent_p2(self):
        assert opponent_seat_for_agent(True) == "p2"
        assert opponent_seat_for_agent(False) == "p1"


class TestSimulateIntegration:
    def test_both_swerve_p2_deviates_each_round_p1_swerve_implies_p2_stay(self):
        sim = GameSimulator()
        r = sim.simulate(
            AlwaysSwerveStrategy("p1"),
            AlwaysSwerveStrategy("p2"),
            max_rounds=8,
        )
        rep = hypothesis_deviation_report_from_final_state(
            r["final_state"], agent_plays_p1=True
        )
        # P1 swerve → hypothesis says P2 should stay; P2 swerves → 8 deviations at (S,S).
        assert rep.total_deviation_rounds == 8
        assert rep.deviation_counts_by_joint_cell == (8, 0, 0, 0)
        assert rep.rounds == 8

    def test_p1_swerve_p2_stay_matches_hypothesis_zero_deviations(self):
        sim = GameSimulator()
        r = sim.simulate(
            AlwaysSwerveStrategy("p1"),
            AlwaysStayStrategy("p2"),
            max_rounds=7,
        )
        rep = hypothesis_deviation_report_from_final_state(
            r["final_state"], agent_plays_p1=True
        )
        assert rep.total_deviation_rounds == 0
        assert rep.rounds >= 1

    def test_p2_swerves_when_p1_stays_triggers_deviations_on_stay_rows(self):
        sim = GameSimulator()
        r = sim.simulate(
            AlwaysStayStrategy("p1"),
            AlwaysSwerveStrategy("p2"),
            max_rounds=4,
        )
        rep = hypothesis_deviation_report_from_final_state(
            r["final_state"], agent_plays_p1=True
        )
        # P1 stay → P2 should swerve; P2 swerves → matches hypothesis.
        assert rep.total_deviation_rounds == 0

    def test_both_stay_crashes_deviation_in_stay_stay_cell(self):
        sim = GameSimulator()
        r = sim.simulate(
            AlwaysStayStrategy("p1"),
            AlwaysStayStrategy("p2"),
            max_rounds=3,
        )
        rep = hypothesis_deviation_report_from_final_state(
            r["final_state"], agent_plays_p1=True
        )
        # P1 stay → expect P2 swerve; P2 stays → every round deviates at index 3.
        assert rep.deviation_counts_by_joint_cell == (0, 0, 0, 3)
        assert rep.to_dict()["total_deviation_rounds"] == 3
