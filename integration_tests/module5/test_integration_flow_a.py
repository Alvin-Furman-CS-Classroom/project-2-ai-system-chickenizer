"""Integration Flow A: Module 1 -> Engine/Strategies -> Module 5 analysis.

Goal: prove we can take a KB entailment result, configure strategies from it,
run the engine loop, and compute repeated-play analytics end-to-end.
"""

from __future__ import annotations

import sys
from pathlib import Path

import sympy as sp

# Match unit-test import pattern: add `.src` to path.
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / ".src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from engine import GameEngine  # noqa: E402
from module1_kb import ChickenKB  # noqa: E402
from nash_repeated_analysis import analyze_repeated_play  # noqa: E402
from strategies import (  # noqa: E402
    AlwaysStayStrategy,
    AlwaysSwerveStrategy,
    merge_strategy_preferences,
)


def test_flow_a_kb_entailment_drives_strategy_then_repeated_play_analysis():
    # --- Module 1: KB setup + entailment ---
    kb = ChickenKB()
    p1_stays = sp.Symbol("p1_stays")
    p2_swerves = sp.Symbol("p2_swerves")
    kb.tell([p1_stays, sp.Implies(p1_stays, p2_swerves)])

    ok, conflict = kb.validate_kb()
    assert ok is True
    assert conflict is None
    assert kb.ask(p2_swerves) is True

    # Use KB outputs to *configure* downstream strategies.
    p1 = AlwaysStayStrategy("p1") if kb.ask(p1_stays) else AlwaysSwerveStrategy("p1")
    p2 = AlwaysSwerveStrategy("p2") if kb.ask(p2_swerves) else AlwaysStayStrategy("p2")

    # --- Engine/Strategies: merged state and match run (inside Module 5 analysis) ---
    base = GameEngine().get_gamestate()
    merged = merge_strategy_preferences(base, p1, p2)

    # --- Module 5: repeated-play analysis should be coherent and consistent ---
    r = analyze_repeated_play(p1, p2, merged, max_rounds=4)
    assert r.rounds_played == 4
    assert len(r.records) == 4

    # Deterministic joint action: P1 stay, P2 swerve each round.
    key = (1, 0)  # Stay, Swerve (see ACTION_LABELS semantics)
    assert key in r.joint_cells
    assert r.joint_cells[key].count == 4

    # Conditional aggregates should exist once we have >= 2 rounds.
    assert key in r.conditional_prev_to_next
    assert r.conditional_prev_to_next[key].count == 3
