"""
Module 2: Optimal Strategy Search

Uses depth-limited minimax search to find optimal actions in the Chicken game.
The search assumes a resilience-based zero-sum game where each player tries
to maximize their resilience differential.

Input:
    - gamestate: Dict[str, Any] - Current game state from GameEngine
      Example: {"p1_hp": 100, "p2_hp": 100, "round": 0, ...}
    - player: str - Target player ("p1" or "p2")
    - depth: int - Search depth in full rounds (default: 2)

Output:
    - SearchResult dataclass containing:
        - optimal_action: bool (True=stay, False=swerve)
        - expected_utility: float (best worst-case resilience differential)
        - nodes_evaluated: int (number of game states examined)

Next Module Feed:
    - SearchResult.optimal_action feeds into Module 4 (Game Simulation)
    - Expected utility can be compared with Module 3 (Nash Equilibria) payoffs
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import importlib.util