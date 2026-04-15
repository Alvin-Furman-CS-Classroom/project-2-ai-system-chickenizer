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

from ql_strategy import QLearningStrategy, agent_resilience_margin  # noqa: E402
from train_ql_trace import (  # noqa: E402
    extract_episode_round_trace,
    format_training_round_trace,
)
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
    resilience_leader_p1_seat,
    resilience_margin_p1_minus_p2,
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
    """Linear ε schedule: episode ``0`` uses ``start``, last episode uses ``end``.

    With multiple episodes of similar length, the **expected** fraction of exploratory
    moves is about ``(start + end) / 2``, not ``start`` — ε is lower on later episodes.
    A single episode uses ``start`` (there is no "last episode" distinct from the first).
    """
    if total <= 1:
        return start
    t = ep / (total - 1)
    return start + (end - start) * t


def _episode_outcome_from_resilience(
    final_state: Dict[str, Any], agent_plays_p1: bool
) -> str:
    """Classify one finished match using final **resilience margin** (same objective as Q rewards).

    Margin is ``resilience_diff`` (P1−P2) from the agent's perspective:
    P1 maximizes it; P2 maximizes its negation. Falls back to per-player
    resilience fields if ``resilience_diff`` is absent.
    """
    role = "p1" if agent_plays_p1 else "p2"
    m = agent_resilience_margin(role, final_state)
    if m > 0:
        return "win"
    if m < 0:
        return "loss"
    return "tie"


@dataclass
class TrainingRunStats:
    """Per-run aggregates after many simulated episodes.

    ``wins`` / ``losses`` / ``ties`` count **episodes** by **final resilience margin**
    (P1−P2 from the agent's seat — same zero-sum notion as Q-learning step rewards),
    not round-by-round ``score`` tallies.

    ``total_p1_wins_in_score`` / ``total_p2_wins_in_score`` sum per-round ``\"P1\"`` /
    ``\"P2\"`` counts from summaries across episodes (auxiliary, for inspection).
    """

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
    training_round_trace_out: Optional[List[Dict[str, Any]]] = None,
    training_round_trace_max_engine_rounds: int = 0,
) -> Tuple[QLearningStrategy, List[Dict[str, Any]], TrainingRunStats]:
    """Run many games; Q-table updates in-agent. Returns agent, per-episode rows, aggregate stats.

    Uses one ``GameSimulator``; each episode merges preferences and runs a full match.
    Epsilon is **constant within** an episode and decays **linearly across** episodes
    from ``epsilon_start`` (episode 0) to ``epsilon_end`` (last episode). Over a long
    run with similar episode lengths, the fraction of exploratory decisions is near
    ``(epsilon_start + epsilon_end) / 2`` (e.g. 0.25→0.05 gives ~15%), not
    ``epsilon_start`` alone.

    Aggregate ``wins`` / ``losses`` / ``ties`` use **final resilience margin** per
    episode (aligned with Q-learning rewards), not round ``score`` counts — see
    ``TrainingRunStats``.

    For string ``opponent`` names, see ``make_opponent_by_name`` / ``OPPONENT_CHOICES``.
    ``minimax_depth`` applies when ``opponent`` is ``\"minimax\"``; ``random_seed`` when
    ``opponent`` is ``\"random\"`` (``None`` = nondeterministic).

    Optional training trace: pass ``training_round_trace_out=[]`` and set
    ``training_round_trace_max_engine_rounds`` > 0 to append per-engine-round rows
    (actions, margins, ``ql_td_reward``, exploration flags) for the **first** cumulative
    rounds of training across episodes. Use ``format_training_round_trace`` to print.
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

        tracing = (
            training_round_trace_out is not None
            and training_round_trace_max_engine_rounds > 0
            and len(training_round_trace_out) < training_round_trace_max_engine_rounds
        )
        agent._episode_decision_trace = [] if tracing else None

        result = sim.simulate(p1, p2, max_rounds=max_rounds)
        s = result["summary"]
        fs = result["final_state"]

        if tracing:
            remaining = training_round_trace_max_engine_rounds - len(
                training_round_trace_out
            )
            if remaining > 0:
                ep_rows = extract_episode_round_trace(
                    result,
                    episode_index=ep,
                    agent_plays_p1=agent_plays_p1,
                    agent=agent,
                )
                training_round_trace_out.extend(ep_rows[:remaining])

        tp1 += s.get("p1_wins", 0)
        tp2 += s.get("p2_wins", 0)

        outcome = _episode_outcome_from_resilience(fs, agent_plays_p1)
        if outcome == "win":
            wins += 1
        elif outcome == "loss":
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
                "p1_resilience": fs.get("p1_resilience"),
                "p2_resilience": fs.get("p2_resilience"),
                "resilience_diff": fs.get("resilience_diff"),
                "resilience_margin_p1_minus_p2": resilience_margin_p1_minus_p2(fs),
                "resilience_leader": resilience_leader_p1_seat(fs),
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
    agent._episode_decision_trace = None
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
    Episode W/L/T in returned stats match ``train_ql_agent`` (margin-based).
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
        "--seat",
        choices=("p1", "p2"),
        default="p1",
        help="Seat for the Q-learning agent (opponent takes the other seat)",
    )
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
    parser.add_argument(
        "--epsilon-start",
        type=float,
        default=0.25,
        help="exploration probability at first training episode (then decays linearly to --epsilon-end)",
    )
    parser.add_argument(
        "--epsilon-end",
        type=float,
        default=0.05,
        help="exploration probability at last training episode",
    )
    parser.add_argument(
        "--export-q-table",
        type=str,
        default=None,
        metavar="PATH",
        help="After training, write q_table_payload JSON (for UI or analysis)",
    )
    parser.add_argument(
        "--trace-engine-rounds",
        type=int,
        default=0,
        metavar="N",
        help=(
            "Print first N engine-round rows after training (one row per joint round). "
            "Use -1 to trace every round of this run (episodes × max-rounds). "
            "Pipe through `less -S` for long tables."
        ),
    )
    args = parser.parse_args()

    agent = QLearningStrategy(args.seat, seed=args.seed)
    trace_out: Optional[List[Dict[str, Any]]] = None
    if args.trace_engine_rounds == -1:
        trace_max = max(1, args.episodes * args.max_rounds)
    elif args.trace_engine_rounds > 0:
        trace_max = args.trace_engine_rounds
    else:
        trace_max = 0
    if trace_max > 0:
        trace_out = []
    _, _, stats = train_ql_agent(
        agent,
        opponent=args.opponent,
        episodes=args.episodes,
        max_rounds=args.max_rounds,
        agent_plays_p1=(args.seat == "p1"),
        epsilon_start=args.epsilon_start,
        epsilon_end=args.epsilon_end,
        minimax_depth=args.minimax_depth,
        random_seed=args.random_seed,
        training_round_trace_out=trace_out,
        training_round_trace_max_engine_rounds=trace_max,
    )
    print("Training complete")
    print(f"  Episodes: {stats.episodes}  Opponent: {stats.opponent}")
    print(
        f"  Episode outcomes (final resilience margin — agent win/loss/tie): "
        f"{stats.wins} / {stats.losses} / {stats.ties}"
    )
    print(
        f"  Sum of per-round score labels (not margin): "
        f"P1={stats.total_p1_wins_in_score}, P2={stats.total_p2_wins_in_score}"
    )
    print(f"  Q table size (states): {len(agent.q)}")
    if trace_out:
        print()
        print(format_training_round_trace(trace_out), end="")
    if args.export_q_table:
        out = Path(args.export_q_table)
        out.parent.mkdir(parents=True, exist_ok=True)
        agent.write_q_table_json(out)
        print(f"  Wrote Q-table snapshot to {out.resolve()}")


if __name__ == "__main__":
    main()
