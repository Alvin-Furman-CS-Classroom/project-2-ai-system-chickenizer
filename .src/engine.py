"""
Game engine for Chickenizer.

Manages the game loop for the Chicken game, generating gamestates and handling
player actions in a turn-based sequence. The engine alternates between players
until a round threshold is reached or game over conditions are met.
"""

from typing import Callable, Optional, Dict, Any, List
from copy import deepcopy


class GameEngine:
    """Game engine for managing Chicken game state and turn-based gameplay.
    
    The engine maintains the current game state and executes a game loop where
    players alternate actions. After each action, a new gamestate is generated
    reflecting the updated game state.
    """
    
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
    }
    
    def __init__(self, gamestate: Optional[Dict[str, Any]] = None):
        """Initialize the game engine with a gamestate.
        
        Args:
            gamestate: Optional initial game state dictionary. If None, uses
                DEFAULT_GAMESTATE. Must contain all keys from DEFAULT_GAMESTATE.
        
        Raises:
            ValueError: If gamestate contains unexpected keys or type mismatches.
        """
        if gamestate is None:
            gamestate = deepcopy(self.DEFAULT_GAMESTATE)
        
        # Ensure type consistency
        for key, value in gamestate.items():
            if key not in self.DEFAULT_GAMESTATE:
                raise ValueError(f"Unexpected key {key} in gamestate")
            if type(value) != type(self.DEFAULT_GAMESTATE[key]):
                raise ValueError(
                    f"Value type {type(value)} does not match expected gamestate "
                    f"type {type(self.DEFAULT_GAMESTATE[key])} for key {key}"
                )
        
        # Ensure all required keys are present
        for key in self.DEFAULT_GAMESTATE:
            if key not in gamestate:
                gamestate[key] = deepcopy(self.DEFAULT_GAMESTATE[key])
        
        self.gamestate = gamestate
        self.gamestate_history: List[Dict[str, Any]] = [deepcopy(self.gamestate)]
    
    def get_gamestate(self) -> Dict[str, Any]:
        """Get the current game state.
        
        Returns:
            A copy of the current gamestate dictionary.
        """
        return deepcopy(self.gamestate)
    
    def generate_gamestate(self, increment_round: bool = False) -> Dict[str, Any]:
        """Generate and return the current gamestate.
        
        This method updates the gamestate based on current game conditions
        (e.g., applying crash damage if both players stayed) and returns
        a copy of the updated state.
        
        Args:
            increment_round: If True, increments the round counter and applies
                round-end effects (crash damage). Should only
                be True after both players have acted.
        
        Returns:
            A copy of the updated gamestate dictionary.
        """
        if increment_round:
            # Apply crash damage if both players stayed
            if self.gamestate["p1_stay"] and self.gamestate["p2_stay"]:
                self.gamestate["p1_hp"] -= self.gamestate["p1_crash_dmg"]
                self.gamestate["p2_hp"] -= self.gamestate["p2_crash_dmg"]
            
            # Increment round counter
            self.gamestate["round"] += 1
        
        # Save to history
        self.gamestate_history.append(deepcopy(self.gamestate))
        
        return self.get_gamestate()
    
    def play_action(self, player: str, action: bool) -> Dict[str, Any]:
        """Execute a player's action and update the gamestate.
        
        Args:
            player: Player identifier ("p1" or "p2").
            action: True for "stay", False for "swerve".
        
        Returns:
            A copy of the updated gamestate dictionary.
        
        Raises:
            ValueError: If player is not "p1" or "p2".
        """
        if player not in ["p1", "p2"]:
            raise ValueError(f"Player must be 'p1' or 'p2', got '{player}'")
        
        self.gamestate[f"{player}_stay"] = action
        # Append action to player's history
        action_str = "stay" if action else "swerve"
        self.gamestate[f"{player}_action_history"].append(action_str)
        
        return self.get_gamestate()
    
    def is_game_over(self) -> tuple[bool, Optional[str]]:
        """Check if the game should end.
        
        Returns:
            A tuple (is_over, reason) where:
            - is_over: True if game should end, False otherwise
            - reason: String describing why game ended, or None if not over
        
        Note:
            Currently only checks round-based termination. Future implementations
            can add HP-based termination (e.g., if p1_hp <= 0 or p2_hp <= 0).
        """
        # Placeholder for HP-based game over conditions
        # Future: Check if either player's HP <= 0
        # if self.gamestate["p1_hp"] <= 0:
        #     return True, "p1_hp_zero"
        # if self.gamestate["p2_hp"] <= 0:
        #     return True, "p2_hp_zero"
        
        # For now, game over is only checked externally via round count
        return False, None
    
    def run_game(
        self,
        max_rounds: int,
        p1_strategy: Callable[[Dict[str, Any]], bool],
        p2_strategy: Callable[[Dict[str, Any]], bool],
        initial_gamestate: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Run the game loop until max_rounds is reached or game over.
        
        The loop alternates between players: p1 acts, then p2 acts, then
        a new gamestate is generated. This continues until max_rounds is
        reached or is_game_over() returns True.
        
        Args:
            max_rounds: Maximum number of rounds to play.
            p1_strategy: Callable that takes gamestate and returns True (stay)
                or False (swerve) for player 1.
            p2_strategy: Callable that takes gamestate and returns True (stay)
                or False (swerve) for player 2.
            initial_gamestate: Optional initial gamestate. If provided, resets
                the engine to this state before starting.
        
        Returns:
            List of gamestate dictionaries representing the game history.
            Each gamestate is a snapshot after both players have acted.
        """
        # Reset to initial state if provided
        if initial_gamestate is not None:
            self.__init__(initial_gamestate)
        
        # Reset action flags and history for new game
        self.gamestate["p1_stay"] = False
        self.gamestate["p2_stay"] = False
        self.gamestate["round"] = 0
        self.gamestate["p1_action_history"] = []
        self.gamestate["p2_action_history"] = []
        
        while self.gamestate["round"] < max_rounds:
            # Check for game over conditions
            is_over, reason = self.is_game_over()
            if is_over:
                break
            
            # Generate initial gamestate for this round (before any actions)
            current_state = self.generate_gamestate(increment_round=False)
            
            # Player 1 acts
            p1_action = p1_strategy(current_state)
            self.play_action("p1", p1_action)
            
            # Generate gamestate after p1's action (for p2 to see)
            current_state = self.generate_gamestate(increment_round=False)
            
            # Player 2 acts
            p2_action = p2_strategy(current_state)
            self.play_action("p2", p2_action)
            
            # Generate final gamestate for this round (applies crash damage, increments round)
            self.generate_gamestate(increment_round=True)
        
        return self.gamestate_history
    
    def step(self, key: str, value: Any) -> Dict[str, Any]:
        """Update a single gamestate field (legacy method for backward compatibility).
        
        Args:
            key: The gamestate key to update.
            value: The new value for the key.
        
        Returns:
            A copy of the updated gamestate dictionary.
        
        Raises:
            ValueError: If key doesn't exist or value type doesn't match.
        """
        if key not in self.gamestate:
            raise ValueError(f"Key '{key}' not found in gamestate")
        if type(value) != type(self.gamestate[key]):
            raise ValueError(
                f"Value type {type(value)} does not match gamestate type "
                f"{type(self.gamestate[key])} for key {key}"
            )
        self.gamestate[key] = value
        return self.get_gamestate()
