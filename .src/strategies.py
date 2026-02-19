"""
Strategy system for Chickenizer game.

Provides a Strategy base class and concrete strategy implementations that can be
assigned to players and used with the GameEngine to simulate games.
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod


class Strategy(ABC):
    """Base class for player strategies in the Chicken game.
    
    Strategies decide whether a player should "stay" (True) or "swerve" (False)
    based on the current game state. Subclasses should implement the decide()
    method to define specific strategy behaviors.
    """
    
    def __init__(self, player: str):
        """Initialize a strategy for a specific player.
        
        Args:
            player: Player identifier ("p1" or "p2")
        """
        self.player = player
        self.opponent = "p2" if player == "p1" else "p1"
    
    @abstractmethod
    def decide(self, gamestate: Dict[str, Any]) -> bool:
        """Decide whether to stay (True) or swerve (False).
        
        Args:
            gamestate: Current game state dictionary
            
        Returns:
            True to stay, False to swerve
        """
        pass
    
    def __call__(self, gamestate: Dict[str, Any]) -> bool:
        """Make the strategy callable so it can be used with GameEngine.run_game().
        
        Args:
            gamestate: Current game state dictionary
            
        Returns:
            True to stay, False to swerve
        """
        return self.decide(gamestate)


class AlwaysStayStrategy(Strategy):
    """Strategy that always chooses to stay."""
    
    def decide(self, gamestate: Dict[str, Any]) -> bool:
        return True


class AlwaysSwerveStrategy(Strategy):
    """Strategy that always chooses to swerve."""
    
    def decide(self, gamestate: Dict[str, Any]) -> bool:
        return False


class TitForTatStrategy(Strategy):
    """Strategy that mirrors the opponent's action from the last completed round.
    
    Reacts to what the opponent did in the previous round, not their immediately
    previous action. On the first round (round 0), defaults to swerve (cooperation).
    """
    
    def decide(self, gamestate: Dict[str, Any]) -> bool:
        current_round = gamestate.get("round", 0)
        opponent_history = gamestate.get(f"{self.opponent}_action_history", [])
        
        # If we're in round 0 or opponent has no history, default to swerve (cooperate initially)
        if current_round == 0 or not opponent_history:
            return False
        
        # React to opponent's action from the last completed round (round - 1)
        # Each round adds one action to the history, so index (round - 1) is the last completed round
        last_round_index = current_round - 1
        
        # Safety check: ensure we have enough history
        if last_round_index >= len(opponent_history):
            # Fallback to most recent action if history is incomplete
            last_action = opponent_history[-1] if opponent_history else "swerve"
        else:
            last_action = opponent_history[last_round_index]
        
        return last_action == "stay"


class RandomStrategy(Strategy):
    """Strategy that randomly chooses to stay or swerve.
    
    Note: This requires random module. For deterministic behavior, use
    a seeded random number generator.
    """
    
    def __init__(self, player: str, seed: Optional[int] = None):
        """Initialize random strategy.
        
        Args:
            player: Player identifier ("p1" or "p2")
            seed: Optional random seed for reproducibility
        """
        super().__init__(player)
        import random
        if seed is not None:
            random.seed(seed)
        self.random = random
    
    def decide(self, gamestate: Dict[str, Any]) -> bool:
        return self.random.choice([True, False])


class HPThresholdStrategy(Strategy):
    """Strategy that stays only if HP is above a threshold.
    
    If HP is below the threshold, swerves to avoid further damage.
    """
    
    def __init__(self, player: str, threshold: Optional[int] = None):
        """Initialize HP threshold strategy.
        
        Args:
            player: Player identifier ("p1" or "p2")
            threshold: HP threshold. If None, uses player's hp_thresh from gamestate
        """
        super().__init__(player)
        self.threshold = threshold
    
    def decide(self, gamestate: Dict[str, Any]) -> bool:
        threshold = self.threshold or gamestate.get(f"{self.player}_hp_thresh", 20)
        current_hp = gamestate.get(f"{self.player}_hp", 100)
        return current_hp > threshold


class AggressiveStrategy(Strategy):
    """Strategy that stays unless HP is critically low.
    
    More aggressive than HPThresholdStrategy - only swerves when HP
    is very low (below half of hp_thresh).
    """
    
    def decide(self, gamestate: Dict[str, Any]) -> bool:
        hp_thresh = gamestate.get(f"{self.player}_hp_thresh", 20)
        current_hp = gamestate.get(f"{self.player}_hp", 100)
        critical_threshold = hp_thresh // 2
        
        return current_hp > critical_threshold


class DefensiveStrategy(Strategy):
    """Strategy that swerves unless HP is very high.
    
    Only stays when HP is well above the threshold.
    """
    
    def decide(self, gamestate: Dict[str, Any]) -> bool:
        hp_thresh = gamestate.get(f"{self.player}_hp_thresh", 20)
        current_hp = gamestate.get(f"{self.player}_hp", 100)
        safe_threshold = hp_thresh * 2
        
        return current_hp > safe_threshold


class GameSimulator:
    """Simulator for pitting two strategies against each other.
    
    Wraps the GameEngine to provide a convenient interface for running
    games with strategy objects.
    """
    
    def __init__(self, engine=None):
        """Initialize the simulator.
        
        Args:
            engine: Optional GameEngine instance. If None, creates a new one.
        """
        if engine is None:
            try:
                from .engine import GameEngine
            except ImportError:
                from engine import GameEngine
            engine = GameEngine()
        self.engine = engine
    
    def simulate(
        self,
        p1_strategy: Strategy,
        p2_strategy: Strategy,
        max_rounds: int = 10,
        initial_gamestate: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run a game simulation between two strategies.
        
        Args:
            p1_strategy: Strategy object for player 1
            p2_strategy: Strategy object for player 2
            max_rounds: Maximum number of rounds to play
            initial_gamestate: Optional initial game state
            
        Returns:
            Dictionary containing:
                - history: List of gamestate dictionaries
                - final_state: Final gamestate dictionary
                - summary: Dictionary with game summary statistics
        """
        # Ensure strategies are for correct players
        if p1_strategy.player != "p1":
            raise ValueError(f"p1_strategy must have player='p1', got '{p1_strategy.player}'")
        if p2_strategy.player != "p2":
            raise ValueError(f"p2_strategy must have player='p2', got '{p2_strategy.player}'")
        
        # Run the game
        history = self.engine.run_game(
            max_rounds=max_rounds,
            p1_strategy=p1_strategy,
            p2_strategy=p2_strategy,
            initial_gamestate=initial_gamestate
        )
        
        final_state = history[-1] if history else self.engine.get_gamestate()
        
        # Calculate summary statistics
        score = final_state.get("score", [])
        p1_wins = score.count("P1")
        p2_wins = score.count("P2")
        ties = score.count("TIE")
        crashes = score.count("CRASH")
        
        summary = {
            "rounds_played": final_state.get("round", 0),
            "p1_hp": final_state.get("p1_hp", 100),
            "p2_hp": final_state.get("p2_hp", 100),
            "p1_wins": p1_wins,
            "p2_wins": p2_wins,
            "ties": ties,
            "crashes": crashes,
            "p1_strategy": p1_strategy.__class__.__name__,
            "p2_strategy": p2_strategy.__class__.__name__,
        }
        
        return {
            "history": history,
            "final_state": final_state,
            "summary": summary
        }
    
    def print_summary(self, result: Dict[str, Any]):
        """Print a formatted summary of the game simulation.
        
        Args:
            result: Result dictionary from simulate() method
        """
        summary = result["summary"]
        final_state = result["final_state"]
        
        print("=" * 60)
        print("GAME SIMULATION SUMMARY")
        print("=" * 60)
        print(f"P1 Strategy: {summary['p1_strategy']}")
        print(f"P2 Strategy: {summary['p2_strategy']}")
        print(f"Rounds Played: {summary['rounds_played']}")
        print()
        print("Final HP:")
        print(f"  P1: {summary['p1_hp']}")
        print(f"  P2: {summary['p2_hp']}")
        print()
        print("Round Outcomes:")
        print(f"  P1 Wins: {summary['p1_wins']}")
        print(f"  P2 Wins: {summary['p2_wins']}")
        print(f"  Ties: {summary['ties']}")
        print(f"  Crashes: {summary['crashes']}")
        print()
        print("Score History:", final_state.get("score", []))
        print("=" * 60)
