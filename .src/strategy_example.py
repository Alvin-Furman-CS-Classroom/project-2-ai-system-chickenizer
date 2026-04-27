"""Example usage of the Strategy system for Chickenizer.

Demonstrates how to create strategy objects and pit them against each other
using the GameSimulator.
"""

import sys
from pathlib import Path

# Ensure .src directory is in path for imports
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from strategies import (  # type: ignore
    Strategy,
    AlwaysStayStrategy,
    AlwaysSwerveStrategy,
    TitForTatStrategy,
    HPThresholdStrategy,
    AggressiveStrategy,
    DefensiveStrategy,
    MinimaxStrategy,
    GameSimulator,
)
from engine import GameEngine  # type: ignore
from nash_normal_form import analyze_normal_form, format_nash_table  # type: ignore


# Default gamestate with full HP for resetting between games
DEFAULT_GAMESTATE = {
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
    "score": [],
}


def print_resilience_summary(result):
    """Print resilience scores (U) for both players.
    
    Shows the final resilience for each player and the differential U used by
    minimax (U = p1_resilience - p2_resilience).
    """
    final_state = result["final_state"]
    p1_res = final_state.get("p1_resilience", 0)
    p2_res = final_state.get("p2_resilience", 0)
    u = final_state.get("resilience_diff", p1_res - p2_res)
    
    print("Resilience / Utility (U):")
    print(f"  P1 resilience: {p1_res}")
    print(f"  P2 resilience: {p2_res}")
    print(f"  U = P1 - P2:  {u}")
    print("=" * 60)


def main():
    """Run example game simulations."""
    
    print("Example 1: Always Stay vs Always Swerve")
    print("-" * 60)
    
    # Create strategies
    p1_strategy = AlwaysStayStrategy("p1")
    p2_strategy = AlwaysSwerveStrategy("p2")
    
    # Create simulator
    simulator = GameSimulator()
    
    # Run simulation with fresh gamestate (resets HP)
    result = simulator.simulate(
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy,
        max_rounds=5,
        initial_gamestate=DEFAULT_GAMESTATE.copy()
    )
    
    simulator.print_summary(result)
    print_resilience_summary(result)
    print("\n")
    
    print("Example 2: Tit-for-Tat vs Aggressive")
    print("-" * 60)
    
    p1_strategy = TitForTatStrategy("p1")
    p2_strategy = AggressiveStrategy("p2")
    
    result = simulator.simulate(
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy,
        max_rounds=10,
        initial_gamestate=DEFAULT_GAMESTATE.copy()
    )
    
    simulator.print_summary(result)
    print_resilience_summary(result)
    print("\n")
    
    print("Example 3: HP Threshold vs Defensive")
    print("-" * 60)
    
    p1_strategy = HPThresholdStrategy("p1", threshold=30)
    p2_strategy = DefensiveStrategy("p2")
    
    result = simulator.simulate(
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy,
        max_rounds=8,
        initial_gamestate=DEFAULT_GAMESTATE.copy()
    )
    
    simulator.print_summary(result)
    print_resilience_summary(result)
    print("\n")
    
    print("Example 4: Custom Strategy")
    print("-" * 60)
    
    class CustomStrategy(Strategy):
        """Custom strategy that stays on even rounds, swerves on odd rounds."""
        
        def decide(self, gamestate):
            round_num = gamestate.get("round", 0)
            return round_num % 2 == 0
    
    p1_strategy = AggressiveStrategy("p1")
    p2_strategy = TitForTatStrategy("p2")
    
    result = simulator.simulate(
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy,
        max_rounds=6,
        initial_gamestate=DEFAULT_GAMESTATE.copy(),
    )
    
    simulator.print_summary(result)
    print_resilience_summary(result)
    print("\n")

    print("Example 5: Minimax vs Always Swerve")
    print("-" * 60)

    p1_strategy = MinimaxStrategy("p1", depth=2)
    p2_strategy = AlwaysSwerveStrategy("p2")

    result = simulator.simulate(
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy,
        max_rounds=8,
        initial_gamestate=DEFAULT_GAMESTATE.copy(),
    )

    simulator.print_summary(result)
    print_resilience_summary(result)
    print("\n")

    print("Example 6: Minimax vs Always Stay")
    print("-" * 60)

    p1_strategy = MinimaxStrategy("p1", depth=2)
    p2_strategy = AlwaysStayStrategy("p2")

    result = simulator.simulate(
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy,
        max_rounds=8,
        initial_gamestate=DEFAULT_GAMESTATE.copy(),
    )

    simulator.print_summary(result)
    print_resilience_summary(result)
    print("\n")

    print("Example 7: Minimax vs Tit-for-Tat")
    print("-" * 60)

    p1_strategy = MinimaxStrategy("p1", depth=2)
    p2_strategy = TitForTatStrategy("p2")

    result = simulator.simulate(
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy,
        max_rounds=10,
        initial_gamestate=DEFAULT_GAMESTATE.copy(),
    )

    simulator.print_summary(result)
    print_resilience_summary(result)
    print("\n")

    print("Example 8: Minimax vs Defensive")
    print("-" * 60)

    p1_strategy = MinimaxStrategy("p1", depth=2)
    p2_strategy = DefensiveStrategy("p2")

    result = simulator.simulate(
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy,
        max_rounds=10,
        initial_gamestate=DEFAULT_GAMESTATE.copy(),
    )

    simulator.print_summary(result)
    print_resilience_summary(result)
    print("\n")

    print("Example 9: Minimax (no HP care) vs Always Stay (HP care)")
    print("-" * 60)

    # MinimaxStrategy does not imply HP preferences (hp_delta stays at 0),
    # while we manually configure the AlwaysStay player to care about HP by
    # setting its hp_delta preference to a non-zero value.

    p1_strategy = MinimaxStrategy("p1", depth=2)
    p2_strategy = AlwaysStayStrategy("p2")

    # Start from engine's default gamestate so we get preference dicts.
    engine = GameEngine()
    initial_state = engine.get_gamestate()
    # P1: only cares about round outcomes
    initial_state["p1_preferences"]["hp_delta"] = 0
    # P2: also cares about HP gain/loss
    initial_state["p2_preferences"]["hp_delta"] = 1

    result = simulator.simulate(
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy,
        max_rounds=10,
        initial_gamestate=initial_state,
    )

    simulator.print_summary(result)
    print_resilience_summary(result)
    print("\n")

    print("Example 10: Aggressive (HP care) vs Minimax (no HP care)")
    print("-" * 60)

    # Player 1 uses the Aggressive HP-based strategy and explicitly cares
    # about HP changes; Player 2 uses Minimax but is configured to ignore HP
    # (hp_delta = 0), caring only about game outcomes.

    p1_strategy = AggressiveStrategy("p1")
    p2_strategy = MinimaxStrategy("p2", depth=2)

    engine = GameEngine()
    initial_state = engine.get_gamestate()
    # P1: cares about HP as well as round outcomes
    initial_state["p1_preferences"]["hp_delta"] = 1
    # P2: cares only about round outcomes
    initial_state["p2_preferences"]["hp_delta"] = 0

    result = simulator.simulate(
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy,
        max_rounds=10,
        initial_gamestate=initial_state,
    )

    simulator.print_summary(result)
    print_resilience_summary(result)
    print("\n")

    print("Example 11: Always Stay vs Minimax (P2)")
    print("-" * 60)

    # Here the naive player (P1) is AlwaysStay, while P2 uses MinimaxStrategy.
    # Preferences are taken from the engine defaults, so both players care
    # about game outcomes, and minimax evaluates actions accordingly.

    p1_strategy = AlwaysStayStrategy("p1")
    p2_strategy = MinimaxStrategy("p2", depth=2)

    result = simulator.simulate(
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy,
        max_rounds=8,
        initial_gamestate=DEFAULT_GAMESTATE.copy(),
    )

    simulator.print_summary(result)
    print_resilience_summary(result)
    print("\n")

    print("Example 12: Minimax (HP care) vs Always Swerve (no HP care)")
    print("-" * 60)

    # Here we invert the situation: P1 (minimax) is configured to care about
    # HP changes, while P2 (AlwaysSwerve) only cares about round outcomes.

    p1_strategy = MinimaxStrategy("p1", depth=2)
    p2_strategy = AlwaysSwerveStrategy("p2")

    engine = GameEngine()
    initial_state = engine.get_gamestate()
    # P1: cares about HP as well as game results
    initial_state["p1_preferences"]["hp_delta"] = 1
    # P2: cares only about game results
    initial_state["p2_preferences"]["hp_delta"] = 0

    result = simulator.simulate(
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy,
        max_rounds=10,
        initial_gamestate=initial_state,
    )

    simulator.print_summary(result)
    print_resilience_summary(result)
    print("\n")

    print("Example 13: One-shot normal form & Nash (simultaneous round abstraction)")
    print("-" * 60)
    print(
        "Payoffs are resilience after one counterfactual round per action pair.\n"
        "This is not the same as turn-based run_game (P1 moves, then P2).\n"
    )
    nash_result = analyze_normal_form(
        AlwaysSwerveStrategy("p1"),
        AlwaysSwerveStrategy("p2"),
        include_mixed=True,
    )
    print(format_nash_table(nash_result))


if __name__ == "__main__":
    main()
