"""Train ``QLearningStrategy`` against built-in or custom opponents via ``GameSimulator``.

Episodes always go through ``simulate`` so ``finalize_episode`` runs on success;
on ``run_game`` failure, strategies with ``abandon_episode`` are reset.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ql_strategy import QLearningStrategy  # noqa: E402
from strategies import (  # noqa: E402
    AggressiveStrategy,
    AlwaysStayStrategy,
    AlwaysSwerveStrategy,
    DefensiveStrategy,
    GameSimulator,
    HPThresholdStrategy,
    MinimaxStrategy,
    RandomStrategy,
    Strategy,
    TitForTatStrategy,
)

OpponentSpec = Union[str, Strategy, Callable[[], Strategy]]

# String names accepted by ``train_ql_agent`` / CLI (see ``make_opponent_by_name``).
OPPONENT_CHOICES = (
    "always_swerve",
    "always_stay",
    "random",
    "tit_for_tat",
    "minimax",
    "hp_threshold",
    "aggressive",
    "defensive",
)


def make_opponent_by_name(
    player: str,
    name: str,
    *,
    minimax_depth: int = 2,
    random_seed: Optional[int] = None,
) -> Strategy:
    """Build a built-in opponent strategy for ``player`` (``p1`` or ``p2``).

    Names are for convenience in the training CLI; you can always pass a
    ``Strategy`` instance or factory via ``train_ql_agent(..., opponent=...)``.
    """
    name = name.lower().replace("-", "_")
    if name in ("always_swerve", "swerve"):
        return AlwaysSwerveStrategy(player)
    if name in ("always_stay", "stay"):
        return AlwaysStayStrategy(player)
    if name in ("random", "rand"):
        return RandomStrategy(player, seed=random_seed)
    if name in ("tit_for_tat", "tft", "titfortat"):
        return TitForTatStrategy(player)
    if name in ("minimax", "minmax"):
        if minimax_depth < 1:
            raise ValueError("minimax_depth must be >= 1")
        return MinimaxStrategy(player, depth=minimax_depth)
    if name in ("hp_threshold", "hp", "threshold"):
        return HPThresholdStrategy(player)
    if name in ("aggressive", "agg"):
        return AggressiveStrategy(player)
    if name in ("defensive", "def"):
        return DefensiveStrategy(player)
    raise ValueError(f"Unknown opponent name: {name!r}; try one of {OPPONENT_CHOICES}")


def _make_naive_for_player(
    player: str,
    name: str,
    *,
    minimax_depth: int = 2,
    random_seed: Optional[int] = None,
) -> Strategy:
    return make_opponent_by_name(
        player, name, minimax_depth=minimax_depth, random_seed=random_seed
    )


def _resolve_opponent(
    spec: OpponentSpec,
    opponent_player: str,
    *,
    minimax_depth: int = 2,
    random_seed: Optional[int] = None,
) -> Strategy:
    """Build one opponent strategy for the given seat (p1 or p2)."""
    if isinstance(spec, Strategy):
        if spec.player != opponent_player:
            raise ValueError(
                f"Opponent strategy must have player={opponent_player!r}, got {spec.player!r}"
            )
        return spec
    if isinstance(spec, str):
        return _make_naive_for_player(
            opponent_player,
            spec,
            minimax_depth=minimax_depth,
            random_seed=random_seed,
        )
    return spec()


def _epsilon_for_episode(
    ep: int, total: int, start: float, end: float
) -> float:
    if total <= 1:
        return end
    t = ep / max(total - 1, 1)
    return start + (end - start) * t


@dataclass
class TrainingRunStats:
    episodes: int
    opponent: str
    agent_role: str
    wins: int
    losses: int
    ties: int
    total_p1_wins_in_score: int
    total_p2_wins_in_score: int


def train_ql_agent(
    agent: QLearningStrategy,
    opponent: OpponentSpec = "always_swerve",
    *,
    episodes: int = 200,
    max_rounds: int = 15,
    agent_plays_p1: bool = True,
    epsilon_start: Optional[float] = None,
    epsilon_end: Optional[float] = None,
    minimax_depth: int = 2,
    random_seed: Optional[int] = None,
) -> Tuple[QLearningStrategy, List[Dict[str, Any]], TrainingRunStats]:
    """Run many games; Q-table updates in-agent. Returns agent, per-episode rows, aggregate stats.

    Uses one ``GameSimulator``; each episode merges preferences and runs a full match.
    Epsilon decays linearly from ``epsilon_start`` to ``epsilon_end`` if both are set.

    For string ``opponent`` names, see ``make_opponent_by_name`` / ``OPPONENT_CHOICES``.
    ``minimax_depth`` applies when ``opponent`` is ``\"minimax\"``; ``random_seed`` when
    ``opponent`` is ``\"random\"`` (``None`` = nondeterministic).
    """
    if episodes < 1:
        raise ValueError("episodes must be >= 1")

    sim = GameSimulator()

    eps0 = epsilon_start if epsilon_start is not None else agent.epsilon
    eps1 = epsilon_end if epsilon_end is not None else agent.epsilon

    rows: List[Dict[str, Any]] = []
    wins = losses = ties = 0
    tp1 = tp2 = 0
    opp_name = ""

    for ep in range(episodes):
        agent.epsilon = _epsilon_for_episode(ep, episodes, eps0, eps1)

        if agent_plays_p1:
            p1 = agent
            p2 = _resolve_opponent(
                opponent,
                "p2",
                minimax_depth=minimax_depth,
                random_seed=random_seed,
            )
        else:
            p1 = _resolve_opponent(
                opponent,
                "p1",
                minimax_depth=minimax_depth,
                random_seed=random_seed,
            )
            p2 = agent

        opp_name = (p2 if agent_plays_p1 else p1).__class__.__name__

        result = sim.simulate(p1, p2, max_rounds=max_rounds)
        s = result["summary"]
        fs = result["final_state"]

        tp1 += s.get("p1_wins", 0)
        tp2 += s.get("p2_wins", 0)

        if agent_plays_p1:
            my_wins, their_wins = s.get("p1_wins", 0), s.get("p2_wins", 0)
        else:
            my_wins, their_wins = s.get("p2_wins", 0), s.get("p1_wins", 0)

        if my_wins > their_wins:
            wins += 1
        elif their_wins > my_wins:
            losses += 1
        else:
            ties += 1

        rows.append(
            {
                "episode": ep,
                "epsilon": agent.epsilon,
                "rounds": fs.get("round", 0),
                "p1_hp": fs.get("p1_hp"),
                "p2_hp": fs.get("p2_hp"),
                "p1_wins": s.get("p1_wins"),
                "p2_wins": s.get("p2_wins"),
            }
        )

    stats = TrainingRunStats(
        episodes=episodes,
        opponent=opp_name,
        agent_role="p1" if agent_plays_p1 else "p2",
        wins=wins,
        losses=losses,
        ties=ties,
        total_p1_wins_in_score=tp1,
        total_p2_wins_in_score=tp2,
    )
    return agent, rows, stats


def run_greedy_evaluation_episodes(
    agent: QLearningStrategy,
    opponent: OpponentSpec,
    *,
    episodes: int,
    max_rounds: int = 15,
    agent_plays_p1: bool = True,
    minimax_depth: int = 2,
    random_seed: Optional[int] = None,
) -> TrainingRunStats:
    """Evaluate the current Q-policy without learning (greedy actions only).

    Temporarily sets ``learn=False`` and ``epsilon=0``, runs the same episode loop
    as ``train_ql_agent``, then restores the previous ``learn`` and ``epsilon``.
    """
    if episodes < 1:
        raise ValueError("episodes must be >= 1")

    saved_learn = agent.learn
    saved_eps = agent.epsilon
    agent.learn = False
    agent.epsilon = 0.0
    try:
        _, _, stats = train_ql_agent(
            agent,
            opponent,
            episodes=episodes,
            max_rounds=max_rounds,
            agent_plays_p1=agent_plays_p1,
            epsilon_start=0.0,
            epsilon_end=0.0,
            minimax_depth=minimax_depth,
            random_seed=random_seed,
        )
        return stats
    finally:
        agent.learn = saved_learn
        agent.epsilon = saved_eps


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train Q-learning vs built-in or custom opponent (see make_opponent_by_name)"
    )
    parser.add_argument("--episodes", type=int, default=150)
    parser.add_argument("--max-rounds", type=int, default=12)
    parser.add_argument(
        "--opponent",
        choices=OPPONENT_CHOICES,
        default="always_swerve",
        help="Built-in opponent policy (tit_for_tat, minimax, hp_threshold, …)",
    )
    parser.add_argument("--seed", type=int, default=0, help="RNG seed for the Q-learning agent")
    parser.add_argument(
        "--minimax-depth",
        type=int,
        default=2,
        help="Search depth when --opponent minimax",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="Fixed seed for random opponent; omit for different randomness each episode",
    )
    parser.add_argument("--epsilon-start", type=float, default=0.25)
    parser.add_argument("--epsilon-end", type=float, default=0.05)
    parser.add_argument(
        "--export-q-table",
        type=str,
        default=None,
        metavar="PATH",
        help="After training, write q_table_payload JSON (for UI or analysis)",
    )
    args = parser.parse_args()

    agent = QLearningStrategy("p1", seed=args.seed)
    _, _, stats = train_ql_agent(
        agent,
        opponent=args.opponent,
        episodes=args.episodes,
        max_rounds=args.max_rounds,
        agent_plays_p1=True,
        epsilon_start=args.epsilon_start,
        epsilon_end=args.epsilon_end,
        minimax_depth=args.minimax_depth,
        random_seed=args.random_seed,
    )
    print("Training complete")
    print(f"  Episodes: {stats.episodes}  Opponent: {stats.opponent}")
    print(f"  Score wins (episode-level): agent {stats.wins}, opp {stats.losses}, ties {stats.ties}")
    print(f"  Sum of round outcomes — P1 wins: {stats.total_p1_wins_in_score}, P2: {stats.total_p2_wins_in_score}")
    print(f"  Q table size (states): {len(agent.q)}")
    if args.export_q_table:
        out = Path(args.export_q_table)
        out.parent.mkdir(parents=True, exist_ok=True)
        agent.write_q_table_json(out)
        print(f"  Wrote Q-table snapshot to {out.resolve()}")


if __name__ == "__main__":
    main()
