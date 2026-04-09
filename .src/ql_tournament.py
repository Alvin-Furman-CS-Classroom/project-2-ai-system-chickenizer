"""Train a tabular Q-agent per opponent, then evaluate with learning off (tournament rounds).

Each matchup uses a fresh ``QLearningStrategy``: train vs one built-in opponent, then
run greedy test episodes against that same opponent. Use ``train_and_test_vs_opponent``
for a single row, or ``run_full_tournament`` for every name in ``OPPONENT_CHOICES``.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ql_strategy import QLearningStrategy  # noqa: E402
from train_ql import (  # noqa: E402
    OPPONENT_CHOICES,
    TrainingRunStats,
    run_greedy_evaluation_episodes,
    train_ql_agent,
)

# Text report layout (CLI)
_REPORT_COL_OPPONENT = 16
_REPORT_RULE_LEN = 60


@dataclass
class OpponentTournamentResult:
    """Train + test summary for one opponent key (e.g. ``\"tit_for_tat\"``)."""

    opponent_key: str
    train: TrainingRunStats
    test: TrainingRunStats


def _validate_opponent_key(opponent: str) -> str:
    key = opponent.lower().replace("-", "_").strip()
    if key not in OPPONENT_CHOICES:
        raise ValueError(
            f"Unknown opponent {opponent!r}; expected one of {OPPONENT_CHOICES}"
        )
    return key


def train_and_test_vs_opponent(
    opponent: str,
    *,
    train_episodes: int = 150,
    test_episodes: int = 40,
    max_rounds: int = 12,
    agent_seed: int = 0,
    agent_plays_p1: bool = True,
    epsilon_start: float = 0.25,
    epsilon_end: float = 0.05,
    minimax_depth: int = 2,
    random_seed: Optional[int] = None,
) -> Tuple[QLearningStrategy, OpponentTournamentResult]:
    """Train a new Q-agent vs ``opponent``, then test it frozen against the same opponent."""
    if train_episodes < 1:
        raise ValueError("train_episodes must be >= 1")

    key = _validate_opponent_key(opponent)
    role = "p1" if agent_plays_p1 else "p2"
    agent = QLearningStrategy(role, seed=agent_seed)

    _, _, train_stats = train_ql_agent(
        agent,
        key,
        episodes=train_episodes,
        max_rounds=max_rounds,
        agent_plays_p1=agent_plays_p1,
        epsilon_start=epsilon_start,
        epsilon_end=epsilon_end,
        minimax_depth=minimax_depth,
        random_seed=random_seed,
    )

    test_stats = run_greedy_evaluation_episodes(
        agent,
        key,
        episodes=test_episodes,
        max_rounds=max_rounds,
        agent_plays_p1=agent_plays_p1,
        minimax_depth=minimax_depth,
        random_seed=random_seed,
    )

    return agent, OpponentTournamentResult(
        opponent_key=key,
        train=train_stats,
        test=test_stats,
    )


def run_full_tournament(
    *,
    opponents: Optional[Sequence[str]] = None,
    train_episodes: int = 150,
    test_episodes: int = 40,
    max_rounds: int = 12,
    agent_seed: int = 0,
    agent_plays_p1: bool = True,
    epsilon_start: float = 0.25,
    epsilon_end: float = 0.05,
    minimax_depth: int = 2,
    random_seed: Optional[int] = None,
) -> List[OpponentTournamentResult]:
    """Run ``train_and_test_vs_opponent`` for each opponent (default: all of ``OPPONENT_CHOICES``)."""
    names = list(opponents) if opponents is not None else list(OPPONENT_CHOICES)
    results: List[OpponentTournamentResult] = []
    for name in names:
        _, row = train_and_test_vs_opponent(
            name,
            train_episodes=train_episodes,
            test_episodes=test_episodes,
            max_rounds=max_rounds,
            agent_seed=agent_seed,
            agent_plays_p1=agent_plays_p1,
            epsilon_start=epsilon_start,
            epsilon_end=epsilon_end,
            minimax_depth=minimax_depth,
            random_seed=random_seed,
        )
        results.append(row)
    return results


def format_tournament_report(rows: Sequence[OpponentTournamentResult]) -> str:
    """Plain-text table for CLI or logs."""
    w = _REPORT_COL_OPPONENT
    hdr_opp = "opponent"
    hdr_train = "train W/L/T"
    hdr_test = "test W/L/T"
    hdr_cls = "opponent_class"
    lines = [
        "QL tournament (train, then greedy evaluation vs same opponent)",
        f"{hdr_opp:<{w}}  {hdr_train:>12}  {hdr_test:>12}  {hdr_cls}",
        "-" * _REPORT_RULE_LEN,
    ]
    for r in rows:
        tr = r.train
        te = r.test
        train_wlt = f"{tr.wins}/{tr.losses}/{tr.ties}"
        test_wlt = f"{te.wins}/{te.losses}/{te.ties}"
        lines.append(
            f"{r.opponent_key:<{w}}  {train_wlt:>12}  {test_wlt:>12}  {tr.opponent}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Q-learning tournament: train vs one or all built-in opponents, then test greedy."
    )
    parser.add_argument(
        "--opponent",
        default="all",
        help=f"One of {OPPONENT_CHOICES} or 'all' (default: all)",
    )
    parser.add_argument("--train-episodes", type=int, default=150)
    parser.add_argument("--test-episodes", type=int, default=40)
    parser.add_argument("--max-rounds", type=int, default=12)
    parser.add_argument("--seed", type=int, default=0, help="QLearningStrategy seed")
    parser.add_argument("--epsilon-start", type=float, default=0.25)
    parser.add_argument("--epsilon-end", type=float, default=0.05)
    parser.add_argument("--minimax-depth", type=int, default=2)
    parser.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="Seed for random opponent during train and test",
    )
    args = parser.parse_args()

    tournament_kw = dict(
        train_episodes=args.train_episodes,
        test_episodes=args.test_episodes,
        max_rounds=args.max_rounds,
        agent_seed=args.seed,
        epsilon_start=args.epsilon_start,
        epsilon_end=args.epsilon_end,
        minimax_depth=args.minimax_depth,
        random_seed=args.random_seed,
    )

    spec = args.opponent.lower().replace("-", "_").strip()
    try:
        if spec == "all":
            rows = run_full_tournament(**tournament_kw)
        else:
            _, one = train_and_test_vs_opponent(spec, **tournament_kw)
            rows = [one]
    except ValueError as exc:
        print(f"ql_tournament: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    print(format_tournament_report(rows))


if __name__ == "__main__":
    main()
