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
    st.subheader("One-shot Nash vs. this match")
    st.caption(
        "Two small **what-if** tables (not a forecast of the whole match). **Hypothesis** = built like a "
        "brand-new game; **Final** = built from **right now** in your match. Gold boxes mark stable "
        "one-shot choices (pure Nash cells)."
    )
    with st.expander("What you’re looking at (read once)", expanded=False):
        st.markdown(
            """
Each payoff cell asks: *if both players picked those two moves for one round*, what would each
player’s **resilience** be afterward—using the strategy weights and the **cares** sliders from the sidebar.

- **Hypothesis** table: same idea as **before any rounds** in a fresh game.
- **Final** table: same math, but using **today’s** HP/resilience from the live match, so the “best
  responses” can move.
- **Nash / NE** here means “if both picked their moves **at the same time** once, who would want to
  change?”—not the long back-and-forth of the arena.

**Colors** use one scale for both tables: **P1 edge** = P1’s resilience minus P2’s in that cell (not
“who is winning overall”).

**Play vs expected** (after at least one round): we count how many times each **pair** of moves
happened in your match, and compare to a **chicken-style baseline**: when the hypothesis game has
pure Nash equilibria, we spread expected probability **evenly across those pure cells** (so the two
classic asymmetric outcomes get the same expected weight). **Cell color** = how <strong>surprising</strong>
that count is vs that baseline: pale ≈ on target, <strong>intense red</strong> = far <em>more</em> often
than expected (e.g. lots of mutual swerve when the baseline puts no weight there), <strong>intense blue</strong>
= far <em>less</em> often than expected. **Stay/stay** is only “on baseline” if mutual stay is itself one
of those pure cells; otherwise a long crash streak reads as very surprising (red). Ratios near **1** in the
text mean “about on target.”

**Why you might see `>∞`:** the baseline can assign **almost no** probability to a pair (for example,
only pure equilibria on other cells). If you still saw that pair at least once, dividing “what we saw”
by “almost zero expected” would look like infinity, so we show **`>∞`** to mean **“way above what the
baseline guessed.”** If you saw **zero** times and the baseline also expects **zero**, we show **—**.

**ASCII export** matches the `nash_normal_form` CLI helpers for reports.
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
            "We couldn’t compute **mixed** equilibria for at least one table (needs **nashpy** and "
            "**numpy**). You still get pure-equilibrium outlines when they exist."
        )

    st.markdown("##### Payoff tables & equilibria")
    st.caption(
        "Side by side: **hypothesis** (fresh start) vs **final** (current match). Each number is "
        "resilience **after that one joint move**, not your running total from the arena."
    )

    n_mixed = len(hyp.mixed_equilibria)
    mixed_index = 0
    # When pure NE exist, joint "expected" uses a uniform mix over those cells (chicken intuition).
    # Mixed-index slider only matters if there are **no** pure equilibria but several mixed ones.
    if n_mixed > 1 and not hyp.pure_nash_indices:
        mixed_index = int(
            st.select_slider(
                "Which baseline mix?",
                options=list(range(n_mixed)),
                format_func=lambda i: f"Option {int(i) + 1} of {n_mixed}",
                value=0,
                key="hf_joint_mixed_index",
                help=(
                    "Several mixed Nash equilibria exist (no pure NE). Pick which self-consistent "
                    "randomization sets **expected** pair odds for **Play vs expected**."
                ),
            )
        )
    elif hyp.pure_nash_indices:
        st.caption(
            "**Play vs expected** uses a **uniform mix over pure Nash** cells of the hypothesis game "
            "(e.g. each asymmetric chicken equilibrium gets equal expected weight when both are pure NE)."
        )

    grids = hypothesis_final_side_by_side_html(
        hyp,
        fin,
        hypothesis_title="Hypothesis NE (fresh baseline)",
        final_title="Final NE (live match state → one-shot matrix)",
    )
    st.markdown(grids, unsafe_allow_html=True)

    st.markdown(
        "<p style='color:#0369a1;font-size:1.28rem;font-weight:800;margin:1.15rem 0 0.35rem;"
        "line-height:1.25;font-family:system-ui,Segoe UI,sans-serif'>"
        "Play vs expected</p>",
        unsafe_allow_html=True,
    )
    if payload.joint_error:
        st.warning(f"Joint-frequency table: {payload.joint_error}")
    elif payload.joint_counts is not None and payload.n_rounds > 0:
        st.caption(
            f"Using **{payload.n_rounds}** finished round(s). Each cell: how many times that **pair** of "
            "moves happened, then a ratio **≈ 1** means “about as often as the hypothesis baseline expects.” "
            "**>∞** means the baseline treated that pair as nearly impossible, but it still happened—open "
            "**What you’re looking at** above for the full story. **—** means zero seen and ~zero expected."
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
            "Play a full round first. Then this block compares **what you did** to **what the hypothesis "
            "table would predict** if both sides randomized the way that baseline says."
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
