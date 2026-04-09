"""Tests for ql_tournament train+test rounds."""

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / ".src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from train_ql import OPPONENT_CHOICES  # noqa: E402

import ql_tournament as qt  # noqa: E402


class TestTrainAndTestVsOpponent:
    def test_short_run_always_swerve(self):
        agent, res = qt.train_and_test_vs_opponent(
            "always_swerve",
            train_episodes=3,
            test_episodes=2,
            max_rounds=5,
            agent_seed=1,
            epsilon_start=0.2,
            epsilon_end=0.1,
        )
        assert res.opponent_key == "always_swerve"
        assert res.rl_seat == "p1"
        assert res.train.episodes == 3
        assert res.test.episodes == 2
        assert res.train.wins + res.train.losses + res.train.ties == 3
        assert res.test.wins + res.test.losses + res.test.ties == 2
        assert len(agent.q) > 0

    def test_unknown_opponent_raises(self):
        with pytest.raises(ValueError, match="Unknown opponent"):
            qt.train_and_test_vs_opponent(
                "not_a_real_bot",
                train_episodes=1,
                test_episodes=1,
                max_rounds=3,
            )


class TestRunFullTournament:
    def test_subset_opponents_both_seats(self):
        subset = ("always_swerve", "always_stay")
        rows = qt.run_full_tournament(
            opponents=subset,
            train_episodes=2,
            test_episodes=1,
            max_rounds=4,
            agent_seed=0,
            epsilon_start=0.15,
            epsilon_end=0.15,
        )
        assert len(rows) == 4
        assert [(r.opponent_key, r.rl_seat) for r in rows] == [
            ("always_swerve", "p1"),
            ("always_swerve", "p2"),
            ("always_stay", "p1"),
            ("always_stay", "p2"),
        ]
        for r in rows:
            assert r.train.episodes == 2
            assert r.test.episodes == 1

    def test_rl_seat_p1_only_halves_rows(self):
        rows = qt.run_full_tournament(
            opponents=("always_swerve",),
            rl_seat="p1",
            train_episodes=1,
            test_episodes=1,
            max_rounds=3,
            agent_seed=0,
            epsilon_start=0.0,
            epsilon_end=0.0,
        )
        assert len(rows) == 1
        assert rows[0].rl_seat == "p1"

    def test_default_covers_all_builtin_names_and_both_seats(self):
        rows = qt.run_full_tournament(
            train_episodes=1,
            test_episodes=1,
            max_rounds=3,
            agent_seed=42,
            epsilon_start=0.0,
            epsilon_end=0.0,
        )
        assert len(rows) == 2 * len(OPPONENT_CHOICES)
        assert {r.opponent_key for r in rows} == set(OPPONENT_CHOICES)
        for key in OPPONENT_CHOICES:
            seats = {r.rl_seat for r in rows if r.opponent_key == key}
            assert seats == {"p1", "p2"}


class TestFormatTournamentReport:
    def test_contains_opponent_keys(self):
        rows = qt.run_full_tournament(
            opponents=("always_stay",),
            rl_seat="p1",
            train_episodes=1,
            test_episodes=1,
            max_rounds=3,
            agent_seed=0,
            epsilon_start=0.0,
            epsilon_end=0.0,
        )
        text = qt.format_tournament_report(rows)
        assert rows[0].rl_seat == "p1"
        assert "always_stay" in text
        assert "tr R W/L/T" in text
        assert "margin" in text
        assert "opponent_class" in text
        assert "seat" in text
