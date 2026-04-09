"""Tests for QLearningStrategy and state encoding."""

import json
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / ".src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from engine import GameEngine  # noqa: E402
from ql_strategy import (  # noqa: E402
    QLearningStrategy,
    encode_ql_state,
    terminal_margin_bonus,
)
from strategies import AlwaysSwerveStrategy, GameSimulator  # noqa: E402


class TestTerminalMarginBonus:
    def test_round_cap_tied_margin_no_terminal_bonus(self):
        gs = {
            "match_end_reason": "round_cap",
            "p1_hp": 100,
            "p2_hp": 100,
            "resilience_diff": 0,
        }
        assert (
            terminal_margin_bonus("p1", gs, terminal_win=50.0, terminal_loss=50.0) == 0.0
        )

    def test_round_cap_no_bonus_even_if_margin_ahead(self):
        """Horn ending: no terminal spike; decisive endings use HP / tap only."""
        gs = {
            "match_end_reason": "round_cap",
            "p1_hp": 100,
            "p2_hp": 100,
            "resilience_diff": 3,
        }
        assert (
            terminal_margin_bonus("p1", gs, terminal_win=50.0, terminal_loss=50.0) == 0.0
        )

    def test_round_cap_overrides_stale_zero_hp_on_snapshot(self):
        """Horn wins if ``match_end_reason`` says so (ignore inconsistent HP fields)."""
        gs = {
            "match_end_reason": "round_cap",
            "p1_hp": 100,
            "p2_hp": 0,
            "resilience_diff": 20,
        }
        assert (
            terminal_margin_bonus("p1", gs, terminal_win=50.0, terminal_loss=50.0) == 0.0
        )

    def test_hp_knockout_no_bonus_when_resilience_still_tied(self):
        """Symmetric crashes keep diff 0; HP-only win must not inject +50."""
        gs = {
            "match_end_reason": "p2_hp_zero",
            "p1_hp": 40,
            "p2_hp": 0,
            "resilience_diff": 0,
        }
        assert (
            terminal_margin_bonus("p1", gs, terminal_win=50.0, terminal_loss=50.0) == 0.0
        )

    def test_hp_knockout_bonus_when_margin_separated(self):
        gs = {
            "match_end_reason": "p2_hp_zero",
            "p1_hp": 40,
            "p2_hp": 0,
            "resilience_diff": 15,
        }
        assert terminal_margin_bonus(
            "p1", gs, terminal_win=50.0, terminal_loss=50.0
        ) == pytest.approx(50.0)


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


class TestQTableExport:
    def test_q_table_records_columns_stable(self):
        sim = GameSimulator()
        p1 = QLearningStrategy("p1", seed=0, epsilon=0.5)
        p2 = AlwaysSwerveStrategy("p2")
        sim.simulate(p1, p2, max_rounds=5)
        rows = p1.q_table_records()
        assert len(rows) == len(p1.q)
        for row in rows:
            assert set(row.keys()) == {
                "own_res_bin",
                "own_resilience_bin",
                "my_last_code",
                "my_last",
                "opp_last_code",
                "opp_last",
                "q_swerve",
                "q_stay",
                "greedy_action",
            }
            assert row["greedy_action"] in ("stay", "swerve")

    def test_q_table_payload_json_roundtrip(self, tmp_path):
        sim = GameSimulator()
        p1 = QLearningStrategy("p1", seed=2, epsilon=0.3)
        p2 = AlwaysSwerveStrategy("p2")
        sim.simulate(p1, p2, max_rounds=4)
        payload = p1.q_table_payload()
        json.dumps(payload)  # must be JSON-serializable
        out = tmp_path / "q.json"
        p1.write_q_table_json(out)
        loaded = json.loads(out.read_text(encoding="utf-8"))
        assert loaded["schema_version"] == 1
        assert loaded["player"] == "p1"
        assert len(loaded["rows"]) == len(payload["rows"])
