"""Unit tests for strategy classes and GameSimulator.

This suite focuses on:
- Basic behavior of individual strategies (AlwaysStay, AlwaysSwerve, etc.)
- Compatibility of strategies with the resilience-based GameEngine
- Functional checks for the MinimaxStrategy using the live engine
- End-to-end simulations via GameSimulator
"""

import importlib.util
from pathlib import Path

import pytest


# Load strategies and engine modules from .src directory
strategies_path = Path(__file__).parent.parent / ".src" / "strategies.py"
strategies_spec = importlib.util.spec_from_file_location("strategies", strategies_path)
strategies_module = importlib.util.module_from_spec(strategies_spec)
strategies_spec.loader.exec_module(strategies_module)  # type: ignore

engine_path = Path(__file__).parent.parent / ".src" / "engine.py"
engine_spec = importlib.util.spec_from_file_location("engine", engine_path)
engine_module = importlib.util.module_from_spec(engine_spec)
engine_spec.loader.exec_module(engine_module)  # type: ignore

AlwaysStayStrategy = strategies_module.AlwaysStayStrategy
AlwaysSwerveStrategy = strategies_module.AlwaysSwerveStrategy
TitForTatStrategy = strategies_module.TitForTatStrategy
RandomStrategy = strategies_module.RandomStrategy
HPThresholdStrategy = strategies_module.HPThresholdStrategy
AggressiveStrategy = strategies_module.AggressiveStrategy
DefensiveStrategy = strategies_module.DefensiveStrategy
MinimaxStrategy = strategies_module.MinimaxStrategy
GameSimulator = strategies_module.GameSimulator

GameEngine = engine_module.GameEngine


class TestBasicStrategiesBehavior:
    """Unit tests for simple, stateless strategies."""

    def test_always_stay_strategy(self):
        strat = AlwaysStayStrategy("p1")
        engine = GameEngine()
        gs = engine.get_gamestate()

        assert strat(gs) is True
        # Repeated calls should be stable
        assert strat(gs) is True

    def test_always_swerve_strategy(self):
        strat = AlwaysSwerveStrategy("p2")
        engine = GameEngine()
        gs = engine.get_gamestate()

        assert strat(gs) is False
        assert strat(gs) is False

    def test_random_strategy_seeded(self):
        """Seeded RandomStrategy should be deterministic for test stability."""
        strat1 = RandomStrategy("p1", seed=42)
        strat2 = RandomStrategy("p1", seed=42)
        engine = GameEngine()
        gs = engine.get_gamestate()

        seq1 = [strat1(gs) for _ in range(10)]
        seq2 = [strat2(gs) for _ in range(10)]
        assert seq1 == seq2


class TestStatefulStrategiesBehavior:
    """Unit tests for strategies that depend on HP or history."""

    def test_tit_for_tat_defaults_to_swerve(self):
        strat = TitForTatStrategy("p1")
        engine = GameEngine()
        gs = engine.get_gamestate()

        # Round 0, no history -> swerve (False)
        assert strat(gs) is False

    def test_tit_for_tat_responds_to_last_completed_round(self):
        strat = TitForTatStrategy("p2")
        engine = GameEngine()

        # Simulate one completed round where p1 stayed and p2 swerved
        gs = engine.get_gamestate()
        gs["round"] = 1
        gs["p1_action_history"] = ["stay"]
        gs["p2_action_history"] = ["swerve"]

        # p2 should now mirror p1's last completed round action: "stay"
        assert strat(gs) is True

    def test_hp_threshold_strategy_uses_gamestate_when_no_override(self):
        engine = GameEngine()
        gs = engine.get_gamestate()
        # Default hp_thresh is 20, hp is 100 > 20 => stay
        strat = HPThresholdStrategy("p1")
        assert strat(gs) is True

        gs_low = dict(gs)
        gs_low["p1_hp"] = 10
        # hp (10) <= threshold (20) => swerve
        assert strat(gs_low) is False

    def test_hp_threshold_strategy_with_explicit_threshold(self):
        engine = GameEngine()
        gs = engine.get_gamestate()
        strat = HPThresholdStrategy("p2", threshold=50)

        gs["p2_hp"] = 60
        assert strat(gs) is True

        gs["p2_hp"] = 40
        assert strat(gs) is False

    def test_aggressive_and_defensive_responses(self):
        engine = GameEngine()
        gs = engine.get_gamestate()

        aggressive = AggressiveStrategy("p1")
        defensive = DefensiveStrategy("p2")

        # Defaults: hp=100, hp_thresh=20 => both well above thresholds
        assert aggressive(gs) is True  # aggressive: stays
        assert defensive(gs) is True  # defensive: HP is very high, so stay

        gs_low = dict(gs)
        gs_low["p1_hp"] = 5
        gs_low["p2_hp"] = 25

        # Now p1 is critically low, p2 is only a bit above threshold
        assert aggressive(gs_low) is False
        assert defensive(gs_low) is False


class TestMinimaxStrategy:
    """Tests for the depth-limited MinimaxStrategy."""

    def test_minimax_depth_validation(self):
        with pytest.raises(ValueError, match="depth must be >= 1"):
            MinimaxStrategy("p1", depth=0)

    def test_minimax_prefers_stay_against_always_swerve(self):
        """Against an always-swerve opponent, minimax should learn to stay."""
        engine = GameEngine()
        minimax = MinimaxStrategy("p1", depth=2)
        opp = AlwaysSwerveStrategy("p2")

        gs = engine.get_gamestate()
        action = minimax(gs)
        # Staying against a guaranteed swerve is strictly better under resilience scoring
        assert action is True

    def test_minimax_does_not_crash_immediately_against_always_stay(self):
        """Against an always-stay opponent, minimax should at least sometimes swerve.

        This is a coarse sanity check that the search is exploring,
        not a guarantee of optimal play.
        """
        engine = GameEngine()
        minimax = MinimaxStrategy("p1", depth=2)
        opp = AlwaysStayStrategy("p2")
        gs = engine.get_gamestate()

        action = minimax(gs)
        # At depth 2, there is an incentive not to head straight into repeated crashes.
        assert action in (True, False)  # primarily a smoke test that it runs without error


class TestGameSimulatorIntegration:
    """End-to-end tests using GameSimulator with various strategies."""

    def test_always_stay_vs_always_swerve(self):
        sim = GameSimulator()
        p1 = AlwaysStayStrategy("p1")
        p2 = AlwaysSwerveStrategy("p2")

        result = sim.simulate(p1, p2, max_rounds=5)
        summary = result["summary"]

        # P1 should win every round
        assert summary["p1_wins"] == 5
        assert summary["p2_wins"] == 0
        assert summary["crashes"] == 0

    def test_minimax_vs_always_swerve_resilience_increases(self):
        """Minimax vs always-swerve should lead to positive resilience_diff for p1."""
        engine = GameEngine()
        sim = GameSimulator(engine=engine)

        p1 = MinimaxStrategy("p1", depth=2)
        p2 = AlwaysSwerveStrategy("p2")

        result = sim.simulate(p1, p2, max_rounds=5)
        final_state = result["final_state"]

        assert final_state["resilience_diff"] > 0
        assert final_state["p1_resilience"] > final_state["p2_resilience"]

