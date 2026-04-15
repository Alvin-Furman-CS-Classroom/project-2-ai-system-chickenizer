"""
Strategy system for Chickenizer game.

Provides a Strategy base class and concrete strategy implementations that can be
assigned to players and used with the GameEngine to simulate games.

Agent API: autonomous players implement ``Strategy`` with ``decide(gamestate) -> bool``
(stay vs swerve). ``GameEngine.run_game`` and ``GameSimulator`` use that interface;
future policies (e.g. RL) can subclass ``Strategy`` without changing the engine.

Sequential vs one-shot Nash: ``GameEngine.run_game`` is turn-based (P1 then P2).
``nash_normal_form`` analyzes a simultaneous one-shot round (both actions fixed,
then resolved), consistent with ``MinimaxStrategy`` joint-action simulation.
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path
import importlib.util
import random


def _load_engine_class():
    """Helper to load GameEngine regardless of package context.

    When strategies.py is imported as part of a package, we can use a normal
    relative import. When it is loaded directly via spec_from_file_location
    (as in unit tests), we fall back to a path-based import.
    """
    try:
        from .engine import GameEngine  # type: ignore
        return GameEngine
    except ImportError:
        engine_path = Path(__file__).resolve().with_name("engine.py")
        spec = importlib.util.spec_from_file_location("engine_for_strategies", engine_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load GameEngine from {engine_path}") from None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.GameEngine


class Strategy(ABC):
    """Player policy interface: map a gamestate to stay (True) or swerve (False).

    Subclasses implement ``decide``. ``implied_preferences()`` optionally declares
    outcome weights merged into gamestate for simulation and normal-form payoffs.
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

    def implied_preferences(self) -> Dict[str, int]:
        """Return preference weight overrides implied by this strategy.
        
        By default, strategies only inherit the engine's default preferences,
        which already encode caring about round outcomes. Subclasses can
        override this to indicate additional cares (e.g., HP).
        """
        return {}


def merge_strategy_preferences(
    base_gamestate: Dict[str, Any],
    p1_strategy: "Strategy",
    p2_strategy: "Strategy",
) -> Dict[str, Any]:
    """Deep-copy ``base_gamestate`` and merge each strategy's ``implied_preferences``.

    Ensures ``p1_preferences`` / ``p2_preferences`` exist (from engine defaults if
    missing), then overlays implied weights. Used by ``GameSimulator`` and
    ``nash_normal_form``.
    """
    state = deepcopy(base_gamestate)
    GameEngine = _load_engine_class()
    default_state = GameEngine.DEFAULT_GAMESTATE
    if "p1_preferences" not in state:
        state["p1_preferences"] = deepcopy(default_state.get("p1_preferences", {}))
    if "p2_preferences" not in state:
        state["p2_preferences"] = deepcopy(default_state.get("p2_preferences", {}))
    state["p1_preferences"] = {
        **state["p1_preferences"],
        **p1_strategy.implied_preferences(),
    }
    state["p2_preferences"] = {
        **state["p2_preferences"],
        **p2_strategy.implied_preferences(),
    }
    return state


def resilience_margin_p1_minus_p2(gamestate: Dict[str, Any]) -> float:
    """Signed resilience margin P1−P2 (same sign convention as engine ``resilience_diff``)."""
    raw = gamestate.get("resilience_diff")
    if raw is not None:
        return float(raw)
    return float(
        int(gamestate.get("p1_resilience", 0)) - int(gamestate.get("p2_resilience", 0))
    )


def resilience_leader_p1_seat(gamestate: Dict[str, Any]) -> str:
    """Who leads on resilience: ``\"p1\"``, ``\"p2\"``, or ``\"tie\"``."""
    m = resilience_margin_p1_minus_p2(gamestate)
    if m > 0:
        return "p1"
    if m < 0:
        return "p2"
    return "tie"


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
    
    Can be passed a seed for more deterministic behavior. If no seed is provided,
    a module-level random number generator is used."""
    
    def __init__(self, player: str, seed: Optional[int] = None):
        """Initialize random strategy.
        
        Args:
            player: Player identifier ("p1" or "p2")
            seed: Optional random seed for reproducibility. When provided,
                a per-instance Random object is created to ensure deterministic
                behavior for this strategy only.
        """
        super().__init__(player)
        if seed is not None:
            self.random = random.Random(seed)
        else:
            # Fall back to module-level RNG if no seed is provided.
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

    def implied_preferences(self) -> Dict[str, int]:
        """HP-based strategy: player cares about HP changes."""
        return {"hp_delta": 1}


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

    def implied_preferences(self) -> Dict[str, int]:
        """Aggressive HP-based strategy: also cares about HP."""
        return {"hp_delta": 1}


class DefensiveStrategy(Strategy):
    """Strategy that swerves unless HP is very high.
    
    Only stays when HP is well above the threshold.
    """
    
    def decide(self, gamestate: Dict[str, Any]) -> bool:
        hp_thresh = gamestate.get(f"{self.player}_hp_thresh", 20)
        current_hp = gamestate.get(f"{self.player}_hp", 100)
        safe_threshold = hp_thresh * 2
        
        return current_hp > safe_threshold

    def implied_preferences(self) -> Dict[str, int]:
        """Defensive HP-based strategy: cares about HP safety."""
        return {"hp_delta": 1}


class EntertainerStrategy(Strategy):
    """Spectacle-seeking style: the crowd rewards **stay** (see engine ``p*_reputation``).

    The engine increments ``p*_reputation`` when that player stays **and** their merged
    preferences have non-zero ``reputation_delta`` (same "cares" rule as ``hp_delta``).
    This strategy declares ``reputation_delta`` so those stays also move **resilience**
    (same moment as round-outcome updates). It still cares about HP a little, and when
    healthy it biases toward stay for the show (stochastic so matches are not pure
    always-stay unless RNG rolls that way).
    """

    def __init__(
        self,
        player: str,
        *,
        stay_bias: float = 0.72,
        seed: Optional[int] = None,
    ):
        super().__init__(player)
        if not 0.0 <= stay_bias <= 1.0:
            raise ValueError("stay_bias must be in [0, 1]")
        self.stay_bias = float(stay_bias)
        self._rng = random.Random(seed) if seed is not None else random

    def decide(self, gamestate: Dict[str, Any]) -> bool:
        hp_thresh = int(gamestate.get(f"{self.player}_hp_thresh", 20))
        current_hp = int(gamestate.get(f"{self.player}_hp", 100))
        if current_hp <= hp_thresh:
            return False
        return self._rng.random() < self.stay_bias

    def implied_preferences(self) -> Dict[str, int]:
        return {"reputation_delta": 6, "hp_delta": 1}


class MinimaxStrategy(Strategy):
    """Depth-limited minimax strategy assuming resilience-based zero-sum game.
    
    This strategy maximizes the resilience differential U = R1 - R2 from the
    perspective of the configured player. The opponent is assumed to choose
    actions that minimize this value. Depth is measured in full rounds.
    """
    
    def __init__(
        self,
        player: str,
        depth: int = 2,
    ):
        """Initialize a minimax strategy.
        
        Args:
            player: Player identifier ("p1" or "p2").
            depth: Depth limit in full rounds (must be >= 1).
        """
        super().__init__(player)
        if depth < 1:
            raise ValueError(f"depth must be >= 1, got {depth}")
        self.depth = depth

        # Resolve GameEngine lazily to avoid circular imports and support
        # different import contexts (package vs direct file import).
        GameEngine = _load_engine_class()
        self._EngineClass = GameEngine
        self.resilience_threshold = GameEngine.RESILIENCE_THRESHOLD
    
    def decide(self, gamestate: Dict[str, Any]) -> bool:
        """Choose 'stay' (True) or 'swerve' (False) via depth-limited minimax."""
        best_value = float("-inf")
        best_action = False  # default to swerve
        
        for my_action in (False, True):  # False=swerve, True=stay
            value = self._min_value(gamestate, my_action, self.depth)
            if value > best_value:
                best_value = value
                best_action = my_action
        
        return best_action

    # --- Internal helpers for minimax search ---

    def _evaluate_state(self, state: Dict[str, Any]) -> float:
        """Leaf evaluation using resilience differential U = R1 - R2."""
        u = float(state.get("resilience_diff", 0))
        # From p1's perspective we maximize U; from p2's we maximize -U.
        return u if self.player == "p1" else -u

    def _is_terminal(self, state: Dict[str, Any]) -> bool:
        """Check terminal conditions based on HP and resilience differential."""
        p1_hp = state.get("p1_hp", 0)
        p2_hp = state.get("p2_hp", 0)
        if p1_hp <= 0 or p2_hp <= 0:
            return True
        
        diff = state.get("resilience_diff", 0)
        return abs(diff) >= self.resilience_threshold

    def _simulate_round(
        self,
        state: Dict[str, Any],
        my_action: bool,
        opp_action: bool,
    ) -> Dict[str, Any]:
        """Simulate a single full round with fixed actions for both players."""
        Engine = self._EngineClass
        engine = Engine(gamestate=deepcopy(state))
        
        if self.player == "p1":
            engine.play_action("p1", my_action)
            engine.play_action("p2", opp_action)
        else:
            engine.play_action("p2", my_action)
            engine.play_action("p1", opp_action)
        
        next_state = engine.generate_gamestate(increment_round=True)
        return next_state

    def _min_value(
        self,
        state: Dict[str, Any],
        my_action: bool,
        depth: int,
    ) -> float:
        """Opponent chooses an action that minimizes our eventual utility."""
        values = []
        for opp_action in (False, True):
            next_state = self._simulate_round(state, my_action, opp_action)
            if depth == 1 or self._is_terminal(next_state):
                values.append(self._evaluate_state(next_state))
            else:
                values.append(self._max_value(next_state, depth - 1))
        return min(values)

    def _max_value(self, state: Dict[str, Any], depth: int) -> float:
        """Our move again in the next round."""
        best = float("-inf")
        for my_action in (False, True):
            val = self._min_value(state, my_action, depth)
            if val > best:
                best = val
        return best


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
            GameEngine = _load_engine_class()
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
        
        # Prepare initial gamestate with per-player preferences merged from strategies.
        # Use a fresh default template, not ``engine.get_gamestate()`` — the engine may
        # still hold end-of-match HP (e.g. 0) from a previous ``simulate`` on this instance.
        if initial_gamestate is None:
            GameEngine = _load_engine_class()
            base_gamestate = merge_strategy_preferences(
                deepcopy(GameEngine.DEFAULT_GAMESTATE), p1_strategy, p2_strategy
            )
        else:
            base_gamestate = merge_strategy_preferences(
                initial_gamestate, p1_strategy, p2_strategy
            )

        # Run the game with the enriched initial gamestate.
        try:
            history = self.engine.run_game(
                max_rounds=max_rounds,
                p1_strategy=p1_strategy,
                p2_strategy=p2_strategy,
                initial_gamestate=base_gamestate,
            )
        except Exception:
            for strat in (p1_strategy, p2_strategy):
                abandon = getattr(strat, "abandon_episode", None)
                if callable(abandon):
                    abandon()
            raise

        final_state = history[-1] if history else self.engine.get_gamestate()

        # Calculate summary statistics
        score = final_state.get("score", [])
        p1_wins = score.count("P1")
        p2_wins = score.count("P2")
        ties = score.count("TIE")
        crashes = score.count("CRASH")
        margin = resilience_margin_p1_minus_p2(final_state)
        leader = resilience_leader_p1_seat(final_state)

        summary = {
            "rounds_played": final_state.get("round", 0),
            "p1_hp": final_state.get("p1_hp", 100),
            "p2_hp": final_state.get("p2_hp", 100),
            "p1_wins": p1_wins,
            "p2_wins": p2_wins,
            "ties": ties,
            "crashes": crashes,
            "resilience_margin_p1_minus_p2": margin,
            "resilience_leader": leader,
            "p1_strategy": p1_strategy.__class__.__name__,
            "p2_strategy": p2_strategy.__class__.__name__,
        }

        result_dict = {
            "history": history,
            "final_state": final_state,
            "summary": summary,
        }
        fin = getattr(p1_strategy, "finalize_episode", None)
        if callable(fin):
            fin(final_state)
        fin2 = getattr(p2_strategy, "finalize_episode", None)
        if callable(fin2):
            fin2(final_state)
        return result_dict
    
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
        print("Resilience (end of match, P1−P2 margin):")
        m = summary.get("resilience_margin_p1_minus_p2")
        ld = summary.get("resilience_leader", "?")
        print(f"  Margin: {m:+.1f}  →  leader: {ld}")
        print("Round score tallies (P1 stayed / P2 swerved style):")
        print(f"  P1 Wins: {summary['p1_wins']}")
        print(f"  P2 Wins: {summary['p2_wins']}")
        print(f"  Ties: {summary['ties']}")
        print(f"  Crashes: {summary['crashes']}")
        print()
        print("Score History:", final_state.get("score", []))
        print("=" * 60)
