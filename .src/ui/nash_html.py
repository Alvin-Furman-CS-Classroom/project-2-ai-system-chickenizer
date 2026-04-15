"""HTML/CSS helpers for rendering Nash matrices in Streamlit."""

from __future__ import annotations

import html
from typing import List

from nash_normal_form import ACTION_LABELS, RoundNormalFormSnapshot


def _cell_rgb_welfare_global(u1: int, u2: int, w_min: int, w_max: int) -> str:
    """CSS background + text color from joint welfare, normalized globally."""
    w = u1 + u2
    if w_max > w_min:
        t = (w - w_min) / (w_max - w_min)
    else:
        t = 0.5
    t = max(0.0, min(1.0, t))
    r = int(240 - t * (240 - 18))
    g = int(240 - t * (240 - 95))
    b = int(240 - t * (240 - 42))
    text = "#111111" if t < 0.45 else "#f8fff8"
    return f"background: rgb({r},{g},{b}); color: {text};"


def stacked_nash_round_matrices_html(snapshots: List[RoundNormalFormSnapshot]) -> str:
    """HTML: one 2x2 matrix per round; heatmap uses global welfare scale."""
    lab = list(ACTION_LABELS)
    all_welfare: List[int] = []
    for snap in snapshots:
        for i in range(2):
            for j in range(2):
                all_welfare.append(snap.payoff_p1[i][j] + snap.payoff_p2[i][j])
    w_min, w_max = min(all_welfare), max(all_welfare)

    parts: List[str] = [
        "<style>",
        ".nash-stack-wrap { font-family: system-ui, Segoe UI, sans-serif; }",
        ".nash-stack-wrap table { border-collapse: collapse; width: 100%; max-width: 520px; margin: 0 auto 1rem auto; }",
        ".nash-stack-wrap th, .nash-stack-wrap td { border: 1px solid #555; padding: 10px 14px; text-align: center; }",
        ".nash-stack-wrap th.hdr { background: #2a2a2a; color: #eee; }",
        ".nash-stack-wrap th.rowh { background: #222; color: #ddd; font-weight: 600; }",
        ".nash-stack-wrap .round-title { color: #eee; font-weight: 700; margin: 0.75rem 0 0.35rem 0; font-size: 1.05rem; }",
        ".nash-stack-wrap .baseline { color: #aaa; font-size: 0.85rem; margin: 0 0 0.5rem 0; }",
        "</style>",
        '<div class="nash-stack-wrap">',
    ]
    for snap in snapshots:
        ne_set = set(snap.pure_nash_indices)
        parts.append(f'<div class="round-title">Round {snap.round_index}</div>')
        parts.append(
            f'<div class="baseline">Baseline resilience at round start: '
            f"P1 = {snap.baseline_p1_resilience}, P2 = {snap.baseline_p2_resilience} "
            f"(cells show cumulative resilience after that counterfactual joint action)</div>"
        )
        parts.append("<table>")
        parts.append(
            "<thead><tr><th class='hdr'></th>"
            f"<th class='hdr'>P2 · {html.escape(lab[0])}</th>"
            f"<th class='hdr'>P2 · {html.escape(lab[1])}</th></tr></thead><tbody>"
        )
        for i, a1 in enumerate(lab):
            parts.append("<tr>")
            parts.append(f"<th class='rowh'>P1 · {html.escape(a1)}</th>")
            for j, _a2 in enumerate(lab):
                u1, u2 = snap.payoff_p1[i][j], snap.payoff_p2[i][j]
                bg_style = _cell_rgb_welfare_global(u1, u2, w_min, w_max)
                is_ne = (i, j) in ne_set
                ne_extra = (
                    " box-shadow: inset 0 0 0 3px #ffc107; font-weight: 700;"
                    if is_ne
                    else ""
                )
                cell_inner = f"({u1}, {u2})"
                if is_ne:
                    cell_inner += "  ·  NE"
                parts.append(
                    f"<td style='{bg_style}{ne_extra}'>{html.escape(cell_inner)}</td>"
                )
            parts.append("</tr>")
        parts.append("</tbody></table>")
    parts.append("</div>")
    return "".join(parts)

