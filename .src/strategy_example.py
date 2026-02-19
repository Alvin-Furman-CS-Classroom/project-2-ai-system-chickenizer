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
    GameSimulator
)
from engine import GameEngine  # type: ignore


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
    print("\n")
    
    print("Example 4: Custom Strategy")
    print("-" * 60)
    
    class CustomStrategy(Strategy):
        """Custom strategy that stays on even rounds, swerves on odd rounds."""
        
        def decide(self, gamestate):
            round_num = gamestate.get("round", 0)
            return round_num % 2 == 0
    
    p1_strategy = CustomStrategy("p1")
    p2_strategy = TitForTatStrategy("p2")
    
    result = simulator.simulate(
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy,
        max_rounds=6,
        initial_gamestate=DEFAULT_GAMESTATE.copy()
    )
    
    simulator.print_summary(result)


if __name__ == "__main__":
    main()
