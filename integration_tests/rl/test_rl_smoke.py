"""Integration smoke tests for RL components (tiny, deterministic runs).

These avoid asserting "performance"; they only verify that training/tournament
pipelines execute and return correctly-shaped summaries under fixed seeds.
"""

from __future__ import annotations

from bootstrap_dot_src import add_dot_src_to_path

add_dot_src_to_path()

from ql_strategy import QLearningStrategy  # noqa: E402
from ql_tournament import run_full_tournament  # noqa: E402
from train_ql import train_ql_agent  # noqa: E402


def test_train_ql_agent_smoke_two_episodes_deterministic_seed():
    agent = QLearningStrategy("p1", seed=0)
    agent, rows, stats = train_ql_agent(
        agent,
        opponent="always_swerve",
        episodes=2,
        max_rounds=4,
        agent_plays_p1=True,
        epsilon_start=0.2,
        epsilon_end=0.2,
        minimax_depth=1,
        random_seed=0,
    )

    assert stats.episodes == 2
    assert stats.wins + stats.losses + stats.ties == 2
    assert isinstance(rows, list)
    assert len(agent.q) >= 1  # visited at least one state


def test_ql_tournament_smoke_single_opponent_single_seat():
    rows = run_full_tournament(
        opponents=["always_swerve"],
        train_episodes=2,
        test_episodes=2,
        max_rounds=4,
        agent_seed=0,
        rl_seat="p1",
        epsilon_start=0.2,
        epsilon_end=0.2,
        minimax_depth=1,
        random_seed=0,
    )
    assert len(rows) == 1
    r = rows[0]
    assert r.opponent_key == "always_swerve"
    assert r.rl_seat == "p1"
    assert r.train.episodes == 2
    assert r.test.episodes == 2
