"""HTML for hypothesis vs final one-shot Nash matrices and joint-play vs hypothesis."""

from __future__ import annotations

import html
import math
from typing import List, Sequence, Tuple

from nash_normal_form import (
    ACTION_LABELS,
    NormalFormResult,
    joint_play_ratio_strings,
    hypothesis_joint_distribution_for_joint_display,
)

# --- P1-advantage heatmap (shared scale across hypothesis vs final matrices) ---
_P1_ADV_R_P2_FAVORS, _P1_ADV_G_P2_FAVORS, _P1_ADV_B_P2_FAVORS = 240, 80, 80
_P1_ADV_R_P1_FAVORS, _P1_ADV_G_P1_FAVORS, _P1_ADV_B_P1_FAVORS = 18, 200, 95
_P1_ADV_TEXT_DARK, _P1_ADV_TEXT_LIGHT = "#111111", "#f8fff8"
_P1_ADV_TEXT_LIGHT_THRESHOLD = 0.52

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


# Joint-play "weirdness": log((O+½)/(E+½)) vs baseline expected count E = N·p.
# Intensity = how far from 0 in log space (symmetric); sign = over vs under baseline.
_JP_LOG_WEIRD_CAP = 2.05


def _cell_rgb_joint_surprise(obs: int, exp_n: float) -> str:
    """Background intensity ∝ surprise vs baseline; warm = too often, cool = too rare, soft = on target."""
    o = float(obs)
    e = max(0.0, float(exp_n))
    ratio_smoothed = (o + 0.5) / (e + 0.5)
    w = math.log(max(ratio_smoothed, 1e-15))
    s = max(-1.0, min(1.0, w / _JP_LOG_WEIRD_CAP))
    # Slightly favor vivid colors before hitting the cap (moderate surprises read stronger).
    intensity = min(1.0, abs(s) ** 0.92)

    neutral = (218, 224, 222)
    hot = (255, 48, 38)
    cold = (28, 92, 200)

    if intensity < 0.05:
        r, g, b = neutral
    elif s > 0.0:
        t = intensity
        r = int(neutral[0] + t * (hot[0] - neutral[0]))
        g = int(neutral[1] + t * (hot[1] - neutral[1]))
        b = int(neutral[2] + t * (hot[2] - neutral[2]))
    else:
        t = intensity
        r = int(neutral[0] + t * (cold[0] - neutral[0]))
        g = int(neutral[1] + t * (cold[1] - neutral[1]))
        b = int(neutral[2] + t * (cold[2] - neutral[2]))

    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    txt = "#111111" if lum > 0.68 else "#f8fafc"
    return f"background: rgb({r},{g},{b}); color: {txt};"


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
        '<p class="hf-legend">Color = <strong>P1 edge</strong> (P1 resilience minus P2’s in that cell), '
        f"same scale in both tables (range {adv_min}…{adv_max}). "
        "Gold outline = a **pure** equilibrium cell for that table (neither side wants to switch alone).</p>",
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
    """2×2 joint play: cell color intensity = how surprising vs baseline NE (log-ratio surprise)."""
    if n_rounds <= 0:
        return ""

    probs = hypothesis_joint_distribution_for_joint_display(hypothesis, mixed_index=mixed_index)
    ratios = joint_play_ratio_strings(counts, probs, n_rounds=n_rounds)
    lab = list(hypothesis.action_labels)

    parts: List[str] = [
        "<style>",
        ".jp-wrap { font-family: system-ui, Segoe UI, sans-serif; margin-top: 1rem; }",
        ".jp-wrap table { border-collapse: collapse; width: 100%; max-width: 420px; }",
        ".jp-wrap th, .jp-wrap td { border: 1px solid #555; padding: 10px 12px; text-align: center; }",
        ".jp-hdr { background: #2a2a2a; color: #eee; }",
        ".jp-rowh { background: #222; color: #ddd; font-weight: 600; }",
        ".jp-title { font-weight: 800; margin-bottom: 0.5rem; font-size: 1.12rem; letter-spacing: 0.01em; "
        "color: #0369a1; }",
        ".jp-cap { font-size: 0.88rem; color: #475569; margin-top: 0.55rem; line-height: 1.45; }",
        "@media (prefers-color-scheme: dark) {",
        "  .jp-title { color: #7dd3fc; }",
        "  .jp-cap { color: #cbd5e1; }",
        "}",
        "</style>",
        '<div class="jp-wrap">',
        '<div class="jp-title">Play vs expected</div>',
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
            p = float(probs[idx])
            exp_n = float(n_rounds) * p
            bg = _cell_rgb_joint_surprise(c, exp_n)
            rtxt = ratios[idx]
            display = f"{c} / {n_rounds}   ·   {rtxt}"
            parts.append(f"<td style='{bg}'>{html.escape(display)}</td>")
            idx += 1
        parts.append("</tr>")
    if hypothesis.pure_nash_indices:
        hyp_src = f"uniform over {len(hypothesis.pure_nash_indices)} pure NE cell(s)"
    elif hypothesis.mixed_equilibria:
        hyp_src = f"mixed[{mixed_index}]"
    else:
        hyp_src = "uniform 1/4"
    parts.append("</tbody></table>")
    parts.append(
        f'<p class="jp-cap">Each cell: <strong>count</strong> of rounds with that move pair (out of '
        f"<strong>N = {n_rounds}</strong>), then <strong>observed ÷ expected</strong> under baseline "
        f"<em>{html.escape(hyp_src)}</em>. "
        "<strong>Background</strong> = how <em>surprising</em> that count is vs the baseline: soft gray-green "
        "≈ “about what we’d guess,” <strong>strong red</strong> ≈ happened <em>way</em> more than the baseline "
        "expects (including “expected ~0 but you saw it a lot”), <strong>strong blue</strong> ≈ happened "
        "much <em>less</em> than expected. "
        "<strong>&gt;∞</strong> in the text means the baseline gave that pair almost no weight but you still "
        "saw it—the number would be enormous, so we shorten the label. "
        "<strong>—</strong> = never seen and (almost) never expected.</p>"
    )
    parts.append("</div>")
    return "".join(parts)
