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

    # Threshold at which resilience difference forces a tap-out.
    RESILIENCE_THRESHOLD: int = 100

    # class constants
    DEFAULT_HP = 100
    DEFAULT_HP_THRESHOLD = 20
    DEFAULT_CRASH_DAMAGE = 10


    DEFAULT_GAMESTATE: Dict[str, Any] = {
        "p1_stay": False,
        "p2_stay": False,
        "p1_hp": DEFAULT_HP,
        "p2_hp": DEFAULT_HP,
        "p1_hp_thresh": DEFAULT_HP_THRESHOLD,
        "p2_hp_thresh": DEFAULT_HP_THRESHOLD,
        "p1_crash_dmg": DEFAULT_CRASH_DAMAGE,
        "p2_crash_dmg": DEFAULT_CRASH_DAMAGE,
        "round": 0,
        "p1_action_history": [],
        "p2_action_history": [],
        "score": [],
        # Resilience scores capture how much each player can "stay in the game".
        # These can be influenced by round wins/losses, crashes, HP, etc.
        "p1_resilience": 0,
        "p2_resilience": 0,
        # Convenience field for differential resilience used by minimax: R1 - R2.
        "resilience_diff": 0,
        # Per-player preference weights for translating round outcomes and HP
        # changes into resilience updates. "Cares about X" == non-zero weight.
        "p1_preferences": {
            "round_win": 10,
            "round_loss": -10,
            "tie": 0,
            "crash": -15,
            "hp_delta": 0,  # default: P1 does not care about HP unless overridden
        },
        "p2_preferences": {
            "round_win": 10,
            "round_loss": -10,
            "tie": 0,
            "crash": -15,
            "hp_delta": 0,  # default: P2 does not care about HP unless overridden
        },
        # Set by ``run_game`` when the loop ends: ``round_cap`` or ``is_game_over`` reason.
        "match_end_reason": "",
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

    def _apply_crash_damage(self) -> None:
        """Apply crash damage to both players if both players stayed."""
        if self.gamestate["p1_stay"] and self.gamestate["p2_stay"]:
            self.gamestate["p1_hp"] -= self.gamestate["p1_crash_dmg"]
            self.gamestate["p2_hp"] -= self.gamestate["p2_crash_dmg"]

    def _determine_round_outcome(self) -> Optional[str]:
        """Determine the round outcome based on the current gamestate."""
        if self.gamestate["p1_stay"] and not self.gamestate["p2_stay"]:
            return "P1"
        elif self.gamestate["p2_stay"] and not self.gamestate["p1_stay"]:
            return "P2"
        elif not self.gamestate["p1_stay"] and not self.gamestate["p2_stay"]:
            return "TIE"
        elif self.gamestate["p1_stay"] and self.gamestate["p2_stay"]:
            return "CRASH"
        return None

    def _update_resilience(self, old_p1_hp: int, old_p2_hp: int) -> None:
        """Update resilience scores based on round outcome and HP changes.
    
        Args:
            old_p1_hp: P1's HP before the round
            old_p2_hp: P2's HP before the round
        """
        p1_prefs: Dict[str, Any] = self.gamestate.get("p1_preferences", {})
        p2_prefs: Dict[str, Any] = self.gamestate.get("p2_preferences", {})
        round_outcome: Optional[str] = self._determine_round_outcome()
        
        # Update based on round outcome
        if round_outcome == "P1":
            self.gamestate["p1_resilience"] += int(p1_prefs.get("round_win", 0))
            self.gamestate["p2_resilience"] += int(p2_prefs.get("round_loss", 0))
        elif round_outcome == "P2":
            self.gamestate["p1_resilience"] += int(p1_prefs.get("round_loss", 0))
            self.gamestate["p2_resilience"] += int(p2_prefs.get("round_win", 0))
        elif round_outcome == "TIE":
            self.gamestate["p1_resilience"] += int(p1_prefs.get("tie", 0))
            self.gamestate["p2_resilience"] += int(p2_prefs.get("tie", 0))
        elif round_outcome == "CRASH":
            self.gamestate["p1_resilience"] += int(p1_prefs.get("crash", 0))
            self.gamestate["p2_resilience"] += int(p2_prefs.get("crash", 0))
        
        # Update based on HP changes (for strategies that care about HP)
        delta_p1_hp = self.gamestate["p1_hp"] - old_p1_hp
        delta_p2_hp = self.gamestate["p2_hp"] - old_p2_hp
        hp_weight_p1 = int(p1_prefs.get("hp_delta", 0))
        hp_weight_p2 = int(p2_prefs.get("hp_delta", 0))
        if delta_p1_hp != 0 and hp_weight_p1 != 0:
            self.gamestate["p1_resilience"] += delta_p1_hp * hp_weight_p1
        if delta_p2_hp != 0 and hp_weight_p2 != 0:
            self.gamestate["p2_resilience"] += delta_p2_hp * hp_weight_p2
        
        # Update resilience differential
        self.gamestate["resilience_diff"] = (
            self.gamestate["p1_resilience"] - self.gamestate["p2_resilience"]
        )

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
            # Track HP before applying any round-end effects so we can compute
            # HP-based contributions to resilience for players who care about HP.
            old_p1_hp = self.gamestate["p1_hp"]
            old_p2_hp = self.gamestate["p2_hp"]

            self._apply_crash_damage()

            # Determine round outcome and update score
            round_outcome: Optional[str] = self._determine_round_outcome()
            if round_outcome is not None:
                self.gamestate["score"].append(round_outcome)

                self._update_resilience(old_p1_hp, old_p2_hp)

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
            Checks both HP-based termination (players running out of HP) and
            resilience-based termination (one player "tapping out" when the
            resilience differential becomes too large in magnitude).
        """
        # HP-based game over conditions
        if self.gamestate["p1_hp"] <= 0 and self.gamestate["p2_hp"] <= 0:
            return True, "both_hp_zero"
        if self.gamestate["p1_hp"] <= 0:
            return True, "p1_hp_zero"
        if self.gamestate["p2_hp"] <= 0:
            return True, "p2_hp_zero"

        # Resilience-based tap-out: when |R1 - R2| exceeds threshold.
        diff = self.gamestate.get("resilience_diff", 0)
        if diff >= self.RESILIENCE_THRESHOLD:
            # P1 is much more resilient; P2 taps out.
            return True, "p2_resilience_tapout"
        if diff <= -self.RESILIENCE_THRESHOLD:
            # P2 is much more resilient; P1 taps out.
            return True, "p1_resilience_tapout"

        # Otherwise, game over is only checked externally via round count.
        return False, None

    def run_game(
        self,
        max_rounds: int,
        p1_strategy: Callable[[Dict[str, Any]], bool],
        p2_strategy: Callable[[Dict[str, Any]], bool],
        initial_gamestate: Optional[Dict[str, Any]] = None,
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

        # Reset action flags, history, score, and resilience for new game
        self.gamestate["p1_stay"] = False
        self.gamestate["p2_stay"] = False
        self.gamestate["round"] = 0
        self.gamestate["p1_action_history"] = []
        self.gamestate["p2_action_history"] = []
        self.gamestate["score"] = []
        self.gamestate["p1_resilience"] = 0
        self.gamestate["p2_resilience"] = 0
        self.gamestate["resilience_diff"] = 0
        self.gamestate["match_end_reason"] = ""

        # New match: revive HP if a prior game left anyone at/below zero (same engine).
        if self.gamestate["p1_hp"] <= 0 or self.gamestate["p2_hp"] <= 0:
            self.gamestate["p1_hp"] = self.DEFAULT_HP
            self.gamestate["p2_hp"] = self.DEFAULT_HP

        # ``__init__`` captured a snapshot before these resets; align history with the
        # actual match start (see GameSimulator using prior ``get_gamestate()`` as base).
        self.gamestate_history = [deepcopy(self.gamestate)]

        while self.gamestate["round"] < max_rounds:
            # Check for game over conditions
            is_over, reason = self.is_game_over()
            if is_over:
                self.gamestate["match_end_reason"] = reason or "game_over"
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
        else:
            # Exhausted ``max_rounds`` without breaking (no mid-match ``is_game_over``).
            self.gamestate["match_end_reason"] = "round_cap"

        # Last history row was appended before ``match_end_reason`` was set; align it.
        if self.gamestate_history:
            self.gamestate_history[-1] = deepcopy(self.gamestate)

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
        # Apply the update after successful validation.
        self.gamestate[key] = value
        return self.get_gamestate()

