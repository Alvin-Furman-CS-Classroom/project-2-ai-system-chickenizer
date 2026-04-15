"""Streamlit panel for repeated-play analysis."""

from __future__ import annotations

from typing import Any, Callable, Dict

import streamlit as st

from analysis_payloads import build_repeated_analysis_payload
from ui.nash_html import stacked_nash_round_matrices_html


def render_repeated_play_panel(
    p1_choice: Any,
    p2_choice: Any,
    p1_params: Dict[str, Any],
    p2_params: Dict[str, Any],
    p1_prefs: Dict[str, int],
    p2_prefs: Dict[str, int],
    max_rounds: int,
    *,
    build_strategy: Callable[[Any, str, Dict[str, Any]], Any],
) -> None:
    """Per-round stacked 2x2 matrices plus composite/conditional summaries."""
    st.subheader("N-round analysis (simulation)")
    p1s = build_strategy(p1_choice, "p1", p1_params)
    p2s = build_strategy(p2_choice, "p2", p2_params)
    cap = max(1, int(max_rounds))
    payload = build_repeated_analysis_payload(
        p1s,
        p2s,
        p1_prefs,
        p2_prefs,
        max_rounds=cap,
        base_gamestate=None,
    )
    merged = payload.merged_gamestate

    with st.expander("Per-round 2×2 normal forms (at round start)", expanded=True):
        st.caption(
            "Runs a **fresh** match in the engine with your sidebar strategies, up to **max rounds** "
            "(or until HP / resilience tap-out). **Before** each round’s actions, we build the same **one-shot** "
            "2×2 matrix (resilience payoffs if both sides chose Swerve/Stay that round). "
            "Each matrix uses **cares + implied preferences** (same merge as the live match). "
            "Cell values are **cumulative resilience after** that joint action from the **round-start** "
            "baseline (so totals rise/fall as the simulated match progresses). "
            "**Heatmap color** uses one **global** scale across *all* stacked rounds (min→max joint welfare "
            "over every cell), so later rounds can look darker/lighter than early ones — not just a "
            "per-round comparison. **NE** = pure Nash in that matrix (gold outline)."
        )
        with st.expander("Effective preference weights (used for each round’s payoffs)", expanded=False):
            st.markdown("**P1** `p1_preferences`")
            st.json(merged["p1_preferences"])
            st.markdown("**P2** `p2_preferences`")
            st.json(merged["p2_preferences"])

        snaps = payload.per_round_normal_forms
        if not snaps:
            st.warning("No rounds captured — game ended before the first round (check game state).")
        else:
            st.markdown(stacked_nash_round_matrices_html(snaps), unsafe_allow_html=True)
            st.caption(f"Showing **{len(snaps)}** round(s) (stopped early if the match ended).")

    with st.expander("Composite & conditional statistics (same strategies and cap)", expanded=False):
        st.caption(
            "Uses the **same** merged preferences and a **full** `run_game` simulation (not the per-round "
            "matrix snapshots above). **Composite** = how often each joint action occurs and mean **per-round** "
            "Δ resilience by cell. **Conditional** = mean next-round Δ resilience given the **previous** round’s "
            "joint action (Markov-style, comparable to Q-table transitions). This is **descriptive**, not a Nash "
            "equilibrium of the repeated game."
        )
        rp = payload.repeated_play_result
        c1, c2, c3 = st.columns(3)
        c1.metric("Rounds simulated", rp.rounds_played)
        c2.metric("Cap (max rounds)", rp.max_rounds)
        c3.metric("End reason", rp.match_end_reason or "—")

        if not rp.records:
            st.info("No rounds completed — nothing to aggregate.")
            return

        st.markdown("**Cumulative resilience**")
        st.line_chart(rp.cumulative_chart_rows(), x="round", y=["p1_cum_resilience", "p2_cum_resilience"])

        st.markdown("**Per-round Δ resilience**")
        st.line_chart(rp.per_round_delta_rows(), x="round", y=["delta_p1", "delta_p2"])

        st.markdown("**Joint action → mean per-round Δ(R1), Δ(R2)** (count *n* in cell)")
        st.dataframe(rp.joint_matrix_rows(), use_container_width=True, hide_index=True)

        st.markdown("**Previous joint action → mean *next* round Δ(R1), Δ(R2)**")
        cond = rp.conditional_rows()
        if cond:
            st.dataframe(cond, use_container_width=True, hide_index=True)
        else:
            st.caption("Need at least two rounds for conditional stats.")

        with st.popover("Round-by-round detail"):
            st.dataframe(
                [
                    {
                        "round": r.round_number,
                        "P1": r.p1_action,
                        "P2": r.p2_action,
                        "outcome": r.outcome,
                        "ΔR1": r.delta_p1_resilience,
                        "ΔR2": r.delta_p2_resilience,
                    }
                    for r in rp.records
                ],
                use_container_width=True,
                hide_index=True,
            )

