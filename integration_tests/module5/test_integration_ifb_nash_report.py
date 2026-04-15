"""Integration Flow B (IFB): simulation -> hypothesis vs final Nash report.

This validates a concrete end-to-end path through Module 4 simulation behavior
and Module 5 normal-form comparison reporting.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Match existing test import setup for `.src`.
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / ".src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nash_normal_form import report_match_hypothesis_vs_final_nash  # noqa: E402
from strategies import AggressiveStrategy, DefensiveStrategy  # noqa: E402


def test_ifb_hypothesis_vs_final_report_contains_expected_sections():
    report = report_match_hypothesis_vs_final_nash(
        AggressiveStrategy("p1"),
        DefensiveStrategy("p2"),
        max_rounds=6,
        include_mixed=False,
    )

    # Integration-level assertions: ensure end-to-end output contract is intact.
    assert "Match recap:" in report
    assert "Hypothesis NE (pre-match normal form)" in report
    assert "Final NE (post-match gamestate" in report
    assert "Payoff matrices identical:" in report
    assert "Pure NE set identical:" in report
    assert "hypothesis pure NE:" in report
    assert "final pure NE:" in report
