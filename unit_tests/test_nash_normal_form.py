"""Tests for one-shot normal-form Nash construction and equilibrium detection."""

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / ".src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import nash_normal_form as nash_nf  # noqa: E402
from engine import GameEngine  # noqa: E402
from strategies import (  # noqa: E402
    AlwaysStayStrategy,
    AlwaysSwerveStrategy,
    AggressiveStrategy,
    HPThresholdStrategy,
    merge_strategy_preferences,
)

build_payoff_matrices = nash_nf.build_payoff_matrices
find_pure_nash = nash_nf.find_pure_nash


class TestPayoffMatrix:
    def test_default_prefs_classic_chicken_payoffs(self):
        p1_m, p2_m = build_payoff_matrices(
            AlwaysSwerveStrategy("p1"),
            AlwaysSwerveStrategy("p2"),
        )
        assert p1_m[0][0] == 0 and p2_m[0][0] == 0
        assert p1_m[1][0] == 10 and p2_m[1][0] == -10
        assert p1_m[0][1] == -10 and p2_m[0][1] == 10
        assert p1_m[1][1] == -15 and p2_m[1][1] == -15

    def test_implied_preferences_affect_payoffs(self):
        p1 = AggressiveStrategy("p1")
        p2 = AlwaysSwerveStrategy("p2")
        p1_m, p2_m = build_payoff_matrices(p1, p2)
        assert p1_m[1][1] == -25
        assert p2_m[1][1] == -15

    def test_wrong_player_ids_raise(self):
        with pytest.raises(ValueError, match="p1"):
            build_payoff_matrices(AlwaysSwerveStrategy("p2"), AlwaysSwerveStrategy("p2"))
        with pytest.raises(ValueError, match="p2"):
            build_payoff_matrices(AlwaysSwerveStrategy("p1"), AlwaysSwerveStrategy("p1"))


class TestPureNash:
    def test_two_pure_asymmetric_chicken(self):
        p1_m = [[0, -10], [10, -15]]
        p2_m = [[0, 10], [-10, -15]]
        ne = find_pure_nash(p1_m, p2_m)
        assert (1, 0) in ne
        assert (0, 1) in ne
        assert len(ne) == 2

    def test_two_pure_coordination(self):
        p1_m = [[1, 0], [0, 1]]
        p2_m = [[1, 0], [0, 1]]
        ne = find_pure_nash(p1_m, p2_m)
        assert set(ne) == {(0, 0), (1, 1)}


class TestAnalyzeAndFormat:
    def test_analyze_pure_nash_default_prefs(self):
        r = nash_nf.analyze_normal_form(
            AlwaysSwerveStrategy("p1"),
            AlwaysSwerveStrategy("p2"),
            include_mixed=False,
        )
        assert set(r.pure_nash_indices) == {(1, 0), (0, 1)}
        text = nash_nf.format_nash_table(r)
        assert "NE" in text
        assert "Mixed Nash: none found" in text or "skipped" in text

    def test_format_includes_strategy_names(self):
        r = nash_nf.analyze_normal_form(
            HPThresholdStrategy("p1"),
            AlwaysStayStrategy("p2"),
            include_mixed=False,
        )
        s = nash_nf.format_nash_table(r)
        assert "HPThresholdStrategy" in s
        assert "AlwaysStayStrategy" in s

    def test_mixed_nash_when_nashpy_available(self):
        pytest.importorskip("nashpy")
        r = nash_nf.analyze_normal_form(
            AlwaysSwerveStrategy("p1"),
            AlwaysSwerveStrategy("p2"),
            include_mixed=True,
        )
        assert r.mixed_equilibria
        t = nash_nf.format_nash_table(r)
        assert "σ=" in t


class TestBestResponseCorrespondences:
    def test_classic_chicken(self):
        p1_m = [[0, -10], [10, -15]]
        p2_m = [[0, 10], [-10, -15]]
        br = nash_nf.best_response_correspondences(p1_m, p2_m)
        assert br["p1_best_rows_given_p2_col"] == [[1], [0]]
        assert br["p2_best_cols_given_p1_row"] == [[1], [0]]


class TestNormalFormToDict:
    def test_shape_and_pure_nash(self):
        r = nash_nf.analyze_normal_form(
            AlwaysSwerveStrategy("p1"),
            AlwaysSwerveStrategy("p2"),
            include_mixed=False,
        )
        d = nash_nf.normal_form_to_dict(r, include_best_responses=True)
        assert d["p1_strategy_name"] == "AlwaysSwerveStrategy"
        assert d["action_labels"] == ["Swerve", "Stay"]
        assert len(d["payoff_p1"]) == 2 and len(d["payoff_p1"][0]) == 2
        assert {tuple(x) for x in d["pure_nash_indices"]} == {(1, 0), (0, 1)}
        br = d["best_responses"]
        assert br["p1_best_rows_given_p2_col"] == [[1], [0]]
        assert br["p2_best_cols_given_p1_row"] == [[1], [0]]

    def test_without_best_responses(self):
        r = nash_nf.analyze_normal_form(
            AlwaysSwerveStrategy("p1"),
            AlwaysSwerveStrategy("p2"),
            include_mixed=False,
        )
        d = nash_nf.normal_form_to_dict(r, include_best_responses=False)
        assert "best_responses" not in d


class TestMergeStrategyPreferences:
    def test_merge_combines_implied_prefs(self):
        eng = GameEngine()
        base = eng.get_gamestate()
        merged = merge_strategy_preferences(
            base, AggressiveStrategy("p1"), HPThresholdStrategy("p2")
        )
        assert merged["p1_preferences"].get("hp_delta") == 1
        assert merged["p2_preferences"].get("hp_delta") == 1
