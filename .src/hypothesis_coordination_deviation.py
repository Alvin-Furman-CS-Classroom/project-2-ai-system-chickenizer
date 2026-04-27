"""Per-match counts of opponent deviations from a fixed coordination hypothesis.

Illustration-only: does not affect learning. Uses the usual asymmetric-chicken
story in **sequential** play terms:

- **When P1 stays, P2 swerves.**  (P2 ``False`` when P1 ``True``)
- **When P1 swerves, P2 stays.**  (P2 ``True`` when P1 ``False``)

So P2's hypothesized action is ``not p1_stay``. If the **opponent** is P1, the
symmetric convention is P1 hypothesized ``not p2_stay``.

Joint cells follow ``nash_normal_form.ACTION_ORDER``: row index = P1
(0=Swerve, 1=Stay), column index = P2; flat index ``2 * i + j``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Sequence, Tuple

OpponentSeat = Literal["p1", "p2"]


def _action_to_stay(action: str) -> bool:
    if action == "stay":
        return True
    if action == "swerve":
        return False
    raise ValueError(f"Expected 'stay' or 'swerve', got {action!r}")


def joint_cell_index(p1_stay: bool, p2_stay: bool) -> int:
    """Flat index 0..3 for (P1 row, P2 col) with Swerve=0, Stay=1."""
    i = int(p1_stay)
    j = int(p2_stay)
    return 2 * i + j


def joint_cell_labels() -> Tuple[str, str, str, str]:
    """Human labels for indices 0..3 (P1 action first)."""
    return (
        "P1 swerve, P2 swerve",
        "P1 swerve, P2 stay",
        "P1 stay, P2 swerve",
        "P1 stay, P2 stay",
    )


def expected_opponent_stay(
    opponent: OpponentSeat, *, p1_stay: bool, p2_stay: bool
) -> bool:
    """Hypothesized opponent action (``True`` = stay) under coordination convention."""
    if opponent == "p2":
        return not p1_stay
    if opponent == "p1":
        return not p2_stay
    raise ValueError(f"opponent must be 'p1' or 'p2', got {opponent!r}")


def count_opponent_deviations_by_joint_cell(
    p1_actions: Sequence[str],
    p2_actions: Sequence[str],
    opponent: OpponentSeat,
) -> List[int]:
    """Four counts: index = joint outcome; value = rounds where opponent **deviated**.

    A deviation round increments ``counts[joint_cell_index(p1, p2)]`` by 1.
    Rounds where the opponent matched the hypothesis are not counted in any cell.
    """
    if len(p1_actions) != len(p2_actions):
        raise ValueError(
            f"P1/P2 history length mismatch: {len(p1_actions)} vs {len(p2_actions)}"
        )
    counts = [0, 0, 0, 0]
    for a1, a2 in zip(p1_actions, p2_actions):
        s1 = _action_to_stay(a1)
        s2 = _action_to_stay(a2)
        exp = expected_opponent_stay(opponent, p1_stay=s1, p2_stay=s2)
        actual = s2 if opponent == "p2" else s1
        if actual != exp:
            counts[joint_cell_index(s1, s2)] += 1
    return counts


def counts_to_fractions(counts: Sequence[int], *, rounds: int) -> List[float]:
    """Normalize by total rounds (not only deviation rounds)."""
    if rounds <= 0:
        return [0.0, 0.0, 0.0, 0.0]
    return [float(c) / float(rounds) for c in counts]


@dataclass(frozen=True)
class HypothesisDeviationReport:
    """Per-game deviation-from-coordination-hypothesis summary."""

    opponent: OpponentSeat
    rounds: int
    deviation_counts_by_joint_cell: Tuple[int, int, int, int]
    deviation_fractions_by_joint_cell: Tuple[float, float, float, float]
    total_deviation_rounds: int
    hypothesis_description: str = (
        "Asymmetric coordination: if P1 stays then P2 swerves; "
        "if P1 swerves then P2 stays (opponent P2). If opponent is P1, use P1 = not P2."
    )

    def to_dict(self) -> Dict[str, Any]:
        labels = joint_cell_labels()
        cells = [
            {
                "joint_label": labels[k],
                "deviation_count": self.deviation_counts_by_joint_cell[k],
                "deviation_fraction_of_rounds": self.deviation_fractions_by_joint_cell[
                    k
                ],
            }
            for k in range(4)
        ]
        return {
            "opponent": self.opponent,
            "rounds": self.rounds,
            "total_deviation_rounds": self.total_deviation_rounds,
            "hypothesis_description": self.hypothesis_description,
            "cells": cells,
        }


def opponent_seat_for_agent(agent_plays_p1: bool) -> OpponentSeat:
    return "p2" if agent_plays_p1 else "p1"


def hypothesis_deviation_report_from_final_state(
    final_state: Dict[str, Any],
    *,
    agent_plays_p1: bool,
) -> HypothesisDeviationReport:
    """Build a report from a post-match ``final_state`` (action histories)."""
    h1 = final_state.get("p1_action_history") or []
    h2 = final_state.get("p2_action_history") or []
    if not isinstance(h1, list) or not isinstance(h2, list):
        raise TypeError("final_state must contain list action histories")
    opp = opponent_seat_for_agent(agent_plays_p1)
    counts = count_opponent_deviations_by_joint_cell(h1, h2, opp)
    rounds = len(h1)
    fr = counts_to_fractions(counts, rounds=rounds)
    total = sum(counts)
    dc = (int(counts[0]), int(counts[1]), int(counts[2]), int(counts[3]))
    df = (float(fr[0]), float(fr[1]), float(fr[2]), float(fr[3]))
    return HypothesisDeviationReport(
        opponent=opp,
        rounds=rounds,
        deviation_counts_by_joint_cell=dc,
        deviation_fractions_by_joint_cell=df,
        total_deviation_rounds=total,
    )


def hypothesis_deviation_report_from_simulate_result(
    simulate_result: Dict[str, Any],
    *,
    agent_plays_p1: bool,
) -> HypothesisDeviationReport:
    """Convenience: use ``result['final_state']`` from ``GameSimulator.simulate``."""
    fs = simulate_result.get("final_state")
    if not isinstance(fs, dict):
        raise TypeError("simulate_result must contain a dict final_state")
    return hypothesis_deviation_report_from_final_state(
        fs, agent_plays_p1=agent_plays_p1
    )
