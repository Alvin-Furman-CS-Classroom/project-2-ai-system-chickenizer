"""Train a tabular Q-agent per opponent, then evaluate with learning off (tournament rounds).

Each matchup uses a fresh ``QLearningStrategy``: train vs one built-in opponent, then
greedy test episodes vs that opponent. Sequential play matters, so ``run_full_tournament``
by default runs **every opponent twice**: RL as P1 and RL as P2 (``rl_seat="both"``).
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
_REPORT_COL_SEAT = 4
_REPORT_RULE_LEN = 72


@dataclass
class OpponentTournamentResult:
    """Train + test summary for one opponent key and RL seat (P1 or P2)."""

    opponent_key: str
    rl_seat: str  # "p1" or "p2" — which seat the Q-agent occupied
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
        rl_seat=role,
        train=train_stats,
        test=test_stats,
    )


def _seats_for_rl_seat(rl_seat: str) -> List[bool]:
    s = rl_seat.lower().strip()
    if s == "both":
        return [True, False]
    if s == "p1":
        return [True]
    if s == "p2":
        return [False]
    raise ValueError(
        f"rl_seat must be 'p1', 'p2', or 'both', got {rl_seat!r}"
    )


def run_full_tournament(
    *,
    opponents: Optional[Sequence[str]] = None,
    train_episodes: int = 150,
    test_episodes: int = 40,
    max_rounds: int = 12,
    agent_seed: int = 0,
    rl_seat: str = "both",
    epsilon_start: float = 0.25,
    epsilon_end: float = 0.05,
    minimax_depth: int = 2,
    random_seed: Optional[int] = None,
) -> List[OpponentTournamentResult]:
    """Run ``train_and_test_vs_opponent`` for each opponent × each RL seat in ``rl_seat``.

    Default ``rl_seat=\"both\"`` covers sequential permutations (RL first mover vs second).
    """
    names = list(opponents) if opponents is not None else list(OPPONENT_CHOICES)
    seats = _seats_for_rl_seat(rl_seat)
    results: List[OpponentTournamentResult] = []
    for name in names:
        for agent_plays_p1 in seats:
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
    w_opp = _REPORT_COL_OPPONENT
    w_seat = _REPORT_COL_SEAT
    hdr_opp = "opponent"
    hdr_seat = "seat"
    hdr_train = "tr R W/L/T"
    hdr_test = "te R W/L/T"
    hdr_cls = "opponent_class"
    lines = [
        "QL tournament — episode W/L/T from final resilience margin (P1−P2 from agent seat; "
        "matches Q step reward); tr/te = train / greedy test",
        f"{hdr_opp:<{w_opp}}  {hdr_seat:>{w_seat}}  {hdr_train:>12}  {hdr_test:>12}  {hdr_cls}",
        "-" * _REPORT_RULE_LEN,
    ]
    for r in rows:
        tr = r.train
        te = r.test
        train_wlt = f"{tr.wins}/{tr.losses}/{tr.ties}"
        test_wlt = f"{te.wins}/{te.losses}/{te.ties}"
        lines.append(
            f"{r.opponent_key:<{w_opp}}  {r.rl_seat:>{w_seat}}  {train_wlt:>12}  {test_wlt:>12}  {tr.opponent}"
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
    parser.add_argument(
        "--seat",
        choices=("both", "p1", "p2"),
        default="both",
        help="RL as P1 only, P2 only, or both (default: both — all sequential permutations)",
    )
    args = parser.parse_args()

    tournament_kw = dict(
        train_episodes=args.train_episodes,
        test_episodes=args.test_episodes,
        max_rounds=args.max_rounds,
        agent_seed=args.seed,
        rl_seat=args.seat,
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
            seats = _seats_for_rl_seat(args.seat)
            rows = []
            for plays_p1 in seats:
                _, row = train_and_test_vs_opponent(
                    spec,
                    **{k: v for k, v in tournament_kw.items() if k != "rl_seat"},
                    agent_plays_p1=plays_p1,
                )
                rows.append(row)
    except ValueError as exc:
        print(f"ql_tournament: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    print(format_tournament_report(rows))


if __name__ == "__main__":
    main()
