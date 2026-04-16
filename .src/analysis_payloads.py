"""Reusable (non-UI) analysis payload builders for Chickenizer.

This module exists to decouple Streamlit rendering from the underlying analysis
steps so the same computations can be reused in CLI tools, tests, or other UIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from engine import GameEngine
from nash_normal_form import (
    analyze_normal_form_from_merged_state,
    empirical_joint_action_counts,
)
from strategies import Strategy, merge_strategy_preferences


PreferenceDict = Dict[str, int]


def merge_gamestate_with_strategy_and_cares(
    p1_strategy: Strategy,
    p2_strategy: Strategy,
    p1_cares: PreferenceDict,
    p2_cares: PreferenceDict,
    *,
    base_gamestate: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Engine defaults (or ``base_gamestate``) + implied preferences, then cares override by key."""
    base = GameEngine().get_gamestate() if base_gamestate is None else base_gamestate
    enriched = merge_strategy_preferences(base, p1_strategy, p2_strategy)
    enriched["p1_preferences"] = {**enriched["p1_preferences"], **dict(p1_cares)}
    enriched["p2_preferences"] = {**enriched["p2_preferences"], **dict(p2_cares)}
    return enriched


@dataclass(frozen=True)
class HypothesisVsFinalPayload:
    """Hypothesis (fresh baseline) vs final (live match) one-shot NE, plus joint-play stats."""

    hypothesis_merged: Dict[str, Any]
    final_merged: Dict[str, Any]
    hypothesis_nf: Any
    final_nf: Any
    mixed_skipped_hypothesis: bool
    mixed_skipped_final: bool
    joint_counts: Optional[Tuple[int, int, int, int]]
    n_rounds: int
    joint_error: Optional[str]


def _nf_from_merged_safe(
    p1_strategy: Strategy,
    p2_strategy: Strategy,
    merged: Dict[str, Any],
    *,
    include_mixed: bool,
) -> Tuple[Any, bool]:
    mixed_skipped = False
    if include_mixed:
        try:
            nf = analyze_normal_form_from_merged_state(
                p1_strategy, p2_strategy, merged, include_mixed=True
            )
        except Exception:  # noqa: BLE001
            nf = analyze_normal_form_from_merged_state(
                p1_strategy, p2_strategy, merged, include_mixed=False
            )
            mixed_skipped = True
    else:
        nf = analyze_normal_form_from_merged_state(
            p1_strategy, p2_strategy, merged, include_mixed=False
        )
        mixed_skipped = True
    return nf, mixed_skipped


def build_hypothesis_vs_final_payload(
    p1_strategy: Strategy,
    p2_strategy: Strategy,
    p1_cares: PreferenceDict,
    p2_cares: PreferenceDict,
    *,
    live_base_gamestate: Optional[Dict[str, Any]] = None,
    include_mixed: bool = True,
) -> HypothesisVsFinalPayload:
    """Hypothesis NE from a **fresh** engine state; final NE from **live** state when given.

    Joint-action counts come from ``live_base_gamestate`` (match history), same as
    the ASCII ``report_match_hypothesis_vs_final_nash`` joint table.
    """
    hypothesis_merged = merge_gamestate_with_strategy_and_cares(
        p1_strategy,
        p2_strategy,
        p1_cares,
        p2_cares,
        base_gamestate=None,
    )
    final_merged = merge_gamestate_with_strategy_and_cares(
        p1_strategy,
        p2_strategy,
        p1_cares,
        p2_cares,
        base_gamestate=live_base_gamestate,
    )

    hyp_nf, skip_h = _nf_from_merged_safe(
        p1_strategy, p2_strategy, hypothesis_merged, include_mixed=include_mixed
    )
    fin_nf, skip_f = _nf_from_merged_safe(
        p1_strategy, p2_strategy, final_merged, include_mixed=include_mixed
    )

    joint_counts: Optional[Tuple[int, int, int, int]] = None
    joint_error: Optional[str] = None
    n_rounds = 0
    if live_base_gamestate is not None:
        h1 = live_base_gamestate.get("p1_action_history") or []
        n_rounds = len(h1)
        if n_rounds > 0:
            try:
                joint_counts = empirical_joint_action_counts(live_base_gamestate)
            except ValueError as exc:
                joint_error = str(exc)

    return HypothesisVsFinalPayload(
        hypothesis_merged=hypothesis_merged,
        final_merged=final_merged,
        hypothesis_nf=hyp_nf,
        final_nf=fin_nf,
        mixed_skipped_hypothesis=skip_h,
        mixed_skipped_final=skip_f,
        joint_counts=joint_counts,
        n_rounds=n_rounds,
        joint_error=joint_error,
    )

