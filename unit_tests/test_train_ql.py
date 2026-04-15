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
from train_ql import (  # noqa: E402
    _epsilon_for_episode,
    _episode_outcome_from_resilience,
    make_opponent_by_name,
    run_greedy_evaluation_episodes,
    train_ql_agent,
)


class TestMakeOpponentByName:
    def test_complex_opponents_are_p2(self):
        assert make_opponent_by_name("p2", "tit_for_tat").player == "p2"
        assert make_opponent_by_name("p2", "minimax", minimax_depth=3).depth == 3
        assert make_opponent_by_name("p1", "defensive").player == "p1"

    def test_entertainer_name_and_seed(self):
        from strategies import EntertainerStrategy  # noqa: PLC0415

        e = make_opponent_by_name("p2", "entertainer", random_seed=55)
        assert isinstance(e, EntertainerStrategy)
        assert e.player == "p2"


class TestEpisodeOutcomeFromResilience:
    def test_agent_p1_higher_wins(self):
        fs = {"p1_resilience": 30, "p2_resilience": 10}
        assert _episode_outcome_from_resilience(fs, True) == "win"
        assert _episode_outcome_from_resilience(fs, False) == "loss"

    def test_tie_on_equal_resilience(self):
        fs = {"p1_resilience": 5, "p2_resilience": 5}
        assert _episode_outcome_from_resilience(fs, True) == "tie"
        assert _episode_outcome_from_resilience(fs, False) == "tie"

    def test_resilience_diff_overrides_raw_when_present(self):
        fs = {
            "resilience_diff": -3,
            "p1_resilience": 99,
            "p2_resilience": 0,
        }
        assert _episode_outcome_from_resilience(fs, True) == "loss"
        assert _episode_outcome_from_resilience(fs, False) == "win"


class TestEpsilonSchedule:
    def test_linear_endpoints(self):
        assert _epsilon_for_episode(0, 100, 0.25, 0.05) == pytest.approx(0.25)
        assert _epsilon_for_episode(99, 100, 0.25, 0.05) == pytest.approx(0.05)
        mid = _epsilon_for_episode(40, 80, 0.25, 0.05)
        assert mid == pytest.approx(0.25 + (0.05 - 0.25) * (40 / 79))

    def test_single_episode_uses_start_not_end(self):
        assert _epsilon_for_episode(0, 1, 0.25, 0.05) == pytest.approx(0.25)

    def test_schedule_reflected_in_per_episode_rows(self):
        agent = QLearningStrategy("p1", seed=0)
        _, per_ep, _ = train_ql_agent(
            agent,
            "always_swerve",
            episodes=80,
            max_rounds=3,
            epsilon_start=0.25,
            epsilon_end=0.05,
        )
        assert per_ep[0]["epsilon"] == pytest.approx(0.25)
        assert per_ep[-1]["epsilon"] == pytest.approx(0.05)
        assert per_ep[40]["epsilon"] == pytest.approx(
            0.25 + (0.05 - 0.25) * (40 / 79)
        )


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
        assert "resilience_leader" in rows[0]
        assert "resilience_margin_p1_minus_p2" in rows[0]

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


class TestTrainVsHpThresholdOpponent:
    def test_q_learning_accumulates_q_against_hp_threshold(self):
        """HPThreshold swerves when HP is low; margin-based TD fills Q(s,·) exploitably."""

        def q_action_spread(ag: QLearningStrategy) -> float:
            return sum(abs(ag.q[s][False] - ag.q[s][True]) for s in ag.q)

        agent = QLearningStrategy("p1", seed=3)
        assert q_action_spread(agent) == 0.0
        train_ql_agent(
            agent,
            "hp_threshold",
            episodes=120,
            max_rounds=12,
            epsilon_start=0.25,
            epsilon_end=0.05,
        )
        assert len(agent.q) >= 5
        assert q_action_spread(agent) > 40.0


class TestExplorationMatchesEpsilonGreedy:
    def test_constant_epsilon_explore_rate_near_epsilon(self):
        """When start==end, each decide() explores independently with P=ε."""
        agent = QLearningStrategy("p1", seed=2027)
        sink: list = []
        train_ql_agent(
            agent,
            "always_swerve",
            episodes=60,
            max_rounds=12,
            epsilon_start=0.4,
            epsilon_end=0.4,
            training_round_trace_out=sink,
            training_round_trace_max_engine_rounds=50_000,
        )
        flags = [
            r["agent_explored"]
            for r in sink
            if isinstance(r.get("agent_explored"), bool)
        ]
        n = len(flags)
        assert n > 200
        rate = sum(flags) / n
        assert 0.30 < rate < 0.50


class TestRunGreedyEvaluationEpisodes:
    def test_no_learning_and_restores_flags(self):
        agent = QLearningStrategy("p1", seed=3)
        agent.learn = True
        agent.epsilon = 0.2
        train_ql_agent(agent, "always_swerve", episodes=2, max_rounds=4)
        stats = run_greedy_evaluation_episodes(
            agent, "always_swerve", episodes=2, max_rounds=4
        )
        assert stats.episodes == 2
        assert agent.learn is True
        assert agent.epsilon == 0.2


class TestSimulateAbandonOnFailure:
    def test_run_game_exception_abandons_q_learner(self):
        sim = GameSimulator()
        p1 = QLearningStrategy("p1")
        p2 = AlwaysSwerveStrategy("p2")
        p1._prev_s = (2, 2, 2)
        p1._prev_a = False
        p1._margin_before_action = 0.0

        with patch.object(sim.engine, "run_game", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError, match="boom"):
                sim.simulate(p1, p2, max_rounds=3)

        assert p1._prev_s is None
        assert p1._prev_a is None
        assert p1._margin_before_action is None
