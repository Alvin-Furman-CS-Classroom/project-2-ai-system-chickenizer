"""Tests for QLearningStrategy and state encoding."""

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / ".src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from engine import GameEngine  # noqa: E402
from ql_strategy import QLearningStrategy, encode_ql_state  # noqa: E402
from strategies import AlwaysSwerveStrategy, GameSimulator  # noqa: E402


class TestEncodeState:
    def test_p1_start(self):
        eng = GameEngine()
        gs = eng.get_gamestate()
        assert encode_ql_state("p1", gs) == (2, 2, 2)

    def test_p2_sees_p1(self):
        gs = {
            "p1_resilience": 0,
            "p2_resilience": 0,
            "p1_action_history": ["stay"],
            "p2_action_history": [],
        }
        t = encode_ql_state("p2", gs)
        assert t[2] == 1  # opp = stay


class TestQLearningSmoke:
    def test_simulate_finishes_and_has_q_entries(self):
        sim = GameSimulator()
        p1 = QLearningStrategy("p1", seed=0, epsilon=0.5)
        p2 = AlwaysSwerveStrategy("p2")
        r = sim.simulate(p1, p2, max_rounds=5)
        assert r["summary"]["rounds_played"] == 5
        assert len(p1.q) > 0

    def test_finalize_idempotent_safe(self):
        p1 = QLearningStrategy("p1", seed=1)
        eng = GameEngine()
        p1.finalize_episode(eng.get_gamestate())
        p1.finalize_episode(eng.get_gamestate())
