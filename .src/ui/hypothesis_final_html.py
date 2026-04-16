"""HTML for hypothesis vs final one-shot Nash matrices and joint-play vs hypothesis."""

from __future__ import annotations

import html
from typing import List, Sequence, Tuple

from nash_normal_form import (
    ACTION_LABELS,
    NormalFormResult,
    joint_play_ratio_strings,
    hypothesis_joint_distribution,
)

# --- P1-advantage heatmap (shared scale across hypothesis vs final matrices) ---
_P1_ADV_R_P2_FAVORS, _P1_ADV_G_P2_FAVORS, _P1_ADV_B_P2_FAVORS = 240, 80, 80
_P1_ADV_R_P1_FAVORS, _P1_ADV_G_P1_FAVORS, _P1_ADV_B_P1_FAVORS = 18, 200, 95
_P1_ADV_TEXT_DARK, _P1_ADV_TEXT_LIGHT = "#111111", "#f8fff8"
_P1_ADV_TEXT_LIGHT_THRESHOLD = 0.52

# --- Empirical joint-frequency heatmap ---
_JOINT_R_EMPTY, _JOINT_G_EMPTY, _JOINT_B_EMPTY = 248, 248, 255
_JOINT_R_FULL, _JOINT_G_FULL, _JOINT_B_FULL = 30, 80, 160
_JOINT_TEXT_DARK, _JOINT_TEXT_LIGHT = "#111111", "#0a1628"
_JOINT_TEXT_LIGHT_THRESHOLD = 0.45

# --- Pure NE cell highlight ---
_PURE_NE_OUTLINE_PX = 3
_PURE_NE_OUTLINE_COLOR = "#ffc107"


def _cell_rgb_p1_advantage(u1: int, u2: int, adv_min: int, adv_max: int) -> str:
    """Heatmap by P1 advantage (u1−u2); global adv_min/adv_max for comparable panels."""
    adv = u1 - u2
    if adv_max > adv_min:
        t = (adv - adv_min) / (adv_max - adv_min)
    else:
        t = 0.5
    t = max(0.0, min(1.0, t))
    r = int(_P1_ADV_R_P2_FAVORS - t * (_P1_ADV_R_P2_FAVORS - _P1_ADV_R_P1_FAVORS))
    g = int(_P1_ADV_G_P2_FAVORS + t * (_P1_ADV_G_P1_FAVORS - _P1_ADV_G_P2_FAVORS))
    b = int(_P1_ADV_B_P2_FAVORS + t * (_P1_ADV_B_P1_FAVORS - _P1_ADV_B_P2_FAVORS))
    text = _P1_ADV_TEXT_DARK if t < _P1_ADV_TEXT_LIGHT_THRESHOLD else _P1_ADV_TEXT_LIGHT
    return f"background: rgb({r},{g},{b}); color: {text};"


def _cell_rgb_empirical_rate(rate: float) -> str:
    """Background from empirical joint frequency count/N (0..1)."""
    t = max(0.0, min(1.0, rate))
    r = int(_JOINT_R_EMPTY - t * (_JOINT_R_EMPTY - _JOINT_R_FULL))
    g = int(_JOINT_G_EMPTY - t * (_JOINT_G_EMPTY - _JOINT_G_FULL))
    b = int(_JOINT_B_EMPTY - t * (_JOINT_B_EMPTY - _JOINT_B_FULL))
    text = _JOINT_TEXT_DARK if t < _JOINT_TEXT_LIGHT_THRESHOLD else _JOINT_TEXT_LIGHT
    return f"background: rgb({r},{g},{b}); color: {text};"


def _adv_extrema(a: NormalFormResult, b: NormalFormResult) -> Tuple[int, int]:
    advs: List[int] = []
    for nf in (a, b):
        for i in range(2):
            for j in range(2):
                advs.append(nf.payoff_p1[i][j] - nf.payoff_p2[i][j])
    return min(advs), max(advs)


def _one_matrix_html(
    title: str,
    nf: NormalFormResult,
    adv_min: int,
    adv_max: int,
) -> str:
    lab = list(ACTION_LABELS)
    ne_set = set(nf.pure_nash_indices)
    parts: List[str] = [
        f'<div class="hf-matrix"><div class="hf-mat-title">{html.escape(title)}</div>',
        "<table>",
        "<thead><tr><th class='hf-hdr'></th>",
        f"<th class='hf-hdr'>P2 · {html.escape(lab[0])}</th>",
        f"<th class='hf-hdr'>P2 · {html.escape(lab[1])}</th></tr></thead><tbody>",
    ]
    for i, a1 in enumerate(lab):
        parts.append("<tr>")
        parts.append(f"<th class='hf-rowh'>P1 · {html.escape(a1)}</th>")
        for j, _a2 in enumerate(lab):
            u1, u2 = nf.payoff_p1[i][j], nf.payoff_p2[i][j]
            bg = _cell_rgb_p1_advantage(u1, u2, adv_min, adv_max)
            is_ne = (i, j) in ne_set
            ne_extra = (
                f" box-shadow: inset 0 0 0 {_PURE_NE_OUTLINE_PX}px {_PURE_NE_OUTLINE_COLOR}; font-weight: 700;"
                if is_ne
                else ""
            )
            inner = f"({u1}, {u2})"
            if is_ne:
                inner += "  ·  NE"
            parts.append(f"<td style='{bg}{ne_extra}'>{html.escape(inner)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "".join(parts)


def hypothesis_final_side_by_side_html(
    hypothesis: NormalFormResult,
    final: NormalFormResult,
    *,
    hypothesis_title: str = "Hypothesis NE (fresh baseline)",
    final_title: str = "Final NE (live match state)",
) -> str:
    """Two 2×2 matrices; cell color = P1 advantage (u1−u2) on one scale across both."""
    adv_min, adv_max = _adv_extrema(hypothesis, final)
    parts = [
        "<style>",
        ".hf-wrap { font-family: system-ui, Segoe UI, sans-serif; }",
        ".hf-row { display: flex; flex-wrap: wrap; gap: 1.25rem; align-items: flex-start; }",
        ".hf-matrix { flex: 1; min-width: 280px; }",
        ".hf-matrix table { border-collapse: collapse; width: 100%; max-width: 420px; }",
        ".hf-matrix th, .hf-matrix td { border: 1px solid #555; padding: 10px 12px; text-align: center; }",
        ".hf-hdr { background: #2a2a2a; color: #eee; }",
        ".hf-rowh { background: #222; color: #ddd; font-weight: 600; }",
        ".hf-mat-title { font-weight: 700; margin-bottom: 0.45rem; color: #eaeaea; }",
        ".hf-legend { font-size: 0.85rem; color: #aaa; margin-top: 0.75rem; }",
        "</style>",
        '<div class="hf-wrap">',
        '<div class="hf-row">',
        _one_matrix_html(hypothesis_title, hypothesis, adv_min, adv_max),
        _one_matrix_html(final_title, final, adv_min, adv_max),
        "</div>",
        '<p class="hf-legend">Cell color: <strong>P1 advantage</strong> (P1 resilience − P2 resilience), '
        f"same scale across both tables (min={adv_min}, max={adv_max}). "
        "Gold outline = pure Nash equilibrium in that matrix.</p>",
        "</div>",
    ]
    return "".join(parts)


def joint_play_vs_hypothesis_html(
    counts: Sequence[int],
    hypothesis: NormalFormResult,
    *,
    n_rounds: int,
    mixed_index: int = 0,
) -> str:
    """2×2 joint play: empirical frequency heatmap + ratio vs hypothesis NE expectation."""
    if n_rounds <= 0:
        return ""

    probs = hypothesis_joint_distribution(hypothesis, mixed_index=mixed_index)
    ratios = joint_play_ratio_strings(counts, probs, n_rounds=n_rounds)
    lab = list(hypothesis.action_labels)

    parts: List[str] = [
        "<style>",
        ".jp-wrap { font-family: system-ui, Segoe UI, sans-serif; margin-top: 1rem; }",
        ".jp-wrap table { border-collapse: collapse; width: 100%; max-width: 420px; }",
        ".jp-wrap th, .jp-wrap td { border: 1px solid #555; padding: 10px 12px; text-align: center; }",
        ".jp-hdr { background: #2a2a2a; color: #eee; }",
        ".jp-rowh { background: #222; color: #ddd; font-weight: 600; }",
        ".jp-title { font-weight: 700; margin-bottom: 0.45rem; color: #eaeaea; }",
        ".jp-cap { font-size: 0.85rem; color: #aaa; margin-top: 0.5rem; }",
        "</style>",
        '<div class="jp-wrap">',
        '<div class="jp-title">Joint play vs hypothesis NE</div>',
        "<table>",
        "<thead><tr><th class='jp-hdr'></th>",
        f"<th class='jp-hdr'>P2 · {html.escape(lab[0])}</th>",
        f"<th class='jp-hdr'>P2 · {html.escape(lab[1])}</th></tr></thead><tbody>",
    ]
    idx = 0
    for i, a1 in enumerate(lab):
        parts.append("<tr>")
        parts.append(f"<th class='jp-rowh'>P1 · {html.escape(a1)}</th>")
        for j, _a2 in enumerate(lab):
            c = int(counts[idx])
            rate = c / float(n_rounds)
            bg = _cell_rgb_empirical_rate(rate)
            rtxt = ratios[idx]
            display = f"{c} / {n_rounds}   ·   {rtxt}"
            parts.append(f"<td style='{bg}'>{html.escape(display)}</td>")
            idx += 1
        parts.append("</tr>")
    hyp_src = (
        f"mixed[{mixed_index}]"
        if hypothesis.mixed_equilibria
        else ("pure mix" if hypothesis.pure_nash_indices else "uniform")
    )
    parts.append("</tbody></table>")
    parts.append(
        f'<p class="jp-cap">Each cell: <strong>observed count</strong> / N, then ratio '
        f"observed ÷ (N·Pr cell) under hypothesis NE ({hyp_src}). "
        "Background = empirical frequency in that cell.</p>"
    )
    parts.append("</div>")
    return "".join(parts)
