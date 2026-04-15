"""Tests for one-shot normal-form Nash construction and equilibrium detection.

Visual smoke (print ASCII grids to the terminal)::

    pytest -s unit_tests/test_nash_normal_form.py::TestNashAsciiVisual::test_print_sample_match_report -v

**Hypothesis vs final NE:** With the current engine, one-shot payoffs depend on merged
preferences and damage parameters in gamestate, but *not* on absolute HP (each cell
uses the HP *change* within that counterfactual round). So a typical match that only
lowers HP often leaves the normal form — and pure NE — unchanged vs the hypothesis.
NE sets *can* diverge when post-match state differs in preference weights or damage
parameters (see ``TestHypothesisVsFinalNashDivergence``).
"""

import sys
from copy import deepcopy
from pathlib import Path

import pytest

from bootstrap_dot_src import add_dot_src_to_path

add_dot_src_to_path()

import nash_normal_form as nash_nf  # noqa: E402
from engine import GameEngine  # noqa: E402
from strategies import (  # noqa: E402
    AggressiveStrategy,
    AlwaysStayStrategy,
    AlwaysSwerveStrategy,
    DefensiveStrategy,
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


class TestHypothesisVsFinalNashDivergence:
    """Hypothesis vs final pure NE need not match when gamestate inputs to the form differ."""

    def test_pure_ne_differs_when_merged_preferences_differ(self):
        """Stronger P1 round_win in the *base* gamestate shifts pure NE (same strategies)."""
        base = GameEngine().get_gamestate()
        skewed = deepcopy(base)
        skewed["p1_preferences"] = {
            **dict(skewed["p1_preferences"]),
            "round_win": 50,
            "round_loss": -50,
        }
        p1, p2 = AlwaysSwerveStrategy("p1"), AlwaysSwerveStrategy("p2")
        hyp = nash_nf.analyze_normal_form(
            p1, p2, base, include_mixed=False
        )
        fin = nash_nf.analyze_normal_form(
            p1, p2, skewed, include_mixed=False
        )
        assert hyp.payoff_p1 != fin.payoff_p1
        assert set(hyp.pure_nash_indices) != set(fin.pure_nash_indices)
        assert set(hyp.pure_nash_indices) == {(0, 1), (1, 0)}
        assert set(fin.pure_nash_indices) == {(1, 0)}

    def test_ascii_comparison_flags_non_equivalent_ne(self):
        base = GameEngine().get_gamestate()
        skewed = deepcopy(base)
        skewed["p1_preferences"] = {
            **dict(skewed["p1_preferences"]),
            "round_win": 50,
            "round_loss": -50,
        }
        p1, p2 = AlwaysSwerveStrategy("p1"), AlwaysSwerveStrategy("p2")
        hyp = nash_nf.analyze_normal_form(p1, p2, base, include_mixed=False)
        fin = nash_nf.analyze_normal_form(p1, p2, skewed, include_mixed=False)
        block = nash_nf.format_nash_hypothesis_vs_final_ascii(hyp, fin)
        assert "Payoff matrices identical: False" in block
        assert "Pure NE set identical: False" in block

    def test_hp_only_change_leaves_one_shot_matrix_and_pure_ne_unchanged(self):
        """Resilience HP terms use ΔHP within the round, not starting HP (see engine)."""
        base = GameEngine().get_gamestate()
        hurt = deepcopy(base)
        hurt["p1_hp"] = 14
        hurt["p2_hp"] = 22
        p1, p2 = AggressiveStrategy("p1"), AlwaysSwerveStrategy("p2")
        a = nash_nf.analyze_normal_form(p1, p2, base, include_mixed=False)
        b = nash_nf.analyze_normal_form(p1, p2, hurt, include_mixed=False)
        assert a.payoff_p1 == b.payoff_p1 and a.payoff_p2 == b.payoff_p2
        assert set(a.pure_nash_indices) == set(b.pure_nash_indices)


class TestNashAsciiVisual:
    def test_grid_tags_pure_nash_cells(self):
        r = nash_nf.analyze_normal_form(
            AlwaysSwerveStrategy("p1"),
            AlwaysSwerveStrategy("p2"),
            include_mixed=False,
        )
        art = nash_nf.format_nash_grid_ascii(r, include_mixed_footer=False)
        assert "*NE*" in art
        assert "(0,0)" in art or "(0, 0)" in art.replace(" ", "")
        assert "Pure NE (row_i, col_j):" in art

    def test_hypothesis_vs_final_report_includes_comparison(self):
        report = nash_nf.report_match_hypothesis_vs_final_nash(
            AlwaysSwerveStrategy("p1"),
            AlwaysSwerveStrategy("p2"),
            max_rounds=4,
            include_mixed=False,
        )
        assert "Hypothesis NE (pre-match normal form)" in report
        assert "Final NE (post-match gamestate" in report
        assert "Payoff matrices identical:" in report
        assert "Pure NE set identical:" in report
        assert "Match recap:" in report
        assert "resilience margin (P1−P2):" in report
        assert "round score tallies:" in report
        assert "final HP P1=" in report and "P2=" in report
        assert "Joint play vs hypothesis NE" in report

    def test_stacked_hypothesis_final_ascii(self):
        hyp = nash_nf.analyze_normal_form(
            AlwaysStayStrategy("p1"),
            AlwaysSwerveStrategy("p2"),
            include_mixed=False,
        )
        fin = nash_nf.analyze_normal_form(
            AlwaysStayStrategy("p1"),
            AlwaysSwerveStrategy("p2"),
            include_mixed=False,
        )
        block = nash_nf.format_nash_hypothesis_vs_final_ascii(hyp, fin)
        assert "*NE*" in block
        assert "--- Comparison ---" in block
        assert "+" in block and "|" in block

    def test_print_sample_match_report(self):
        """Run with ``pytest -s`` to view hypothesis vs final NE ASCII side by side."""
        report = nash_nf.report_match_hypothesis_vs_final_nash(
            AggressiveStrategy("p1"),
            DefensiveStrategy("p2"),
            max_rounds=8,
            include_mixed=False,
        )
        print("\n" + report + "\n")
        assert "hypothesis pure NE:" in report


class TestJointPlayVsHypothesis:
    def test_empirical_joint_counts_all_swerve(self):
        fs = {
            "p1_action_history": ["swerve"] * 4,
            "p2_action_history": ["swerve"] * 4,
        }
        assert nash_nf.empirical_joint_action_counts(fs) == (4, 0, 0, 0)

    def test_empirical_joint_counts_mixed_cells(self):
        fs = {
            "p1_action_history": ["swerve", "stay", "stay"],
            "p2_action_history": ["stay", "swerve", "stay"],
        }
        # (Sw,Sw)=0 (Sw,St)=1 (St,Sw)=2 (St,St)=3
        assert nash_nf.empirical_joint_action_counts(fs) == (0, 1, 1, 1)

    def test_hypothesis_pure_uniform_two_cells(self):
        hyp = nash_nf.NormalFormResult(
            payoff_p1=[[0, 0], [0, 0]],
            payoff_p2=[[0, 0], [0, 0]],
            p1_strategy_name="X",
            p2_strategy_name="Y",
            pure_nash_indices=[(0, 1), (1, 0)],
            mixed_equilibria=[],
        )
        p = nash_nf.hypothesis_joint_distribution(hyp)
        assert p[0] == pytest.approx(0.0)
        assert p[1] == pytest.approx(0.5)
        assert p[2] == pytest.approx(0.5)
        assert p[3] == pytest.approx(0.0)

    def test_joint_ratio_on_equilibrium_path_is_one(self):
        counts = (2, 0, 0, 0)
        probs = (1.0, 0.0, 0.0, 0.0)
        r = nash_nf.joint_play_ratio_strings(counts, probs, n_rounds=2)
        assert r[0] == "1.00"
        assert r[1] == "—"

    def test_joint_ratio_off_support_observed_is_infinity_token(self):
        counts = (0, 1, 0, 0)
        probs = (0.0, 0.0, 1.0, 0.0)
        r = nash_nf.joint_play_ratio_strings(counts, probs, n_rounds=1)
        assert r[0] == "—"
        assert r[1] == ">∞"


class TestMergeStrategyPreferences:
    def test_merge_combines_implied_prefs(self):
        eng = GameEngine()
        base = eng.get_gamestate()
        merged = merge_strategy_preferences(
            base, AggressiveStrategy("p1"), HPThresholdStrategy("p2")
        )
        assert merged["p1_preferences"].get("hp_delta") == 1
        assert merged["p2_preferences"].get("hp_delta") == 1


class TestPerRoundNormalForms:
    def test_first_snapshot_matches_at_merged_state(self):
        p1 = AlwaysStayStrategy("p1")
        p2 = AlwaysSwerveStrategy("p2")
        base = GameEngine().get_gamestate()
        merged = merge_strategy_preferences(base, p1, p2)
        snaps = nash_nf.collect_per_round_normal_forms(p1, p2, merged, max_rounds=1)
        assert len(snaps) == 1
        b1, b2 = nash_nf.build_payoff_matrices_at_merged_state(merged)
        assert snaps[0].payoff_p1 == b1
        assert snaps[0].payoff_p2 == b2

    def test_three_rounds_three_matrices(self):
        p1 = AlwaysStayStrategy("p1")
        p2 = AlwaysSwerveStrategy("p2")
        base = GameEngine().get_gamestate()
        merged = merge_strategy_preferences(base, p1, p2)
        snaps = nash_nf.collect_per_round_normal_forms(p1, p2, merged, max_rounds=3)
        assert len(snaps) == 3
        assert [s.round_index for s in snaps] == [1, 2, 3]
