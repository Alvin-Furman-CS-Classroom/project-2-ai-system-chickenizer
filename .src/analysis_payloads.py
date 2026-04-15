"""Reusable (non-UI) analysis payload builders for Chickenizer.

This module exists to decouple Streamlit rendering from the underlying analysis
steps so the same computations can be reused in CLI tools, tests, or other UIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from engine import GameEngine
from nash_normal_form import (
    RoundNormalFormSnapshot,
    analyze_normal_form,
    best_response_correspondences,
    collect_per_round_normal_forms,
)
from nash_repeated_analysis import analyze_repeated_play
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
class OneShotNashPayload:
    merged_gamestate: Dict[str, Any]
    # NormalFormResult type lives in `nash_normal_form` but we keep this payload UI-agnostic.
    normal_form_result: Any
    best_responses: Dict[str, Any]
    mixed_skipped: bool


def build_one_shot_nash_payload(
    p1_strategy: Strategy,
    p2_strategy: Strategy,
    p1_cares: PreferenceDict,
    p2_cares: PreferenceDict,
    *,
    live_base_gamestate: Optional[Dict[str, Any]] = None,
    include_mixed: bool = True,
) -> OneShotNashPayload:
    """Build merged state + normal-form Nash analysis + best responses."""
    merged = merge_gamestate_with_strategy_and_cares(
        p1_strategy,
        p2_strategy,
        p1_cares,
        p2_cares,
        base_gamestate=live_base_gamestate,
    )

    mixed_skipped = False
    if include_mixed:
        try:
            nf = analyze_normal_form(p1_strategy, p2_strategy, merged, include_mixed=True)
        except Exception:  # noqa: BLE001 - optional deps (nashpy/numpy) and edge cases
            nf = analyze_normal_form(p1_strategy, p2_strategy, merged, include_mixed=False)
            mixed_skipped = True
    else:
        nf = analyze_normal_form(p1_strategy, p2_strategy, merged, include_mixed=False)
        mixed_skipped = True

    br = best_response_correspondences(nf.payoff_p1, nf.payoff_p2)
    return OneShotNashPayload(
        merged_gamestate=merged,
        normal_form_result=nf,
        best_responses=br,
        mixed_skipped=mixed_skipped,
    )


@dataclass(frozen=True)
class RepeatedAnalysisPayload:
    merged_gamestate: Dict[str, Any]
    per_round_normal_forms: List[RoundNormalFormSnapshot]
    repeated_play_result: Any


def build_repeated_analysis_payload(
    p1_strategy: Strategy,
    p2_strategy: Strategy,
    p1_cares: PreferenceDict,
    p2_cares: PreferenceDict,
    *,
    max_rounds: int,
    base_gamestate: Optional[Dict[str, Any]] = None,
) -> RepeatedAnalysisPayload:
    """Build per-round normal forms and repeated-play aggregates from the same merged setup."""
    cap = max(1, int(max_rounds))
    merged = merge_gamestate_with_strategy_and_cares(
        p1_strategy, p2_strategy, p1_cares, p2_cares, base_gamestate=base_gamestate
    )

    snaps = collect_per_round_normal_forms(p1_strategy, p2_strategy, merged, max_rounds=cap)
    rp = analyze_repeated_play(p1_strategy, p2_strategy, merged, max_rounds=cap)
    return RepeatedAnalysisPayload(
        merged_gamestate=merged,
        per_round_normal_forms=snaps,
        repeated_play_result=rp,
    )

