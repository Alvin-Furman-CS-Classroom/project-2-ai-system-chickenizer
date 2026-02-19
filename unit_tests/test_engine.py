"""Unit tests for GameEngine class.

This test suite is organized into the following test classes:
- TestGameEngineInitialization: Engine initialization with default and custom gamestates
- TestGameEngineGamestate: get_gamestate() and generate_gamestate() methods
- TestGameEngineActions: play_action() method and action history tracking
- TestGameEngineGameLoop: run_game() method and full game loop functionality
- TestGameEngineCrashDamage: Crash damage application when both players stay
- TestGameEngineRoundTracking: Round counter and round incrementing
- TestGameEngineErrorHandling: Error cases and invalid inputs
- TestGameEngineLegacyMethods: step() method for backward compatibility

Tests cover initialization, gamestate management, action handling, game loop execution,
crash damage, round tracking, error handling, and action history tracking.
"""

import pytest
import sys
import importlib.util
from pathlib import Path
from copy import deepcopy

# Load module from .src directory
src_path = Path(__file__).parent.parent / ".src" / "engine.py"
spec = importlib.util.spec_from_file_location("engine", src_path)
engine_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine_module)

GameEngine = engine_module.GameEngine


class TestGameEngineInitialization:
    """Test cases for GameEngine initialization."""
    
    def test_initialization_default(self):
        """Test that engine initializes with default gamestate."""
        engine = GameEngine()
        gamestate = engine.get_gamestate()
        
        assert gamestate["p1_stay"] == False
        assert gamestate["p2_stay"] == False
        assert gamestate["p1_hp"] == 100
        assert gamestate["p2_hp"] == 100
        assert gamestate["p1_hp_thresh"] == 20
        assert gamestate["p2_hp_thresh"] == 20
        assert gamestate["p1_crash_dmg"] == 10
        assert gamestate["p2_crash_dmg"] == 10
        assert gamestate["round"] == 0
        assert gamestate["p1_action_history"] == []
        assert gamestate["p2_action_history"] == []
    
    def test_initialization_custom_gamestate(self):
        """Test initialization with custom gamestate."""
        custom_state = {
            "p1_stay": True,
            "p2_stay": False,
            "p1_hp": 80,
            "p2_hp": 90,
            "p1_hp_thresh": 15,
            "p2_hp_thresh": 25,
            "p1_crash_dmg": 15,
            "p2_crash_dmg": 12,
            "round": 5,
            "p1_action_history": ["stay", "swerve"],
            "p2_action_history": ["swerve"],
        }
        engine = GameEngine(custom_state)
        gamestate = engine.get_gamestate()
        
        assert gamestate["p1_stay"] == True
        assert gamestate["p2_stay"] == False
        assert gamestate["p1_hp"] == 80
        assert gamestate["p2_hp"] == 90
        assert gamestate["round"] == 5
        assert gamestate["p1_action_history"] == ["stay", "swerve"]
        assert gamestate["p2_action_history"] == ["swerve"]
    
    def test_initialization_partial_gamestate(self):
        """Test initialization with partial gamestate fills in defaults."""
        partial_state = {
            "p1_hp": 50,
            "p2_hp": 60,
        }
        engine = GameEngine(partial_state)
        gamestate = engine.get_gamestate()
        
        assert gamestate["p1_hp"] == 50
        assert gamestate["p2_hp"] == 60
        assert gamestate["p1_stay"] == False  # Default value
        assert gamestate["round"] == 0  # Default value
        assert gamestate["p1_action_history"] == []  # Default value
    
    def test_initialization_unexpected_key(self):
        """Test that unexpected keys raise ValueError."""
        invalid_state = {
            "p1_stay": False,
            "p2_stay": False,
            "p1_hp": 100,
            "p2_hp": 100,
            "p1_hp_thresh": 20,
            "p2_hp_thresh": 20,
            "p1_crash_dmg": 10,
            "p2_crash_dmg": 10,
            "round": 0,
            "p1_action_history": [],
            "p2_action_history": [],
            "invalid_key": "invalid_value",
        }
        with pytest.raises(ValueError, match="Unexpected key"):
            GameEngine(invalid_state)
    
    def test_initialization_type_mismatch(self):
        """Test that type mismatches raise ValueError."""
        invalid_state = {
            "p1_stay": "not_a_bool",  # Should be bool
            "p2_stay": False,
            "p1_hp": 100,
            "p2_hp": 100,
            "p1_hp_thresh": 20,
            "p2_hp_thresh": 20,
            "p1_crash_dmg": 10,
            "p2_crash_dmg": 10,
            "round": 0,
            "p1_action_history": [],
            "p2_action_history": [],
        }
        with pytest.raises(ValueError, match="Value type"):
            GameEngine(invalid_state)
    
    def test_initialization_gamestate_history(self):
        """Test that gamestate_history is initialized with initial state."""
        engine = GameEngine()
        assert len(engine.gamestate_history) == 1
        assert engine.gamestate_history[0]["round"] == 0


class TestGameEngineGamestate:
    """Test cases for get_gamestate() and generate_gamestate() methods."""
    
    def test_get_gamestate_returns_copy(self):
        """Test that get_gamestate() returns a deep copy."""
        engine = GameEngine()
        gamestate1 = engine.get_gamestate()
        gamestate2 = engine.get_gamestate()
        
        # Modify the returned copy
        gamestate1["p1_hp"] = 999
        
        # Original gamestate should be unchanged
        assert engine.get_gamestate()["p1_hp"] == 100
        assert gamestate2["p1_hp"] == 100
    
    def test_generate_gamestate_no_increment(self):
        """Test generate_gamestate() without incrementing round."""
        engine = GameEngine()
        initial_round = engine.get_gamestate()["round"]
        
        gamestate = engine.generate_gamestate(increment_round=False)
        
        assert gamestate["round"] == initial_round
        assert len(engine.gamestate_history) == 2  # Initial + one generated
    
    def test_generate_gamestate_increment_round(self):
        """Test generate_gamestate() with incrementing round."""
        engine = GameEngine()
        initial_round = engine.get_gamestate()["round"]
        
        gamestate = engine.generate_gamestate(increment_round=True)
        
        assert gamestate["round"] == initial_round + 1
        assert engine.get_gamestate()["round"] == initial_round + 1
    
    def test_generate_gamestate_adds_to_history(self):
        """Test that generate_gamestate() adds to history."""
        engine = GameEngine()
        initial_history_len = len(engine.gamestate_history)
        
        engine.generate_gamestate(increment_round=False)
        assert len(engine.gamestate_history) == initial_history_len + 1
        
        engine.generate_gamestate(increment_round=True)
        assert len(engine.gamestate_history) == initial_history_len + 2


class TestGameEngineActions:
    """Test cases for play_action() method and action history."""
    
    def test_play_action_p1_stay(self):
        """Test playing stay action for p1."""
        engine = GameEngine()
        gamestate = engine.play_action("p1", True)
        
        assert gamestate["p1_stay"] == True
        assert engine.get_gamestate()["p1_stay"] == True
        assert gamestate["p1_action_history"] == ["stay"]
        assert engine.get_gamestate()["p1_action_history"] == ["stay"]
    
    def test_play_action_p1_swerve(self):
        """Test playing swerve action for p1."""
        engine = GameEngine()
        gamestate = engine.play_action("p1", False)
        
        assert gamestate["p1_stay"] == False
        assert gamestate["p1_action_history"] == ["swerve"]
    
    def test_play_action_p2(self):
        """Test playing action for p2."""
        engine = GameEngine()
        gamestate = engine.play_action("p2", True)
        
        assert gamestate["p2_stay"] == True
        assert gamestate["p2_action_history"] == ["stay"]
    
    def test_play_action_history_accumulation(self):
        """Test that action history accumulates multiple actions."""
        engine = GameEngine()
        
        engine.play_action("p1", True)
        engine.play_action("p1", False)
        engine.play_action("p1", True)
        
        history = engine.get_gamestate()["p1_action_history"]
        assert history == ["stay", "swerve", "stay"]
    
    def test_play_action_both_players_separate_histories(self):
        """Test that p1 and p2 have separate action histories."""
        engine = GameEngine()
        
        engine.play_action("p1", True)
        engine.play_action("p2", False)
        engine.play_action("p1", False)
        engine.play_action("p2", True)
        
        gamestate = engine.get_gamestate()
        assert gamestate["p1_action_history"] == ["stay", "swerve"]
        assert gamestate["p2_action_history"] == ["swerve", "stay"]
    
    def test_play_action_invalid_player(self):
        """Test that invalid player raises ValueError."""
        engine = GameEngine()
        
        with pytest.raises(ValueError, match="Player must be 'p1' or 'p2'"):
            engine.play_action("p3", True)
        
        with pytest.raises(ValueError, match="Player must be 'p1' or 'p2'"):
            engine.play_action("invalid", False)
    
    def test_play_action_returns_copy(self):
        """Test that play_action() returns a copy of gamestate."""
        engine = GameEngine()
        gamestate = engine.play_action("p1", True)
        
        # Modify returned gamestate
        gamestate["p1_hp"] = 999
        
        # Original should be unchanged
        assert engine.get_gamestate()["p1_hp"] == 100


class TestGameEngineCrashDamage:
    """Test cases for crash damage application."""
    
    def test_crash_damage_both_stay(self):
        """Test that crash damage is applied when both players stay."""
        engine = GameEngine()
        initial_p1_hp = engine.get_gamestate()["p1_hp"]
        initial_p2_hp = engine.get_gamestate()["p2_hp"]
        crash_dmg = engine.get_gamestate()["p1_crash_dmg"]
        
        engine.play_action("p1", True)
        engine.play_action("p2", True)
        engine.generate_gamestate(increment_round=True)
        
        gamestate = engine.get_gamestate()
        assert gamestate["p1_hp"] == initial_p1_hp - crash_dmg
        assert gamestate["p2_hp"] == initial_p2_hp - crash_dmg
    
    def test_crash_damage_p1_stays_p2_swerves(self):
        """Test that no crash damage when only p1 stays."""
        engine = GameEngine()
        initial_p1_hp = engine.get_gamestate()["p1_hp"]
        initial_p2_hp = engine.get_gamestate()["p2_hp"]
        
        engine.play_action("p1", True)
        engine.play_action("p2", False)
        engine.generate_gamestate(increment_round=True)
        
        gamestate = engine.get_gamestate()
        assert gamestate["p1_hp"] == initial_p1_hp
        assert gamestate["p2_hp"] == initial_p2_hp
    
    def test_crash_damage_both_swerve(self):
        """Test that no crash damage when both players swerve."""
        engine = GameEngine()
        initial_p1_hp = engine.get_gamestate()["p1_hp"]
        initial_p2_hp = engine.get_gamestate()["p2_hp"]
        
        engine.play_action("p1", False)
        engine.play_action("p2", False)
        engine.generate_gamestate(increment_round=True)
        
        gamestate = engine.get_gamestate()
        assert gamestate["p1_hp"] == initial_p1_hp
        assert gamestate["p2_hp"] == initial_p2_hp
    
    def test_crash_damage_multiple_rounds(self):
        """Test crash damage accumulates over multiple rounds."""
        engine = GameEngine()
        initial_p1_hp = engine.get_gamestate()["p1_hp"]
        crash_dmg = engine.get_gamestate()["p1_crash_dmg"]
        
        # Both stay for 3 rounds
        for _ in range(3):
            engine.play_action("p1", True)
            engine.play_action("p2", True)
            engine.generate_gamestate(increment_round=True)
        
        gamestate = engine.get_gamestate()
        assert gamestate["p1_hp"] == initial_p1_hp - (3 * crash_dmg)
    
    def test_crash_damage_custom_values(self):
        """Test crash damage with custom damage values."""
        custom_state = {
            "p1_stay": False,
            "p2_stay": False,
            "p1_hp": 100,
            "p2_hp": 100,
            "p1_hp_thresh": 20,
            "p2_hp_thresh": 20,
            "p1_crash_dmg": 25,
            "p2_crash_dmg": 30,
            "round": 0,
            "p1_action_history": [],
            "p2_action_history": [],
        }
        engine = GameEngine(custom_state)
        
        engine.play_action("p1", True)
        engine.play_action("p2", True)
        engine.generate_gamestate(increment_round=True)
        
        gamestate = engine.get_gamestate()
        assert gamestate["p1_hp"] == 75  # 100 - 25
        assert gamestate["p2_hp"] == 70  # 100 - 30


class TestGameEngineRoundTracking:
    """Test cases for round counter tracking."""
    
    def test_round_starts_at_zero(self):
        """Test that round starts at 0."""
        engine = GameEngine()
        assert engine.get_gamestate()["round"] == 0
    
    def test_round_increments_on_generate(self):
        """Test that round increments when generate_gamestate(increment_round=True)."""
        engine = GameEngine()
        
        engine.generate_gamestate(increment_round=True)
        assert engine.get_gamestate()["round"] == 1
        
        engine.generate_gamestate(increment_round=True)
        assert engine.get_gamestate()["round"] == 2
    
    def test_round_does_not_increment_without_flag(self):
        """Test that round doesn't increment without increment_round=True."""
        engine = GameEngine()
        initial_round = engine.get_gamestate()["round"]
        
        engine.generate_gamestate(increment_round=False)
        assert engine.get_gamestate()["round"] == initial_round
        
        engine.generate_gamestate(increment_round=False)
        assert engine.get_gamestate()["round"] == initial_round


class TestGameEngineGameLoop:
    """Test cases for run_game() method."""
    
    def test_run_game_simple_strategies(self):
        """Test running game with simple always-stay strategies."""
        engine = GameEngine()
        
        def always_stay(gs):
            return True
        
        history = engine.run_game(
            max_rounds=3,
            p1_strategy=always_stay,
            p2_strategy=always_stay
        )
        
        # Should have multiple gamestates (initial + after each action/round)
        assert len(history) > 3
        
        # Final round should be 3
        final_state = history[-1]
        assert final_state["round"] == 3
    
    def test_run_game_always_swerve(self):
        """Test running game with always-swerve strategies."""
        engine = GameEngine()
        
        def always_swerve(gs):
            return False
        
        history = engine.run_game(
            max_rounds=2,
            p1_strategy=always_swerve,
            p2_strategy=always_swerve
        )
        
        final_state = history[-1]
        assert final_state["round"] == 2
        assert final_state["p1_stay"] == False
        assert final_state["p2_stay"] == False
    
    def test_run_game_action_histories(self):
        """Test that action histories are tracked during run_game()."""
        engine = GameEngine()
        
        def always_stay(gs):
            return True
        
        history = engine.run_game(
            max_rounds=3,
            p1_strategy=always_stay,
            p2_strategy=always_stay
        )
        
        final_state = history[-1]
        # Each player should have 3 actions (one per round)
        assert len(final_state["p1_action_history"]) == 3
        assert len(final_state["p2_action_history"]) == 3
        assert all(a == "stay" for a in final_state["p1_action_history"])
        assert all(a == "stay" for a in final_state["p2_action_history"])
    
    def test_run_game_resets_on_start(self):
        """Test that run_game() resets action flags and history."""
        engine = GameEngine()
        
        # Set some initial state
        engine.play_action("p1", True)
        engine.play_action("p2", True)
        engine.step("round", 5)
        
        def always_swerve(gs):
            return False
        
        history = engine.run_game(
            max_rounds=2,
            p1_strategy=always_swerve,
            p2_strategy=always_swerve
        )
        
        # Should start fresh
        assert history[0]["round"] == 0
        assert history[0]["p1_action_history"] == []
        assert history[0]["p2_action_history"] == []
    
    def test_run_game_with_initial_gamestate(self):
        """Test run_game() with custom initial gamestate."""
        custom_state = {
            "p1_stay": False,
            "p2_stay": False,
            "p1_hp": 50,
            "p2_hp": 60,
            "p1_hp_thresh": 20,
            "p2_hp_thresh": 20,
            "p1_crash_dmg": 10,
            "p2_crash_dmg": 10,
            "round": 0,
            "p1_action_history": [],
            "p2_action_history": [],
        }
        
        engine = GameEngine()
        
        def always_stay(gs):
            return True
        
        history = engine.run_game(
            max_rounds=1,
            p1_strategy=always_stay,
            p2_strategy=always_stay,
            initial_gamestate=custom_state
        )
        
        # Should start with custom HP values
        assert history[0]["p1_hp"] == 50
        assert history[0]["p2_hp"] == 60
    
    def test_run_game_strategy_receives_gamestate(self):
        """Test that strategies receive gamestate as argument."""
        engine = GameEngine()
        received_gamestates = []
        
        def strategy(gs):
            received_gamestates.append(deepcopy(gs))
            return True
        
        engine.run_game(
            max_rounds=2,
            p1_strategy=strategy,
            p2_strategy=strategy
        )
        
        # Strategies should receive gamestate
        assert len(received_gamestates) > 0
        assert "round" in received_gamestates[0]
        assert "p1_hp" in received_gamestates[0]


class TestGameEngineErrorHandling:
    """Test cases for error handling."""
    
    def test_is_game_over_currently_returns_false(self):
        """Test that is_game_over() currently always returns False."""
        engine = GameEngine()
        is_over, reason = engine.is_game_over()
        
        assert is_over == False
        assert reason is None
    
    def test_step_invalid_key(self):
        """Test that step() raises ValueError for invalid key."""
        engine = GameEngine()
        
        with pytest.raises(ValueError, match="not found in gamestate"):
            engine.step("invalid_key", 100)
    
    def test_step_type_mismatch(self):
        """Test that step() raises ValueError for type mismatch."""
        engine = GameEngine()
        
        with pytest.raises(ValueError, match="does not match gamestate type"):
            engine.step("p1_hp", "not_an_int")  # p1_hp should be int


class TestGameEngineLegacyMethods:
    """Test cases for legacy step() method."""
    
    def test_step_updates_gamestate(self):
        """Test that step() updates gamestate correctly."""
        engine = GameEngine()
        
        gamestate = engine.step("p1_hp", 75)
        
        assert gamestate["p1_hp"] == 75
        assert engine.get_gamestate()["p1_hp"] == 75
    
    def test_step_returns_copy(self):
        """Test that step() returns a copy of gamestate."""
        engine = GameEngine()
        gamestate = engine.step("p1_hp", 75)
        
        # Modify returned copy
        gamestate["p2_hp"] = 999
        
        # Original should be unchanged
        assert engine.get_gamestate()["p2_hp"] == 100


class TestGameEngineIntegration:
    """Integration tests combining multiple features."""
    
    def test_full_game_scenario(self):
        """Test a complete game scenario with multiple rounds and crash damage."""
        engine = GameEngine()
        
        def p1_strategy(gs):
            # Stay if round is even
            return gs["round"] % 2 == 0
        
        def p2_strategy(gs):
            # Always stay
            return True
        
        history = engine.run_game(
            max_rounds=5,
            p1_strategy=p1_strategy,
            p2_strategy=p2_strategy
        )
        
        final_state = history[-1]
        
        # Verify round count
        assert final_state["round"] == 5
        
        # Verify action histories
        assert len(final_state["p1_action_history"]) == 5
        assert len(final_state["p2_action_history"]) == 5
        
        # Verify HP decreased due to crashes (when both stayed)
        # P1 stays on rounds 0, 2, 4 (even rounds)
        # P2 always stays
        # So crashes occur on rounds 0, 2, 4
        expected_damage = 3 * 10  # 3 crashes * 10 damage
        assert final_state["p1_hp"] == 100 - expected_damage
        assert final_state["p2_hp"] == 100 - expected_damage
    
    def test_gamestate_isolation(self):
        """Test that gamestates are properly isolated (no shared references)."""
        engine = GameEngine()
        
        # Get multiple gamestate copies
        gs1 = engine.get_gamestate()
        gs2 = engine.get_gamestate()
        gs3 = engine.play_action("p1", True)
        
        # Modify one copy
        gs1["p1_hp"] = 999
        gs2["p2_hp"] = 888
        
        # Others should be unaffected
        assert gs3["p1_hp"] == 100
        assert engine.get_gamestate()["p1_hp"] == 100
        assert engine.get_gamestate()["p2_hp"] == 100
