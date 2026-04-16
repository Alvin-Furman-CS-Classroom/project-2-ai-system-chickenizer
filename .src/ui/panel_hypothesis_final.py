"""Hypothesis vs final one-shot Nash (UI counterpart to ASCII in ``nash_normal_form``)."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Protocol, Type

import streamlit as st

from analysis_payloads import build_hypothesis_vs_final_payload
from nash_normal_form import (
    format_joint_play_vs_hypothesis_ascii,
    format_nash_hypothesis_vs_final_ascii,
)
from strategies import Strategy
from ui.hypothesis_final_html import (
    hypothesis_final_side_by_side_html,
    joint_play_vs_hypothesis_html,
)


class StrategyUIPick(Protocol):
    """Structural type for sidebar strategy rows (``StrategyChoice`` in ``streamlit_app``).

    Uses read-only properties so frozen dataclasses (``frozen=True``) structurally match
    (Pyright treats plain Protocol attributes as mutable, which conflicts with frozen fields).
    """

    @property
    def label(self) -> str: ...

    @property
    def cls(self) -> Type[Strategy]: ...


def render_hypothesis_vs_final_panel(
    p1_choice: StrategyUIPick,
    p2_choice: StrategyUIPick,
    p1_params: Dict[str, Any],
    p2_params: Dict[str, Any],
    p1_prefs: Dict[str, int],
    p2_prefs: Dict[str, int],
    *,
    build_strategy: Callable[[StrategyUIPick, str, Dict[str, Any]], Strategy],
    live_base_gamestate: Optional[Dict[str, Any]] = None,
) -> None:
    """Side-by-side hypothesis / final NE, joint-play table, optional ASCII export."""
    st.subheader("Strategic snapshot: one-shot Nash vs. your match")
    st.markdown(
        """
This section is a **static 2×2 “what-if”** for *one simultaneous round*, not a prediction of repeated
play. Each cell answers: *if P1 played the row action and P2 the column action*, what would each
player’s **resilience** be **after that single counterfactual round**, using your strategies and
preference weights from the sidebar (engine defaults, each strategy’s implied weights, then your
**cares** sliders on top).

- **Hypothesis** builds that game from a **fresh** baseline—the same starting state you get before a
  new match. Think of it as the normal form “on paper” before anything happens in *this* run.
- **Final** rebuilds the same one-shot game from the **live** match state (HP, resilience, etc.).
  After rounds, the baseline can shift, so payoffs and **Nash equilibria** can **change** vs. the hypothesis.
- **Nash equilibrium (NE)** here means a **Nash equilibrium of this one-shot matrix** (pure cells
  are marked with a gold outline; mixed equilibria may exist when indifference holds).
        """.strip()
    )

    with st.expander("Colors, joint play, and technical notes", expanded=False):
        st.markdown(
            """
**Matrix colors** use one scale across **both** tables: **P1 advantage** = P1 resilience minus P2
resilience in that cell (warmer / greener → better for P1 relative to P2). That is **not** “who is
winning the match”; it compares the two players’ *counterfactual* one-shot payoffs in that cell.

**Joint play vs hypothesis** appears after at least one completed round. For each of the four
(joint actions), you see how often it occurred, and a **ratio**: observed count divided by what you’d
expect under the **hypothesis** equilibrium if rounds were i.i.d. (mixed NE is averaged when several
pure NE exist). The table background reflects **empirical frequency** (how often that joint action
happened), not matrix payoffs.

**ASCII export** is the same text layout as the CLI helpers in `nash_normal_form`, for copying into
reports or diffing runs.
            """.strip()
        )

    p1s = build_strategy(p1_choice, "p1", p1_params)
    p2s = build_strategy(p2_choice, "p2", p2_params)
    payload = build_hypothesis_vs_final_payload(
        p1s,
        p2s,
        p1_prefs,
        p2_prefs,
        live_base_gamestate=live_base_gamestate,
        include_mixed=True,
    )

    hyp = payload.hypothesis_nf
    fin = payload.final_nf

    if payload.mixed_skipped_hypothesis or payload.mixed_skipped_final:
        st.info(
            "Mixed equilibria could not be computed for at least one matrix (install **nashpy** and "
            "**numpy** for mixed NE, or use pure-NE only). Pure NE outlines still show when present."
        )

    st.markdown("##### Payoff matrices & Nash equilibria")
    st.caption(
        "Compare **hypothesis** (cold start) vs **final** (current engine state). Numbers are "
        "resilience after that single hypothetical joint action."
    )

    n_mixed = len(hyp.mixed_equilibria)
    mixed_index = 0
    if n_mixed > 1:
        mixed_index = int(
            st.select_slider(
                "Hypothesis mixed NE index (for joint-play probabilities)",
                options=list(range(n_mixed)),
                value=0,
                key="hf_joint_mixed_index",
            )
        )

    grids = hypothesis_final_side_by_side_html(
        hyp,
        fin,
        hypothesis_title="Hypothesis NE (fresh baseline)",
        final_title="Final NE (live match state → one-shot matrix)",
    )
    st.markdown(grids, unsafe_allow_html=True)

    st.markdown("##### Joint play vs hypothesis equilibrium")
    if payload.joint_error:
        st.warning(f"Joint-frequency table: {payload.joint_error}")
    elif payload.joint_counts is not None and payload.n_rounds > 0:
        st.caption(
            f"Using **N = {payload.n_rounds}** completed round(s). Ratios compare observed counts to "
            "expected counts under the hypothesis NE distribution."
        )
        jp = joint_play_vs_hypothesis_html(
            payload.joint_counts,
            hyp,
            n_rounds=payload.n_rounds,
            mixed_index=mixed_index,
        )
        st.markdown(jp, unsafe_allow_html=True)
    else:
        st.info(
            "**Joint play** appears after at least one completed round: it tallies how often each "
            "pair of actions occurred and compares that to the hypothesis NE."
        )

    with st.expander("ASCII export (same as CLI helpers)", expanded=False):
        ascii_block = format_nash_hypothesis_vs_final_ascii(
            hyp,
            fin,
            hypothesis_caption="Hypothesis NE (pre-match normal form)",
            final_caption="Final NE (post-match gamestate → one-shot matrix)",
        )
        if payload.joint_counts is not None and payload.n_rounds > 0 and not payload.joint_error:
            ascii_block += "\n\n" + format_joint_play_vs_hypothesis_ascii(
                payload.joint_counts,
                hyp,
                n_rounds=payload.n_rounds,
                mixed_index=mixed_index,
            )
        st.code(ascii_block, language=None)
