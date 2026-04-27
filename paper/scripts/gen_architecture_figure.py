"""Generate paper/figures/architecture.png for the term paper (no TikZ required)."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).resolve().parent.parent / "figures" / "architecture.png"


def _box(ax, xy, w, h, text, fc):
    x, y = xy
    p = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        linewidth=1.0,
        edgecolor="#333333",
        facecolor=fc,
    )
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8)


def _arrow(ax, p0, p1, dashed=False):
    ax.add_patch(
        FancyArrowPatch(
            p0,
            p1,
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=0.9,
            color="#333333",
            linestyle="--" if dashed else "-",
        )
    )


def main() -> None:
    fig, ax = plt.subplots(figsize=(7.0, 3.8), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.2)
    ax.axis("off")

    _box(ax, (0.2, 4.15), 2.0, 0.7, "Strategy rules\nconstraints", "#e3f2fd")
    _box(ax, (2.6, 4.15), 2.0, 0.7, "Payoff matrix\nturn order", "#e3f2fd")
    _box(ax, (1.3, 3.0), 2.4, 0.7, "module1_kb\nCNF / chaining", "#e8f5e9")
    _box(ax, (0.2, 1.85), 2.1, 0.7, "strategies", "#e8f5e9")
    _box(ax, (2.6, 1.85), 2.4, 0.7, "engine\nsimulation", "#e8f5e9")
    _box(ax, (0.2, 0.7), 2.3, 0.7, "nash_normal_form", "#fff3e0")
    _box(ax, (2.7, 0.7), 2.3, 0.7, "nash_repeated_analysis", "#fff3e0")
    _box(ax, (5.4, 2.5), 2.2, 0.7, "analysis_payloads", "#f3e5f5")
    _box(ax, (5.4, 1.35), 2.0, 0.7, "Streamlit UI", "#eceff1")
    _box(ax, (5.4, 0.25), 2.0, 0.7, "Q-learning", "#eceff1")

    _arrow(ax, (1.2, 4.15), (2.2, 3.75))
    _arrow(ax, (3.6, 4.15), (2.8, 3.75))
    _arrow(ax, (2.5, 3.0), (1.25, 2.6))
    _arrow(ax, (2.5, 3.0), (3.8, 2.6))
    _arrow(ax, (1.25, 1.85), (1.35, 1.45))
    _arrow(ax, (3.8, 1.85), (3.85, 1.45))
    _arrow(ax, (1.35, 0.7), (1.35, 1.35))
    _arrow(ax, (3.85, 0.7), (3.85, 1.35))
    _arrow(ax, (2.5, 1.2), (5.4, 2.85))
    _arrow(ax, (1.35, 1.0), (5.4, 2.55))
    _arrow(ax, (4.5, 1.85), (5.4, 1.7), dashed=True)
    _arrow(ax, (3.8, 2.2), (6.4, 1.05), dashed=True)

    ax.legend(
        handles=[
            mpatches.Patch(facecolor="#e3f2fd", edgecolor="#333", label="Inputs"),
            mpatches.Patch(facecolor="#e8f5e9", edgecolor="#333", label="Core"),
            mpatches.Patch(facecolor="#fff3e0", edgecolor="#333", label="Nash / repeated"),
            mpatches.Patch(facecolor="#f3e5f5", edgecolor="#333", label="Analysis"),
            mpatches.Patch(facecolor="#eceff1", edgecolor="#333", label="Optional"),
        ],
        loc="lower right",
        fontsize=7,
        frameon=True,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    plt.close(fig)
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
