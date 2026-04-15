"""Streamlit panel for one-shot normal-form Nash analysis."""

from __future__ import annotations

from typing import Any, Dict, Optional, Callable

import streamlit as st

from analysis_payloads import build_one_shot_nash_payload
from nash_normal_form import ACTION_LABELS


def render_nash_normal_form_panel(
    p1_choice: Any,
    p2_choice: Any,
    p1_params: Dict[str, Any],
    p2_params: Dict[str, Any],
    p1_prefs: Dict[str, int],
    p2_prefs: Dict[str, int],
    *,
    build_strategy: Callable[[Any, str, Dict[str, Any]], Any],
    live_base_gamestate: Optional[Dict[str, Any]] = None,
) -> None:
    """2x2 payoff matrix (resilience) and Nash summary for sidebar configuration."""
    st.subheader("One-shot normal form & Nash")
    with st.expander("Payoff matrix and equilibria (from sidebar selections)", expanded=False):
        st.caption(
            "Each cell is **(P1 resilience, P2 resilience)** after one **simultaneous** counterfactual "
            "round — **cumulative** values from the **current** baseline (not reset to zero), so they "
            "track the match. **Before a game starts**, baseline is 0/0; **after rounds**, they use "
            "the live **match state** when available. Preferences: **engine defaults + implied + cares** "
            "(sliders override by key). **Pure/mixed Nash** depend on payoff *differences*, so they usually "
            "match the same game with zero baseline)."
        )
        p1s = build_strategy(p1_choice, "p1", p1_params)
        p2s = build_strategy(p2_choice, "p2", p2_params)
        payload = build_one_shot_nash_payload(
            p1s,
            p2s,
            p1_prefs,
            p2_prefs,
            live_base_gamestate=live_base_gamestate,
            include_mixed=True,
        )
        merged = payload.merged_gamestate
        with st.expander("Effective preference weights (used for Nash payoffs)", expanded=False):
            st.markdown("**P1** `p1_preferences`")
            st.json(merged["p1_preferences"])
            st.markdown("**P2** `p2_preferences`")
            st.json(merged["p2_preferences"])
        result = payload.normal_form_result
        if payload.mixed_skipped:
            st.caption(
                "Mixed equilibria skipped; showing pure Nash only. "
                "Ensure **nashpy** and **numpy** are installed."
            )

        lab = list(ACTION_LABELS)
        ne_set = set(result.pure_nash_indices)
        table_rows = []
        for i, a1 in enumerate(lab):
            row: Dict[str, Any] = {"P1 \\ P2": f"P1 · {a1}"}
            for j, a2 in enumerate(lab):
                u1 = result.payoff_p1[i][j]
                u2 = result.payoff_p2[i][j]
                cell = f"({u1}, {u2})"
                if (i, j) in ne_set:
                    cell += "  [NE]"
                row[f"P2 · {a2}"] = cell
            table_rows.append(row)
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

        br = payload.best_responses
        st.markdown("**Pure best responses** (row index = Swerve→0, Stay→1)")
        st.write(
            {
                "If P2 plays Swerve, P1 best row(s)": br["p1_best_rows_given_p2_col"][0],
                "If P2 plays Stay, P1 best row(s)": br["p1_best_rows_given_p2_col"][1],
                "If P1 plays Swerve, P2 best col(s)": br["p2_best_cols_given_p1_row"][0],
                "If P1 plays Stay, P2 best col(s)": br["p2_best_cols_given_p1_row"][1],
            }
        )

        if result.pure_nash_indices:
            profiles = [f"P1 {lab[i]} / P2 {lab[j]}" for i, j in result.pure_nash_indices]
            st.success("Pure-strategy Nash: " + " · ".join(profiles))
        else:
            st.info("No pure-strategy Nash equilibrium in this induced normal form.")

        if result.mixed_equilibria:
            st.markdown("**Mixed Nash** (probabilities over Swerve, then Stay)")
            for k, (sig, rho) in enumerate(result.mixed_equilibria, 1):
                st.write(f"— Profile {k}: P1 σ = {sig}, P2 ρ = {rho}")
        else:
            st.caption("No mixed equilibrium computed (or none found).")

