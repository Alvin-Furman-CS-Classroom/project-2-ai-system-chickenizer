"""Pairwise benchmark: Monte Carlo built-ins vs on-policy Q-learning.

**Resilience margin** (same as ``train_ql``) classifies each **episode** and drives **share**
and W–L–T. Q strip cells also show **mean final margin** ``μΔ`` from the agent’s seat
(``agent_resilience_margin``), summarizing how decisively the agent won or lost on average.

**Layout**

- **Left:** one **n×n** Monte Carlo grid (P1 rows × P2 cols) + colorbar.
- **Right of that grid:** **Q as P2** vertical strip (``sharey`` with the grid so P1 labels line up with rows).
  Strategy names are on the **right** side of that strip.
- **Below the grid column only (same width as n×n):** **Q as P1** horizontal strip vs each P2.
- **Bottom-right mosaic cell:** hatch **legend** (uses the spare column beside ``q1``).

Run (slow)::

    python .src/ql_pairwise_heatmap_benchmark.py --out ql_pairwise_heatmap.png

Smoke run::

    python .src/ql_pairwise_heatmap_benchmark.py --fast --out pairwise_smoke.png
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ql_strategy import QLearningStrategy, agent_resilience_margin  # noqa: E402
from strategies import GameSimulator, Strategy  # noqa: E402
from train_ql import (  # noqa: E402
    OPPONENT_CHOICES,
    make_opponent_by_name,
    train_ql_agent,
)

_AGENT_SEED_P1_STRIP = 10_007
_AGENT_SEED_P2_STRIP = 30_011


@dataclass(frozen=True)
class OutcomeCell:
    """Aggregated **resilience-margin** episode outcomes (``train_ql`` convention)."""

    share: float
    wins: int
    losses: int
    ties: int
    episodes: int
    mean_margin: Optional[float] = None  # greedy Q only: mean final margin from agent seat

    @property
    def win_rate(self) -> float:
        return self.wins / max(1, self.episodes)

    @property
    def loss_rate(self) -> float:
        return self.losses / max(1, self.episodes)

    @property
    def tie_rate(self) -> float:
        return self.ties / max(1, self.episodes)


def _p1_episode_resilience_wlt(final_state: dict) -> Tuple[int, int, int]:
    """Win / loss / tie for **P1** from final margin (same rule as ``train_ql``)."""
    m = agent_resilience_margin("p1", final_state)
    if m > 0:
        return (1, 0, 0)
    if m < 0:
        return (0, 1, 0)
    return (0, 0, 1)


def _cell_from_counts(wins: int, losses: int, ties: int, episodes: int) -> OutcomeCell:
    if episodes < 1:
        return OutcomeCell(0.0, 0, 0, 0, 0, None)
    share = (float(wins) + 0.5 * float(ties)) / float(episodes)
    return OutcomeCell(share, wins, losses, ties, episodes, None)


def monte_carlo_outcome_grid(
    *,
    labels: Tuple[str, ...],
    episodes: int,
    max_rounds: int,
    minimax_depth: int,
    base_seed: int,
) -> List[List[OutcomeCell]]:
    """``[i][j]`` = MC aggregate for P1 = ``labels[i]`` vs P2 = ``labels[j]`` (P1 lens)."""
    n = len(labels)
    sim = GameSimulator()
    grid: List[List[OutcomeCell]] = []

    for i, ki in enumerate(labels):
        row: List[OutcomeCell] = []
        for j, kj in enumerate(labels):
            w = l = t = 0
            for ep in range(episodes):
                seed = base_seed + 17 * i + 31 * j + 97 * ep
                p1 = make_opponent_by_name(
                    "p1", ki, minimax_depth=minimax_depth, random_seed=seed
                )
                p2 = make_opponent_by_name(
                    "p2", kj, minimax_depth=minimax_depth, random_seed=seed + 1
                )
                result = sim.simulate(p1, p2, max_rounds=max_rounds)
                aw, al, at = _p1_episode_resilience_wlt(result["final_state"])
                w += aw
                l += al
                t += at
            row.append(_cell_from_counts(w, l, t, episodes))
        grid.append(row)
    return grid


def _greedy_resilience_eval_cell(
    agent: QLearningStrategy,
    opp: Strategy,
    *,
    episodes: int,
    max_rounds: int,
    agent_plays_p1: bool,
) -> OutcomeCell:
    """Greedy eval: same margin W/L/T as ``train_ql``, plus mean final margin for the agent."""
    sim = GameSimulator()
    role = "p1" if agent_plays_p1 else "p2"
    w = l = t = 0
    margin_sum = 0.0
    saved_learn, saved_eps = agent.learn, agent.epsilon
    agent.learn = False
    agent.epsilon = 0.0
    try:
        for _ in range(episodes):
            if agent_plays_p1:
                r = sim.simulate(agent, opp, max_rounds=max_rounds)
            else:
                r = sim.simulate(opp, agent, max_rounds=max_rounds)
            fs = r["final_state"]
            m = float(agent_resilience_margin(role, fs))
            margin_sum += m
            if m > 0:
                w += 1
            elif m < 0:
                l += 1
            else:
                t += 1
    finally:
        agent.learn = saved_learn
        agent.epsilon = saved_eps
    ep = max(1, episodes)
    share = (float(w) + 0.5 * float(t)) / float(ep)
    return OutcomeCell(share, w, l, t, episodes, mean_margin=margin_sum / float(ep))


def ql_on_policy_strip_as_p1(
    *,
    labels: Tuple[str, ...],
    train_episodes: int,
    greedy_episodes: int,
    max_rounds: int,
    minimax_depth: int,
    epsilon_start: float,
    epsilon_end: float,
    agent_seed: int,
    random_seed: Optional[int],
) -> List[OutcomeCell]:
    """Column *k* = train vs P2 ``labels[k]``, greedy-eval vs same P2 (Q as P1)."""
    out: List[OutcomeCell] = []
    for k, name in enumerate(labels):
        agent = QLearningStrategy("p1", seed=agent_seed + _AGENT_SEED_P1_STRIP + k)
        train_ql_agent(
            agent,
            name,
            episodes=train_episodes,
            max_rounds=max_rounds,
            agent_plays_p1=True,
            epsilon_start=epsilon_start,
            epsilon_end=epsilon_end,
            minimax_depth=minimax_depth,
            random_seed=random_seed,
        )
        opp = make_opponent_by_name(
            "p2",
            name,
            minimax_depth=minimax_depth,
            random_seed=random_seed,
        )
        out.append(
            _greedy_resilience_eval_cell(
                agent,
                opp,
                episodes=greedy_episodes,
                max_rounds=max_rounds,
                agent_plays_p1=True,
            )
        )
    return out


def ql_on_policy_strip_as_p2(
    *,
    labels: Tuple[str, ...],
    train_episodes: int,
    greedy_episodes: int,
    max_rounds: int,
    minimax_depth: int,
    epsilon_start: float,
    epsilon_end: float,
    agent_seed: int,
    random_seed: Optional[int],
) -> List[OutcomeCell]:
    """Row *k* = train vs P1 ``labels[k]``, greedy-eval vs same P1 (Q as P2); order = P1 row order."""
    out: List[OutcomeCell] = []
    for k, name in enumerate(labels):
        agent = QLearningStrategy("p2", seed=agent_seed + _AGENT_SEED_P2_STRIP + k)
        train_ql_agent(
            agent,
            name,
            episodes=train_episodes,
            max_rounds=max_rounds,
            agent_plays_p1=False,
            epsilon_start=epsilon_start,
            epsilon_end=epsilon_end,
            minimax_depth=minimax_depth,
            random_seed=random_seed,
        )
        opp = make_opponent_by_name(
            "p1",
            name,
            minimax_depth=minimax_depth,
            random_seed=random_seed,
        )
        out.append(
            _greedy_resilience_eval_cell(
                agent,
                opp,
                episodes=greedy_episodes,
                max_rounds=max_rounds,
                agent_plays_p1=False,
            )
        )
    return out


def _outcome_hatch(c: OutcomeCell) -> Optional[str]:
    """Softer hatch: shorter strings, higher thresholds."""
    if c.episodes < 1:
        return None
    wr, lr, tr = c.win_rate, c.loss_rate, c.tie_rate
    if lr > wr + 0.08:
        return "/" * min(2, 1 + int(1.2 * (lr - wr)))
    if tr > max(wr, lr) + 0.08:
        return "o"
    if wr > lr + 0.08:
        return "." * min(2, 1 + int(1.2 * (wr - lr)))
    return None


def _text_color_for_face(rgba) -> str:
    r, g, b = rgba[0], rgba[1], rgba[2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "white" if lum < 0.55 else "black"


def _cell_label_lines(c: OutcomeCell) -> str:
    lines = [f"{c.share:.2f}", f"{c.wins}-{c.losses}-{c.ties}"]
    if c.mean_margin is not None:
        lines.append(f"μΔ{c.mean_margin:+.1f}")
    return "\n".join(lines)


def _draw_outcome_cell_rect(
    ax,
    *,
    i0: float,
    j0: float,
    w: float,
    h: float,
    c: OutcomeCell,
    cmap,
    fontsize: float,
) -> None:
    from matplotlib import colors as mcolors
    from matplotlib.patches import Rectangle

    face = cmap(np.clip(c.share, 0.0, 1.0))
    hatch = _outcome_hatch(c)
    rect = Rectangle(
        (j0, i0),
        w,
        h,
        facecolor=face,
        edgecolor="#222222",
        linewidth=1.9,
        hatch=hatch,
        zorder=1,
    )
    ax.add_patch(rect)
    if hatch == "o":
        # Hatch color follows the dark cell edge by default; tie circles then look like bold rings.
        # Matplotlib stores hatch ink on ``_hatch_color`` (no public setter on all versions).
        setattr(rect, "_hatch_color", mcolors.to_rgba("#c8c8c8"))
    ax.text(
        j0 + w * 0.5,
        i0 + h * 0.5,
        _cell_label_lines(c),
        ha="center",
        va="center",
        fontsize=fontsize,
        color=_text_color_for_face(face),
        linespacing=0.88,
        zorder=6,
    )


def _draw_matrix_grid(
    ax,
    cells: List[List[OutcomeCell]],
    tick: List[str],
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    fontsize: float = 5.0,
) -> None:
    import matplotlib.pyplot as plt

    n = len(cells)
    cmap = plt.get_cmap("RdYlGn")
    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    for i in range(n):
        for j in range(n):
            _draw_outcome_cell_rect(
                ax,
                i0=float(n - 1 - i),
                j0=float(j),
                w=1.0,
                h=1.0,
                c=cells[i][j],
                cmap=cmap,
                fontsize=fontsize,
            )
    ax.set_xticks([j + 0.5 for j in range(n)])
    ax.set_xticklabels(tick, fontsize=7, rotation=45, ha="right")
    # Row i = P1 strategy i occupies y in [n-1-i, n-i]; tick at center n - 0.5 - i.
    ax.set_yticks([n - 0.5 - i for i in range(n)])
    ax.set_yticklabels(tick, fontsize=7)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=11)
    ax.set_aspect("equal")
    ax.set_frame_on(False)


def _draw_horizontal_strip(
    ax,
    cells: List[OutcomeCell],
    tick: List[str],
    *,
    title: str,
    xlabel: str,
    fontsize: float = 5.5,
) -> None:
    import matplotlib.pyplot as plt

    n = len(cells)
    cmap = plt.get_cmap("RdYlGn")
    ax.set_xlim(0, n)
    ax.set_ylim(0, 1)
    for k, c in enumerate(cells):
        _draw_outcome_cell_rect(
            ax,
            i0=0.0,
            j0=float(k),
            w=1.0,
            h=1.0,
            c=c,
            cmap=cmap,
            fontsize=fontsize,
        )
    ax.set_xticks([k + 0.5 for k in range(n)])
    ax.set_xticklabels(tick, fontsize=7, rotation=45, ha="right")
    ax.set_yticks([])
    ax.set_ylabel("")
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontsize=11)
    ax.set_frame_on(False)


def _draw_vertical_strip(
    ax,
    cells: List[OutcomeCell],
    tick: List[str],
    *,
    title: str,
    fontsize: float = 5.5,
) -> None:
    """Draw Q-as-P2 cells; y ticks / labels come from ``sharey`` + caller (right side)."""
    import matplotlib.pyplot as plt

    n = len(cells)
    cmap = plt.get_cmap("RdYlGn")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, n)
    for k, c in enumerate(cells):
        _draw_outcome_cell_rect(
            ax,
            i0=float(n - 1 - k),
            j0=0.0,
            w=1.0,
            h=1.0,
            c=c,
            cmap=cmap,
            fontsize=fontsize,
        )
    ax.set_xticks([0.5])
    ax.set_xticklabels(["Q\n(P2)"], fontsize=8)
    ax.set_xlabel("")
    ax.set_title(title, fontsize=10)
    ax.set_frame_on(False)


def _add_hatch_legend(ax) -> None:
    """Hatch key in the spare bottom-right axes (``axis('off')`` + ``legend``)."""
    from matplotlib import colors as mcolors
    from matplotlib.patches import Patch

    # Strong swatch frames so hatch reads clearly inside the legend.
    _edge = "#1f1f1f"
    _lw = 2.15
    loss_patch = Patch(
        facecolor="#eaeaea",
        edgecolor=_edge,
        linewidth=_lw,
        hatch="//",
        label="Loss-heavy",
    )
    tie_patch = Patch(
        facecolor="#eaeaea",
        edgecolor=_edge,
        linewidth=_lw,
        hatch="o",
        label="Tie-heavy",
    )
    setattr(tie_patch, "_hatch_color", mcolors.to_rgba("#b8b8b8"))
    setattr(loss_patch, "_hatch_color", mcolors.to_rgba("#4a4a4a"))
    win_patch = Patch(
        facecolor="#eaeaea",
        edgecolor=_edge,
        linewidth=_lw,
        hatch="..",
        label="Win-heavy",
    )
    setattr(win_patch, "_hatch_color", mcolors.to_rgba("#4a4a4a"))
    bal_patch = Patch(
        facecolor="#eaeaea",
        edgecolor=_edge,
        linewidth=_lw,
        label="Balanced (no hatch)",
    )

    handles = [loss_patch, tie_patch, win_patch, bal_patch]
    ax.axis("off")
    leg = ax.legend(
        handles=handles,
        loc="center",
        fontsize=14,
        frameon=True,
        fancybox=False,
        facecolor="#f7f7f7",
        edgecolor="#2a2a2a",
        title="Game outcome tendency",
        title_fontsize=16,
        borderpad=1.45,
        labelspacing=1.35,
        handlelength=5.5,
        handleheight=2.05,
        handletextpad=1.25,
    )
    leg.get_frame().set_linewidth(2.0)


def _short_label(k: str) -> str:
    return k.replace("_", "\n")[:18]


def _figure_content_center_x(fig) -> float:
    """Figure x in [0, 1] at the horizontal midpoint of all axes' bounding boxes."""
    boxes = [ax.get_position() for ax in fig.axes]
    if not boxes:
        return 0.5
    return 0.5 * (min(b.x0 for b in boxes) + max(b.x1 for b in boxes))


def plot_benchmark_figure(
    *,
    labels: Tuple[str, ...],
    mc_p1_cells: List[List[OutcomeCell]],
    ql_p1_cells: List[OutcomeCell],
    ql_p2_cells: List[OutcomeCell],
    out_path: Path,
) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    tick = [_short_label(k) for k in labels]

    # Backends take hatch stroke width from rc at draw time (not per-patch).
    with plt.rc_context({"hatch.linewidth": 0.22}):
        fig, axd = plt.subplot_mosaic(
            [["mc", "q2"], ["q1", "leg"]],
            figsize=(14, 11),
            gridspec_kw={
                "height_ratios": [4.2, 1.15],
                "width_ratios": [5.0, 1.55],
                "hspace": 0.34,
                "wspace": 0.22,
                "left": 0.07,
                "right": 0.92,
                "top": 0.90,
                "bottom": 0.14,
            },
        )
        ax_mc = axd["mc"]
        ax_q2 = axd["q2"]
        ax_q1 = axd["q1"]
        ax_leg = axd["leg"]
        ax_q2.sharey(ax_mc)

        _draw_matrix_grid(
            ax_mc,
            mc_p1_cells,
            tick,
            title="P1 (rows) vs P2 (columns)\nBuilt-in pairings (Monte Carlo)",
            xlabel="P2",
            ylabel="P1",
            fontsize=5.0,
        )
        sm_mc = ScalarMappable(norm=Normalize(0.0, 1.0), cmap="RdYlGn")
        sm_mc.set_array([])
        fig.colorbar(sm_mc, ax=ax_mc, fraction=0.046, pad=0.04, label="Share (resilience)")

        _draw_vertical_strip(
            ax_q2,
            ql_p2_cells,
            tick,
            title="Q as P2",
            fontsize=5.2,
        )
        ax_mc.tick_params(axis="y", which="major", labelleft=True, labelright=False)
        ax_q2.tick_params(axis="y", which="major", labelleft=False, labelright=True)
        ax_q2.yaxis.set_label_position("right")
        ax_q2.set_ylabel("P1 (opponent)", fontsize=9, labelpad=6)

        _draw_horizontal_strip(
            ax_q1,
            ql_p1_cells,
            tick,
            title="Q-learning as P1 (train & greedy vs each P2)",
            xlabel="P2 (opponent)",
            fontsize=5.2,
        )

        # ``fig.colorbar(..., ax=ax_mc)`` shrinks ``ax_mc`` horizontally; ``ax_q1`` stays full
        # mosaic-cell width — re-match bbox so P2 tick marks line up with the heatmap columns.
        ax_q1.sharex(ax_mc)
        mc_pos = ax_mc.get_position()
        q1_pos = ax_q1.get_position()
        ax_q1.set_position([mc_pos.x0, q1_pos.y0, mc_pos.width, q1_pos.height])

        _add_hatch_legend(ax_leg)
        # Center on the union of mosaic + colorbar (not the bare figure; ``x=0.5`` skews right).
        fig.suptitle(
            "Heatmap of pairwise strategy matchups",
            fontsize=20,
            y=0.97,
            x=_figure_content_center_x(fig),
            ha="center",
        )
        fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Monte Carlo grid + Q strips (resilience margin; μΔ on Q cells)."
    )
    parser.add_argument("--out", type=Path, default=Path("ql_pairwise_heatmap.png"))
    parser.add_argument("--fast", action="store_true", help="Tiny episode counts for smoke runs.")
    parser.add_argument("--mc-episodes", type=int, default=120)
    parser.add_argument("--train-episodes", type=int, default=180)
    parser.add_argument("--greedy-episodes", type=int, default=60)
    parser.add_argument("--max-rounds", type=int, default=12)
    parser.add_argument("--minimax-depth", type=int, default=2)
    parser.add_argument("--epsilon-start", type=float, default=0.25)
    parser.add_argument("--epsilon-end", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="Seed for random/entertainer/reputation opponents (default: --seed).",
    )
    args = parser.parse_args()
    if args.fast:
        args.mc_episodes = 8
        args.train_episodes = 12
        args.greedy_episodes = 6
        args.max_rounds = 8

    labels = OPPONENT_CHOICES
    rs = args.random_seed if args.random_seed is not None else args.seed

    print(f"Monte Carlo grid ({len(labels)}×{len(labels)}), {args.mc_episodes} eps/cell …")
    mc_p1_cells = monte_carlo_outcome_grid(
        labels=labels,
        episodes=args.mc_episodes,
        max_rounds=args.max_rounds,
        minimax_depth=args.minimax_depth,
        base_seed=args.seed,
    )

    print("Q-learning on-policy strip (P1 seat) …")
    q_p1 = ql_on_policy_strip_as_p1(
        labels=labels,
        train_episodes=args.train_episodes,
        greedy_episodes=args.greedy_episodes,
        max_rounds=args.max_rounds,
        minimax_depth=args.minimax_depth,
        epsilon_start=args.epsilon_start,
        epsilon_end=args.epsilon_end,
        agent_seed=args.seed,
        random_seed=rs,
    )
    print("Q-learning on-policy strip (P2 seat) …")
    q_p2 = ql_on_policy_strip_as_p2(
        labels=labels,
        train_episodes=args.train_episodes,
        greedy_episodes=args.greedy_episodes,
        max_rounds=args.max_rounds,
        minimax_depth=args.minimax_depth,
        epsilon_start=args.epsilon_start,
        epsilon_end=args.epsilon_end,
        agent_seed=args.seed + 199,
        random_seed=rs,
    )

    plot_benchmark_figure(
        labels=labels,
        mc_p1_cells=mc_p1_cells,
        ql_p1_cells=q_p1,
        ql_p2_cells=q_p2,
        out_path=args.out,
    )
    print(f"Wrote {args.out.resolve()}")


if __name__ == "__main__":
    main()
