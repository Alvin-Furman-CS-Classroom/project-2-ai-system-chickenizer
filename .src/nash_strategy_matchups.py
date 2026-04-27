"""Print Nash normal-form tables for several strategy pairs from strategies.py.

One-shot payoffs use merge_strategy_preferences: they depend on each strategy's
implied_preferences() and optional initial_gamestate—not on decide() during the
Nash build. Pairs with the same merged preferences share the same matrix; labels
still show which strategies named the run.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from engine import GameEngine  # noqa: E402
from nash_normal_form import analyze_normal_form, format_nash_table  # noqa: E402
from strategies import (  # noqa: E402
    AggressiveStrategy,
    AlwaysStayStrategy,
    AlwaysSwerveStrategy,
    DefensiveStrategy,
    HPThresholdStrategy,
    MinimaxStrategy,
    TitForTatStrategy,
)

StrategyPairFactory = Callable[
    [],
    Tuple[Any, Any, Optional[Dict[str, Any]]],
]


def _asymmetric_win_weights() -> Tuple[Any, Any, Dict[str, Any]]:
    eng = GameEngine()
    gs = eng.get_gamestate()
    gs["p1_preferences"] = {
        **dict(gs["p1_preferences"]),
        "round_win": 25,
        "round_loss": -25,
    }
    gs["p2_preferences"] = {
        **dict(gs["p2_preferences"]),
        "round_win": 8,
        "round_loss": -8,
    }
    return AlwaysSwerveStrategy("p1"), AlwaysSwerveStrategy("p2"), gs


def _injured_hp_conscious_p1() -> Tuple[Any, Any, Dict[str, Any]]:
    """P1 uses HPThresholdStrategy (hp_delta); low HP + heavier crash damage for P1.

    The normal-form matrix still enumerates all four action pairs; it does not call
    decide(). Low *starting* HP alone does not change payoffs in the engine (only
    ΔHP matters), so we raise ``p1_crash_dmg`` so mutual-crash hurts P1 more—
    plausible \"already hurt / fragile\" framing. In GameSimulator, the same state
    would push HPThresholdStrategy toward swerve; here you see that in the (Stay,
    Stay) payoff vs cases with default crash damage.
    """
    eng = GameEngine()
    gs = eng.get_gamestate()
    gs["p1_hp"] = 14
    gs["p1_hp_thresh"] = 20
    gs["p1_crash_dmg"] = 26
    return HPThresholdStrategy("p1"), AlwaysSwerveStrategy("p2"), gs


CASES: list[tuple[str, StrategyPairFactory]] = [
    (
        "1) Baseline — AlwaysSwerve vs AlwaysSwerve (no implied_prefs)",
        lambda: (AlwaysSwerveStrategy("p1"), AlwaysSwerveStrategy("p2"), None),
    ),
    (
        "2) P1 HP-aware — AggressiveStrategy vs AlwaysSwerve",
        lambda: (AggressiveStrategy("p1"), AlwaysSwerveStrategy("p2"), None),
    ),
    (
        "3) P2 HP-aware — AlwaysSwerve vs AggressiveStrategy",
        lambda: (AlwaysSwerveStrategy("p1"), AggressiveStrategy("p2"), None),
    ),
    (
        "4) Both HP-aware — AggressiveStrategy vs DefensiveStrategy",
        lambda: (AggressiveStrategy("p1"), DefensiveStrategy("p2"), None),
    ),
    (
        "5) Same matrix as (1) if prefs merge equal — TitForTat vs MinimaxStrategy",
        lambda: (
            TitForTatStrategy("p1"),
            MinimaxStrategy("p2", depth=2),
            None,
        ),
    ),
    (
        "6) Asymmetric win/loss weights — two AlwaysSwerve + custom gamestate",
        _asymmetric_win_weights,
    ),
    (
        "7) AlwaysStay vs AlwaysSwerve (labels only vs (1) unless prefs differ)",
        lambda: (AlwaysStayStrategy("p1"), AlwaysSwerveStrategy("p2"), None),
    ),
    (
        "8) HPThreshold vs HPThreshold (both imply hp_delta)",
        lambda: (
            HPThresholdStrategy("p1"),
            HPThresholdStrategy("p2"),
            None,
        ),
    ),
    (
        "9) Injured HP-conscious P1 — low HP + high p1_crash_dmg vs AlwaysSwerve",
        _injured_hp_conscious_p1,
    ),
]


def main() -> None:
    for title, factory in CASES:
        p1, p2, initial = factory()
        print("=" * 72)
        print(title)
        print("=" * 72)
        result = analyze_normal_form(p1, p2, initial, include_mixed=True)
        print(format_nash_table(result))
        print()


if __name__ == "__main__":
    main()
