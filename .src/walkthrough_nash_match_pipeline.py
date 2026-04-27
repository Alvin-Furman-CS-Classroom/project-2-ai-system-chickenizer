#!/usr/bin/env python3
"""Pipeline walkthrough: **normal form → simulate → joint table → resilience outcome**.

This ties four pieces of Chickenizer together for graders or a talk track:

1. **Hypothesis normal form** — One-shot 2×2 payoffs from merged strategy preferences
   (not the dynamic path). Pure / mixed Nash marks what *would* be stable if each
   round were that simultaneous game.

2. **Simulate** — ``GameSimulator`` runs the real **sequential** match (P1 then P2 each
   round). Play can deviate from any one-shot story because strategies react to history,
   HP, etc.

3. **Joint play vs hypothesis** — Count how often each joint (P1 row, P2 col) occurred,
   and compare to ``N × Pr(cell)`` under the hypothesis NE (i.i.d. toy reference; see
   ``hypothesis_joint_distribution`` in ``nash_normal_form``).

4. **Resilience outcome** — Who is ahead on **resilience margin** (P1−P2), same sign
   convention as Q-learning / ``train_ql`` episode labels — not the per-round ``score``
   string tallies.

Run from repo root::

    python .src/walkthrough_nash_match_pipeline.py
    python .src/walkthrough_nash_match_pipeline.py --preset stay-swerve --max-rounds 8 --mixed

This is documentation you can run; it prints ASCII only (no Streamlit).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from engine import GameEngine  # noqa: E402
from nash_normal_form import (  # noqa: E402
    analyze_normal_form,
    empirical_joint_action_counts,
    format_joint_play_vs_hypothesis_ascii,
    format_nash_grid_ascii,
)
from strategies import (  # noqa: E402
    AlwaysStayStrategy,
    AlwaysSwerveStrategy,
    GameSimulator,
    Strategy,
    TitForTatStrategy,
    merge_strategy_preferences,
    resilience_leader_p1_seat,
    resilience_margin_p1_minus_p2,
)

PresetFactory = Callable[[], Tuple[Strategy, Strategy]]


def _preset_swerve_swerve() -> Tuple[Strategy, Strategy]:
    return AlwaysSwerveStrategy("p1"), AlwaysSwerveStrategy("p2")


def _preset_tft_swerve() -> Tuple[Strategy, Strategy]:
    return TitForTatStrategy("p1"), AlwaysSwerveStrategy("p2")


def _preset_stay_swerve() -> Tuple[Strategy, Strategy]:
    return AlwaysStayStrategy("p1"), AlwaysSwerveStrategy("p2")


PRESETS: Dict[str, Tuple[str, PresetFactory]] = {
    "swerve-swerve": ("Both always swerve (symmetric)", _preset_swerve_swerve),
    "tft-swerve": ("Tit-for-tat vs always swerve", _preset_tft_swerve),
    "stay-swerve": ("Always stay vs always swerve", _preset_stay_swerve),
}


def run_walkthrough(
    *,
    preset: str,
    max_rounds: int,
    include_mixed: bool,
    joint_mixed_index: int,
) -> None:
    if preset not in PRESETS:
        raise SystemExit(f"Unknown preset {preset!r}; choose one of: {', '.join(PRESETS)}")
    title, factory = PRESETS[preset]
    p1, p2 = factory()

    eng = GameEngine()
    base = merge_strategy_preferences(eng.get_gamestate(), p1, p2)

    banner = "=" * 72
    print(banner)
    print("Chickenizer pipeline walkthrough (normal form → match → joint → resilience)")
    print(banner)
    print(f"Preset: {preset} — {title}")
    print(f"Max rounds: {max_rounds}  |  mixed NE in grids: {include_mixed}")
    print()

    # --- Step 1: hypothesis normal form ---
    print("STEP 1 — Hypothesis one-shot normal form (merged prefs, start-of-match state)")
    print("-" * 72)
    hypothesis = analyze_normal_form(p1, p2, base, include_mixed=include_mixed)
    print(
        format_nash_grid_ascii(
            hypothesis,
            include_mixed_footer=include_mixed,
        )
    )

    # --- Step 2: simulate ---
    print("STEP 2 — Sequential simulation (engine + strategies)")
    print("-" * 72)
    sim = GameSimulator()
    outcome = sim.simulate(p1, p2, max_rounds=max_rounds, initial_gamestate=base)
    fs = outcome["final_state"]
    summ = outcome.get("summary", {})
    h1 = fs.get("p1_action_history") or []
    print(f"Completed rounds (joint actions recorded): {len(h1)}")
    print(f"Round score tallies — P1: {summ.get('p1_wins')}  P2: {summ.get('p2_wins')}  "
          f"TIE: {summ.get('ties')}  CRASH: {summ.get('crashes')}")
    print(f"Final HP — P1: {fs.get('p1_hp')}  P2: {fs.get('p2_hp')}")
    print()

    # --- Step 3: joint table (same hypothesis object; empirical from match) ---
    print("STEP 3 — Joint play vs hypothesis NE (observed / (N · Pr_cell))")
    print("-" * 72)
    n_r = len(h1)
    if n_r == 0:
        print("(No rounds played; skip joint table.)")
    else:
        counts = empirical_joint_action_counts(fs)
        print(
            format_joint_play_vs_hypothesis_ascii(
                counts,
                hypothesis,
                n_rounds=n_r,
                mixed_index=joint_mixed_index,
            )
        )
    print()

    # --- Step 4: resilience outcome ---
    print("STEP 4 — Resilience outcome (margin-based, same idea as Q-learning episode W/L/T)")
    print("-" * 72)
    m = resilience_margin_p1_minus_p2(fs)
    leader = resilience_leader_p1_seat(fs)
    leader_txt = {
        "p1": "P1 leads on resilience (positive P1−P2 margin)",
        "p2": "P2 leads on resilience (negative P1−P2 margin)",
        "tie": "Tied on resilience",
    }.get(leader, leader)
    print(f"P1 resilience: {fs.get('p1_resilience')}  |  P2 resilience: {fs.get('p2_resilience')}")
    if fs.get("resilience_diff") is not None:
        print(f"resilience_diff (engine): {fs.get('resilience_diff')}")
    print(f"Margin (P1−P2): {m:+.1f}  →  {leader_txt}")
    print()
    print(banner)
    print("Done. For the full hypothesis-vs-final NE ASCII report, run:")
    print("  python .src/nash_hypothesis_vs_final_demo.py --case 1")
    print(banner)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--preset",
        choices=sorted(PRESETS.keys()),
        default="swerve-swerve",
        help="strategy pair to run",
    )
    parser.add_argument("--max-rounds", type=int, default=10, help="max rounds per match")
    parser.add_argument(
        "--mixed",
        action="store_true",
        help="enumerate mixed Nash in the Step 1 grid (slower)",
    )
    parser.add_argument(
        "--mixed-index",
        type=int,
        default=0,
        metavar="K",
        help="which mixed NE to use for Step 3 cell probabilities when several exist",
    )
    args = parser.parse_args(argv)
    run_walkthrough(
        preset=args.preset,
        max_rounds=max(1, int(args.max_rounds)),
        include_mixed=bool(args.mixed),
        joint_mixed_index=max(0, int(args.mixed_index)),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
