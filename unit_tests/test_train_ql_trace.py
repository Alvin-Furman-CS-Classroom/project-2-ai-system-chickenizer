"""Tests for per-round training trace extraction."""

import math
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / ".src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ql_strategy import QLearningStrategy  # noqa: E402
from strategies import AlwaysSwerveStrategy, GameSimulator  # noqa: E402
from train_ql import train_ql_agent  # noqa: E402
from train_ql_trace import extract_episode_round_trace, format_training_round_trace  # noqa: E402


def test_extract_episode_matches_rounds_and_terminal_td():
    sim = GameSimulator()
    agent = QLearningStrategy("p1", seed=1, epsilon=0.0)
    p2 = AlwaysSwerveStrategy("p2")
    agent._episode_decision_trace = []
    result = sim.simulate(agent, p2, max_rounds=5)
    fs = result["final_state"]
    rows = extract_episode_round_trace(
        result, episode_index=0, agent_plays_p1=True, agent=agent
    )
    assert len(rows) == len(fs["score"])
    assert rows[-1]["ql_td_reward"] != 0.0
    text = format_training_round_trace(rows)
    assert "Q_reward" in text
    assert "Margin@move" in text
    assert "P1" in text or "swerve" in text


def test_p2_seat_first_round_q_reward_not_nan_when_multi_round():
    agent = QLearningStrategy("p2", seed=0, epsilon=0.0)
    sink: list = []
    train_ql_agent(
        agent,
        "always_swerve",
        episodes=1,
        max_rounds=5,
        agent_plays_p1=False,
        epsilon_start=0.0,
        epsilon_end=0.0,
        training_round_trace_out=sink,
        training_round_trace_max_engine_rounds=20,
    )
    assert len(sink) >= 2
    assert not math.isnan(sink[0]["ql_td_reward"])
    assert not math.isnan(sink[0]["agent_margin_at_decision"])


def test_second_episode_first_round_margin_starts_at_zero():
    """History must not treat prior episode's final snapshot as round-0 margin."""
    agent = QLearningStrategy("p1", seed=42, epsilon=0.0)
    sink: list = []
    train_ql_agent(
        agent,
        "always_swerve",
        episodes=2,
        max_rounds=6,
        epsilon_start=0.0,
        epsilon_end=0.0,
        training_round_trace_out=sink,
        training_round_trace_max_engine_rounds=20,
    )
    ep1_r1 = next(r for r in sink if r["train_episode"] == 1 and r["round_in_episode"] == 1)
    assert ep1_r1["agent_margin_at_decision"] == 0.0


def test_trace_spans_multiple_episodes_after_hp_reset():
    """Regression: training must not leave engine at 0 HP so later episodes are empty."""
    agent = QLearningStrategy("p1", seed=0, epsilon=0.0)
    sink: list = []
    train_ql_agent(
        agent,
        "always_stay",
        episodes=4,
        max_rounds=12,
        training_round_trace_out=sink,
        training_round_trace_max_engine_rounds=80,
        epsilon_start=0.0,
        epsilon_end=0.0,
    )
    eps = {r["train_episode"] for r in sink}
    assert 0 in eps and 1 in eps
    assert len(sink) > 15


def test_train_ql_agent_respects_trace_cap():
    agent = QLearningStrategy("p1", seed=0, epsilon=0.0)
    sink: list = []
    train_ql_agent(
        agent,
        "always_swerve",
        episodes=5,
        max_rounds=4,
        epsilon_start=0.0,
        epsilon_end=0.0,
        training_round_trace_out=sink,
        training_round_trace_max_engine_rounds=7,
    )
    assert len(sink) == 7
    assert sink[0]["train_episode"] == 0
    assert sink[-1]["train_episode"] == 1
