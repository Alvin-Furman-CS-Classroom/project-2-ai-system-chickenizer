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
    st.markdown(
        "<h2 style='margin:0 0 0.4rem 0;font-size:1.38rem;font-weight:800;"
        "letter-spacing:-0.02em;line-height:1.25;color:inherit;'>"
        "One-shot Nash vs. this match</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='margin:0 0 1rem 0;font-size:1.05rem;line-height:1.6;color:inherit;max-width:52rem;'>"
        "Two small <strong>what-if</strong> tables (not a forecast of the whole match). "
        "<strong>Hypothesis</strong> = built like a brand-new game; <strong>Final</strong> = built from "
        "<strong>right now</strong> in your match. Gold boxes mark stable one-shot choices (pure Nash cells)."
        "</p>",
        unsafe_allow_html=True,
    )
    with st.expander("What you’re looking at (read once)", expanded=False):
        st.markdown(
            """
<div style="font-size:1.05rem;line-height:1.65;color:inherit;max-width:52rem;">
<p style="margin:0 0 0.85rem 0;">Each payoff cell asks: <em>if both players picked those two moves for one
round</em>, what would each player’s <strong>resilience</strong> be afterward—using the strategy weights
and the <strong>cares</strong> sliders from the sidebar.</p>
<ul style="margin:0 0 0.85rem 1.1rem;padding:0;">
<li><strong>Hypothesis</strong> table: same idea as <strong>before any rounds</strong> in a fresh game.</li>
<li><strong>Final</strong> table: same math, but using <strong>today’s</strong> HP/resilience from the live match,
so the “best responses” can move.</li>
<li><strong>Nash / NE</strong> here means “if both picked their moves <strong>at the same time</strong> once,
who would want to change?”—not the long back-and-forth of the arena.</li>
</ul>
<p style="margin:0 0 0.85rem 0;"><strong>Colors</strong> use one scale for both tables: <strong>P1 edge</strong>
= P1’s resilience minus P2’s in that cell (not “who is winning overall”).</p>
<p style="margin:0 0 0.85rem 0;"><strong>Play vs expected</strong> (after at least one round): we count how
many times each <strong>pair</strong> of moves happened in your match, and compare to a
<strong>chicken-style baseline</strong>: when the hypothesis game has pure Nash equilibria, we spread expected
probability <strong>evenly across those pure cells</strong>. <strong>Cell color</strong> = how surprising that count is
vs that baseline: pale ≈ on target, <strong>strong red</strong> = far more often than expected,
<strong>strong blue</strong> = far less often than expected.</p>
<p style="margin:0 0 0.85rem 0;"><strong>Why you might see <code>&gt;∞</code>:</strong> the baseline can assign almost no
probability to a pair. If you still saw that pair at least once, we label the ratio <code>&gt;∞</code>.
If you saw <strong>zero</strong> times and the baseline also expects <strong>zero</strong>, we show <strong>—</strong>.</p>
<p style="margin:0;"><strong>ASCII export</strong> matches the <code>nash_normal_form</code> CLI helpers for reports.</p>
</div>
            """.strip(),
            unsafe_allow_html=True,
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

    st.markdown(
        "<h3 style='margin:1rem 0 0.35rem 0;font-size:1.15rem;font-weight:700;color:inherit;'>"
        "Payoff tables &amp; equilibria</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='margin:0 0 0.75rem 0;font-size:1.02rem;line-height:1.55;color:inherit;max-width:52rem;'>"
        "Side by side: <strong>hypothesis</strong> (fresh start) vs <strong>final</strong> (current match). "
        "Each number is resilience <strong>after that one joint move</strong>, not your running total from the arena."
        "</p>",
        unsafe_allow_html=True,
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
        st.markdown(
            "<p style='margin:0 0 0.75rem 0;font-size:1rem;line-height:1.55;color:inherit;max-width:52rem;'>"
            "<strong>Play vs expected</strong> uses a <strong>uniform mix over pure Nash</strong> cells of the "
            "hypothesis game (e.g. each asymmetric chicken equilibrium gets equal expected weight when both "
            "are pure NE).</p>",
            unsafe_allow_html=True,
        )

    grids = hypothesis_final_side_by_side_html(
        hyp,
        fin,
        hypothesis_title="Hypothesis NE (fresh baseline)",
        final_title="Final NE (live match state → one-shot matrix)",
    )
    st.markdown(grids, unsafe_allow_html=True)

    if payload.joint_error:
        st.warning(f"Joint-frequency table: {payload.joint_error}")
    elif payload.joint_counts is not None and payload.n_rounds > 0:
        st.markdown(
            f"<p style='margin:0 0 0.75rem 0;font-size:1rem;line-height:1.55;color:inherit;max-width:52rem;'>"
            f"Using <strong>{payload.n_rounds}</strong> finished round(s). Each cell: how many times that "
            f"<strong>pair</strong> of moves happened, then a ratio <strong>≈ 1</strong> means about as often as "
            f"the hypothesis baseline expects. <code>&gt;∞</code> means the baseline treated that pair as nearly "
            f"impossible, but it still happened—open <strong>What you’re looking at</strong> above for the full "
            f"story. <strong>—</strong> means zero seen and ~zero expected.</p>",
            unsafe_allow_html=True,
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
