"""Tests for Q-learning training and safe episode cleanup."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SRC = Path(__file__).resolve().parent.parent / ".src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ql_strategy import QLearningStrategy  # noqa: E402
from strategies import AlwaysSwerveStrategy, GameSimulator  # noqa: E402
from train_ql import make_opponent_by_name, train_ql_agent  # noqa: E402


class TestMakeOpponentByName:
    def test_complex_opponents_are_p2(self):
        assert make_opponent_by_name("p2", "tit_for_tat").player == "p2"
        assert make_opponent_by_name("p2", "minimax", minimax_depth=3).depth == 3
        assert make_opponent_by_name("p1", "defensive").player == "p1"


class TestTrainQlAgent:
    def test_short_run_vs_always_swerve(self):
        agent = QLearningStrategy("p1", seed=42)
        _, rows, stats = train_ql_agent(
            agent,
            "always_swerve",
            episodes=8,
            max_rounds=6,
            epsilon_start=0.2,
            epsilon_end=0.1,
        )
        assert len(rows) == 8
        assert stats.episodes == 8
        assert stats.agent_role == "p1"
        assert len(agent.q) > 0

    def test_short_run_vs_tit_for_tat(self):
        agent = QLearningStrategy("p1", seed=7)
        _, _, stats = train_ql_agent(
            agent,
            "tit_for_tat",
            episodes=4,
            max_rounds=5,
        )
        assert stats.episodes == 4
        assert "TitForTat" in stats.opponent


class TestSimulateAbandonOnFailure:
    def test_run_game_exception_abandons_q_learner(self):
        sim = GameSimulator()
        p1 = QLearningStrategy("p1")
        p2 = AlwaysSwerveStrategy("p2")
        p1._prev_s = (2, 2, 2)
        p1._prev_a = False
        p1._res_before_action = 0

        with patch.object(sim.engine, "run_game", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError, match="boom"):
                sim.simulate(p1, p2, max_rounds=3)

        assert p1._prev_s is None
        assert p1._prev_a is None
        assert p1._res_before_action is None
