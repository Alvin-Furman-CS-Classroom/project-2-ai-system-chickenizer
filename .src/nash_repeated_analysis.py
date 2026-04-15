"""N-round and full-match analysis for fixed strategy pairs (Chickenizer).

This is **not** a Nash equilibrium of the finite repeated game in the formal
game-theory sense (that would require modeling the full strategy space of the
repeated game or subgame-perfect equilibria). Instead, it **simulates** the
engine with two concrete ``Strategy`` instances and summarizes outcomes:

* **Composite / aggregate** — per-round resilience deltas, cumulative series,
  joint-action frequencies, and mean deltas per (P1 action, P2 action) cell.
* **Conditional (Markov-style)** — for rounds after the first, groups the
  *next* round’s resilience deltas by the **previous** round’s joint action pair.
  This is the empirical analogue of
  ``E[Δreward_t | a1_{t-1}, a2_{t-1}]`` and is easy to align with tabular
  (state, action) views such as Q-learning.

For a **one-shot** normal form and classical Nash on the induced 2×2 matrix,
see ``nash_normal_form``.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, DefaultDict, Dict, List, Optional, Sequence, Tuple

try:
    from .engine import GameEngine
    from .nash_normal_form import ACTION_LABELS
    from .strategies import Strategy, merge_strategy_preferences
except ImportError:
    from engine import GameEngine  # type: ignore
    from nash_normal_form import ACTION_LABELS  # type: ignore
    from strategies import Strategy, merge_strategy_preferences  # type: ignore


def _idx_stay(stay: bool) -> int:
    """0 = Swerve, 1 = Stay (matches ``ACTION_ORDER`` in ``nash_normal_form``)."""
    return 1 if stay else 0


@dataclass
class RepeatedRoundRecord:
    """One completed round in a simulated match."""

    round_number: int
    p1_stay: bool
    p2_stay: bool
    p1_action: str
    p2_action: str
    outcome: Optional[str]
    delta_p1_resilience: int
    delta_p2_resilience: int
    cum_p1_resilience: int
    cum_p2_resilience: int


@dataclass
class JointCellAggregate:
    """Counts and mean per-round resilience deltas for one joint action cell."""

    count: int = 0
    sum_delta_p1: int = 0
    sum_delta_p2: int = 0

    @property
    def mean_delta_p1(self) -> float:
        if self.count == 0:
            return 0.0
        return self.sum_delta_p1 / self.count

    @property
    def mean_delta_p2(self) -> float:
        if self.count == 0:
            return 0.0
        return self.sum_delta_p2 / self.count


@dataclass
class ConditionalAggregate:
    """Mean next-round deltas given the *previous* round’s joint action."""

    count: int = 0
    sum_delta_p1: int = 0
    sum_delta_p2: int = 0

    @property
    def mean_delta_p1(self) -> float:
        if self.count == 0:
            return 0.0
        return self.sum_delta_p1 / self.count

    @property
    def mean_delta_p2(self) -> float:
        if self.count == 0:
            return 0.0
        return self.sum_delta_p2 / self.count


@dataclass
class RepeatedPlayResult:
    """Outcome of simulating a fixed strategy pair for up to ``max_rounds`` rounds."""

    p1_strategy_name: str
    p2_strategy_name: str
    max_rounds: int
    rounds_played: int
    match_end_reason: str
    records: List[RepeatedRoundRecord] = field(default_factory=list)
    joint_cells: Dict[Tuple[int, int], JointCellAggregate] = field(default_factory=dict)
    conditional_prev_to_next: Dict[Tuple[int, int], ConditionalAggregate] = field(
        default_factory=dict
    )

    def cumulative_chart_rows(self) -> List[Dict[str, Any]]:
        """Rows for ``st.line_chart`` / dataframe: round vs cumulative resilience."""
        rows: List[Dict[str, Any]] = []
        for r in self.records:
            rows.append(
                {
                    "round": r.round_number,
                    "p1_cum_resilience": r.cum_p1_resilience,
                    "p2_cum_resilience": r.cum_p2_resilience,
                }
            )
        return rows

    def per_round_delta_rows(self) -> List[Dict[str, Any]]:
        """Per-round incremental resilience (for trend of *per-round* payoff)."""
        rows: List[Dict[str, Any]] = []
        for r in self.records:
            rows.append(
                {
                    "round": r.round_number,
                    "delta_p1": r.delta_p1_resilience,
                    "delta_p2": r.delta_p2_resilience,
                }
            )
        return rows

    def joint_matrix_rows(self) -> List[Dict[str, Any]]:
        """Human-readable 2×2 summary: count and mean deltas per joint action."""
        lab = list(ACTION_LABELS)
        out: List[Dict[str, Any]] = []
        for i, a1 in enumerate(lab):
            row: Dict[str, Any] = {"P1 \\ P2": f"P1 · {a1}"}
            for j, a2 in enumerate(lab):
                cell = self.joint_cells.get((i, j))
                if cell is None or cell.count == 0:
                    row[f"P2 · {a2}"] = "—"
                else:
                    row[f"P2 · {a2}"] = (
                        f"n={cell.count}, "
                        f"mean ΔR1={cell.mean_delta_p1:.2f}, "
                        f"mean ΔR2={cell.mean_delta_p2:.2f}"
                    )
            out.append(row)
        return out

    def conditional_rows(self) -> List[Dict[str, Any]]:
        """Previous joint (row,col) → mean next-round ΔR1, ΔR2."""
        lab = list(ACTION_LABELS)
        rows: List[Dict[str, Any]] = []
        for (pi, pj), agg in sorted(self.conditional_prev_to_next.items()):
            prev_label = f"P1 {lab[pi]} / P2 {lab[pj]}"
            rows.append(
                {
                    "previous (P1, P2)": prev_label,
                    "n_next": agg.count,
                    "mean next ΔR1": round(agg.mean_delta_p1, 4),
                    "mean next ΔR2": round(agg.mean_delta_p2, 4),
                }
            )
        return rows


def _history_to_records(history: Sequence[Dict[str, Any]]) -> List[RepeatedRoundRecord]:
    """Build per-round records from ``GameEngine.run_game`` history snapshots.

    The engine appends **multiple** snapshots per round (pre-action, post-p1,
    post-p2, post-round). A round completes only when ``score`` gains an entry;
    we pair that step with the immediately previous snapshot so resilience
    deltas match the round resolution.
    """
    if len(history) < 2:
        return []

    records: List[RepeatedRoundRecord] = []
    for k in range(1, len(history)):
        prev = history[k - 1]
        cur = history[k]
        p_sc = len(prev.get("score") or [])
        c_sc = len(cur.get("score") or [])
        if c_sc <= p_sc:
            continue

        d1 = int(cur["p1_resilience"]) - int(prev["p1_resilience"])
        d2 = int(cur["p2_resilience"]) - int(prev["p2_resilience"])

        p1_hist = cur.get("p1_action_history") or []
        p2_hist = cur.get("p2_action_history") or []
        if not p1_hist or not p2_hist:
            continue
        a1s = p1_hist[-1]
        a2s = p2_hist[-1]
        p1_stay = a1s == "stay"
        p2_stay = a2s == "stay"

        score = cur.get("score") or []
        outcome = score[-1] if score else None
        rnd = int(cur.get("round", 0))

        records.append(
            RepeatedRoundRecord(
                round_number=rnd,
                p1_stay=p1_stay,
                p2_stay=p2_stay,
                p1_action=a1s,
                p2_action=a2s,
                outcome=outcome if isinstance(outcome, str) else None,
                delta_p1_resilience=d1,
                delta_p2_resilience=d2,
                cum_p1_resilience=int(cur["p1_resilience"]),
                cum_p2_resilience=int(cur["p2_resilience"]),
            )
        )
    return records


def _aggregate_joint(records: Sequence[RepeatedRoundRecord]) -> Dict[Tuple[int, int], JointCellAggregate]:
    joint: Dict[Tuple[int, int], JointCellAggregate] = {}
    for r in records:
        key = (_idx_stay(r.p1_stay), _idx_stay(r.p2_stay))
        if key not in joint:
            joint[key] = JointCellAggregate()
        c = joint[key]
        c.count += 1
        c.sum_delta_p1 += r.delta_p1_resilience
        c.sum_delta_p2 += r.delta_p2_resilience
    return joint


def _aggregate_conditional(
    records: Sequence[RepeatedRoundRecord],
) -> Dict[Tuple[int, int], ConditionalAggregate]:
    """Group *next-round* deltas by *previous* round’s joint action indices."""
    cond: DefaultDict[Tuple[int, int], ConditionalAggregate] = defaultdict(ConditionalAggregate)
    for i in range(1, len(records)):
        prev = records[i - 1]
        cur = records[i]
        key = (_idx_stay(prev.p1_stay), _idx_stay(prev.p2_stay))
        a = cond[key]
        a.count += 1
        a.sum_delta_p1 += cur.delta_p1_resilience
        a.sum_delta_p2 += cur.delta_p2_resilience
    return dict(cond)


def analyze_repeated_play(
    p1_strategy: Strategy,
    p2_strategy: Strategy,
    initial_gamestate: Optional[Dict[str, Any]] = None,
    *,
    max_rounds: int = 10,
) -> RepeatedPlayResult:
    """Simulate a full match and return composite + conditional statistics.

    Args:
        p1_strategy: Strategy for player 1 (``player`` must be ``\"p1\"``).
        p2_strategy: Strategy for player 2 (``player`` must be ``\"p2\"``).
        initial_gamestate: Merged gamestate (e.g. preferences already applied). If
            ``None``, uses ``GameEngine`` defaults then merges strategy preferences.
        max_rounds: Upper bound on rounds (same semantics as ``GameEngine.run_game``).

    Returns:
        ``RepeatedPlayResult`` with per-round records, joint-cell aggregates, and
        conditional next-round means given previous joint actions.
    """
    if p1_strategy.player != "p1":
        raise ValueError(f"p1_strategy must have player='p1', got {p1_strategy.player!r}")
    if p2_strategy.player != "p2":
        raise ValueError(f"p2_strategy must have player='p2', got {p2_strategy.player!r}")

    if initial_gamestate is None:
        base = GameEngine().get_gamestate()
    else:
        base = deepcopy(initial_gamestate)

    merged = merge_strategy_preferences(base, p1_strategy, p2_strategy)
    engine = GameEngine(gamestate=merged)
    history = engine.run_game(
        max_rounds,
        p1_strategy,
        p2_strategy,
        initial_gamestate=engine.get_gamestate(),
    )

    records = _history_to_records(history)
    joint = _aggregate_joint(records)
    cond = _aggregate_conditional(records)
    gs = engine.get_gamestate()
    reason = str(gs.get("match_end_reason") or "")

    return RepeatedPlayResult(
        p1_strategy_name=p1_strategy.__class__.__name__,
        p2_strategy_name=p2_strategy.__class__.__name__,
        max_rounds=max_rounds,
        rounds_played=len(records),
        match_end_reason=reason,
        records=records,
        joint_cells=joint,
        conditional_prev_to_next=cond,
    )


def repeated_play_to_dict(result: RepeatedPlayResult) -> Dict[str, Any]:
    """JSON-friendly snapshot (e.g. for APIs or notebooks)."""
    joint_means: Dict[str, Any] = {}
    for i in range(2):
        for j in range(2):
            c = result.joint_cells.get((i, j)) or JointCellAggregate()
            joint_means[f"{ACTION_LABELS[i]}_{ACTION_LABELS[j]}"] = {
                "count": c.count,
                "mean_delta_p1": c.mean_delta_p1,
                "mean_delta_p2": c.mean_delta_p2,
            }
    return {
        "p1_strategy_name": result.p1_strategy_name,
        "p2_strategy_name": result.p2_strategy_name,
        "max_rounds": result.max_rounds,
        "rounds_played": result.rounds_played,
        "match_end_reason": result.match_end_reason,
        "rounds": [
            {
                "round": r.round_number,
                "p1_action": r.p1_action,
                "p2_action": r.p2_action,
                "outcome": r.outcome,
                "delta_p1_resilience": r.delta_p1_resilience,
                "delta_p2_resilience": r.delta_p2_resilience,
                "cum_p1_resilience": r.cum_p1_resilience,
                "cum_p2_resilience": r.cum_p2_resilience,
            }
            for r in result.records
        ],
        "joint_action_means": joint_means,
        "conditional_prev_joint_to_next_delta": {
            f"prev_{ACTION_LABELS[pi]}_{ACTION_LABELS[pj]}": {
                "count": agg.count,
                "mean_next_delta_p1": agg.mean_delta_p1,
                "mean_next_delta_p2": agg.mean_delta_p2,
            }
            for (pi, pj), agg in result.conditional_prev_to_next.items()
        },
    }
