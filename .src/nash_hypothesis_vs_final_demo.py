#!/usr/bin/env python3
"""Terminal demo: hypothesis vs post-match normal-form NE + joint-play diagnostics.

Each case prints (see ``report_match_hypothesis_vs_final_nash``):

1. **Match recap** — resilience margin (P1−P2) leader, per-round ``score`` tallies, final HP.
2. **Two ASCII payoff grids** — hypothesis (pre-match state) vs final (post-match state),
   with pure NE cells marked; optional mixed NE lines with ``--mixed``.
3. **Joint play vs hypothesis** — per-cell ratio ``observed / (N · Pr_cell)`` using the
   hypothesis NE as an i.i.d. per-round reference (``--mixed-index`` picks which mixed NE).

Run from the repo root::

    python .src/nash_hypothesis_vs_final_demo.py

One case (1-based index), mixed NE lines + use the second mixed equilibrium for ratios::

    python .src/nash_hypothesis_vs_final_demo.py --case 3 --mixed --mixed-index 1

Strategies span simple constants → reactive / search / HP-aware → tabular RL.
RL cases (11–12) **train** the Q-agent against the listed opponent before the ASCII
match, then set ``epsilon=0`` so the recap uses a **greedy** replay.
``--mixed`` adds mixed NE lines to the two grids and fills ``mixed_equilibria`` so the
joint table can use a **mixed** reference; without it, the joint table uses a **uniform
mixture over pure Nash** cells (see ``hypothesis_joint_distribution``).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from engine import GameEngine  # noqa: E402
from nash_normal_form import report_match_hypothesis_vs_final_nash  # noqa: E402
from strategies import (  # noqa: E402
    AggressiveStrategy,
    AlwaysStayStrategy,
    AlwaysSwerveStrategy,
    DefensiveStrategy,
    HPThresholdStrategy,
    MinimaxStrategy,
    RandomStrategy,
    Strategy,
    TitForTatStrategy,
)

StrategyPairFactory = Callable[
    [],
    Tuple[Strategy, Strategy, Optional[Dict[str, Any]]],
]


def _asymmetric_win_weights() -> Tuple[Strategy, Strategy, Dict[str, Any]]:
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


def _injured_p1() -> Tuple[Strategy, Strategy, Dict[str, Any]]:
    eng = GameEngine()
    gs = eng.get_gamestate()
    gs["p1_hp"] = 14
    gs["p1_hp_thresh"] = 20
    gs["p1_crash_dmg"] = 26
    return HPThresholdStrategy("p1"), AlwaysSwerveStrategy("p2"), gs


# Warm-up training before the hypothesis/final ASCII match (separate from match max_rounds).
_DEMO_QL_TRAIN_EPISODES = 150
_DEMO_QL_TRAIN_MAX_ROUNDS = 12


def _train_p1_ql_for_demo(agent_seed: int, opponent_name: str):
    """Return a P1 ``QLearningStrategy`` trained vs ``opponent_name``; ε=0 for greedy replay."""
    from ql_strategy import QLearningStrategy  # noqa: PLC0415
    from train_ql import train_ql_agent  # noqa: PLC0415

    agent = QLearningStrategy("p1", seed=agent_seed, epsilon=0.15)
    train_ql_agent(
        agent,
        opponent_name,
        episodes=_DEMO_QL_TRAIN_EPISODES,
        max_rounds=_DEMO_QL_TRAIN_MAX_ROUNDS,
        epsilon_start=0.25,
        epsilon_end=0.05,
    )
    agent.epsilon = 0.0
    return agent


def _ql_vs_tft() -> Tuple[Strategy, Strategy, Optional[Dict[str, Any]]]:
    p1 = _train_p1_ql_for_demo(11, "tit_for_tat")
    return (p1, TitForTatStrategy("p2"), None)


def _ql_vs_hp_threshold() -> Tuple[Strategy, Strategy, Optional[Dict[str, Any]]]:
    """Trained tabular RL vs HPThresholdStrategy; post-match NE reflects a greedy replay path."""
    p1 = _train_p1_ql_for_demo(19, "hp_threshold")
    return (p1, HPThresholdStrategy("p2"), None)


# (title, factory, max_rounds)
CASES: List[Tuple[str, StrategyPairFactory, int]] = [
    (
        "1) Simple — AlwaysSwerve vs AlwaysSwerve (default prefs)",
        lambda: (AlwaysSwerveStrategy("p1"), AlwaysSwerveStrategy("p2"), None),
        12,
    ),
    (
        "2) Simple — AlwaysStay vs AlwaysSwerve (pure commitment vs cooperator)",
        lambda: (AlwaysStayStrategy("p1"), AlwaysSwerveStrategy("p2"), None),
        10,
    ),
    (
        "3) Medium — TitForTat vs TitForTat (mirrored reciprocity)",
        lambda: (TitForTatStrategy("p1"), TitForTatStrategy("p2"), None),
        14,
    ),
    (
        "4) Medium — TitForTat vs Random (stochastic opponent, seed=42)",
        lambda: (
            TitForTatStrategy("p1"),
            RandomStrategy("p2", seed=42),
            None,
        ),
        15,
    ),
    (
        "5) Search — Minimax(d=2) vs Minimax(d=2) (symmetric lookahead)",
        lambda: (
            MinimaxStrategy("p1", depth=2),
            MinimaxStrategy("p2", depth=2),
            None,
        ),
        10,
    ),
    (
        "6) Search — Minimax(d=2) vs Minimax(d=3) (asymmetric depth)",
        lambda: (
            MinimaxStrategy("p1", depth=2),
            MinimaxStrategy("p2", depth=3),
            None,
        ),
        8,
    ),
    (
        "7) HP / prefs — AggressiveStrategy vs DefensiveStrategy",
        lambda: (AggressiveStrategy("p1"), DefensiveStrategy("p2"), None),
        12,
    ),
    (
        "8) HP threshold — HPThreshold vs HPThreshold",
        lambda: (
            HPThresholdStrategy("p1"),
            HPThresholdStrategy("p2"),
            None,
        ),
        12,
    ),
    (
        "9) Custom gamestate — asymmetric win weights, both AlwaysSwerve",
        _asymmetric_win_weights,
        10,
    ),
    (
        "10) Injured P1 start — HPThreshold vs AlwaysSwerve (low HP, high crash dmg)",
        _injured_p1,
        8,
    ),
    (
        "11) RL — QLearningStrategy (trained vs TFT, greedy display) vs TitForTat",
        _ql_vs_tft,
        14,
    ),
    (
        "12) RL — QLearningStrategy (trained vs hp_threshold, greedy display) vs "
        "HPThresholdStrategy (P2)",
        _ql_vs_hp_threshold,
        14,
    ),
]


def run_case(
    title: str,
    factory: StrategyPairFactory,
    *,
    max_rounds: int,
    include_mixed: bool,
    joint_mixed_index: int,
) -> str:
    p1, p2, initial = factory()
    body = report_match_hypothesis_vs_final_nash(
        p1,
        p2,
        max_rounds=max_rounds,
        initial_gamestate=initial,
        include_mixed=include_mixed,
        joint_mixed_index=joint_mixed_index,
    )
    banner = "=" * 72
    return f"{banner}\n{title}\n{banner}\n\n{body}"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Print hypothesis vs post-match normal-form NE (ASCII grids) plus a "
            "joint-action table: observed / (N·Pr) under the hypothesis NE."
        ),
    )
    parser.add_argument(
        "--case",
        type=int,
        default=None,
        metavar="N",
        help="run only case N (1-based); default runs all",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=None,
        help="override max rounds for every case (default: per-case value)",
    )
    parser.add_argument(
        "--mixed",
        action="store_true",
        help="include mixed Nash lines in both panels (runs nashpy; slower)",
    )
    parser.add_argument(
        "--mixed-index",
        type=int,
        default=0,
        metavar="K",
        help=(
            "when hypothesis has several mixed equilibria, use mixed[K] for joint "
            "observed/expected ratios (default 0)"
        ),
    )
    args = parser.parse_args(argv)
    include_mixed = args.mixed
    joint_mixed_index = max(0, int(args.mixed_index))

    if args.case is not None:
        if args.case < 1 or args.case > len(CASES):
            print(f"--case must be 1..{len(CASES)}", file=sys.stderr)
            return 2
        indices = [args.case - 1]
    else:
        indices = list(range(len(CASES)))

    blocks: List[str] = []
    for i in indices:
        title, factory, default_mr = CASES[i]
        mr = args.max_rounds if args.max_rounds is not None else default_mr
        blocks.append(
            run_case(
                title,
                factory,
                max_rounds=mr,
                include_mixed=include_mixed,
                joint_mixed_index=joint_mixed_index,
            )
        )

    print("\n\n".join(blocks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
