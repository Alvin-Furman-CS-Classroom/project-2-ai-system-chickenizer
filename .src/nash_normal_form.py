"""One-shot normal-form Nash analysis for Chickenizer.

For each pair of actions (swerve/stay × swerve/stay), simulates one counterfactual
round via ``GameEngine`` and records resilience payoffs. Utilities come from
``merge_strategy_preferences``; ``Strategy`` objects supply ``implied_preferences``
and names — Nash is defined on this induced matrix, not on full dynamic play.

Pure Nash: best-response enumeration. Mixed Nash: ``nashpy`` (lazy-imported).
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from .engine import GameEngine
    from .strategies import Strategy, merge_strategy_preferences
except ImportError:
    from engine import GameEngine  # type: ignore
    from strategies import Strategy, merge_strategy_preferences  # type: ignore

ACTION_ORDER: Tuple[bool, bool] = (False, True)
ACTION_LABELS: Tuple[str, str] = ("Swerve", "Stay")


def _reset_for_one_shot(state: Dict[str, Any]) -> Dict[str, Any]:
    s = deepcopy(state)
    s["p1_stay"] = False
    s["p2_stay"] = False
    s["round"] = 0
    s["p1_action_history"] = []
    s["p2_action_history"] = []
    s["score"] = []
    s["p1_resilience"] = 0
    s["p2_resilience"] = 0
    s["resilience_diff"] = 0
    return s


def _one_shot_payoffs(
    merged_state: Dict[str, Any], p1_action: bool, p2_action: bool
) -> Tuple[int, int]:
    template = _reset_for_one_shot(merged_state)
    engine = GameEngine(gamestate=template)
    engine.play_action("p1", p1_action)
    engine.play_action("p2", p2_action)
    engine.generate_gamestate(increment_round=True)
    gs = engine.gamestate
    return int(gs["p1_resilience"]), int(gs["p2_resilience"])


def build_payoff_matrices(
    p1_strategy: Strategy,
    p2_strategy: Strategy,
    initial_gamestate: Optional[Dict[str, Any]] = None,
) -> Tuple[List[List[int]], List[List[int]]]:
    """Return (payoff_p1, payoff_p2) as 2×2 lists; [i][j] = P1 action i, P2 action j."""
    if p1_strategy.player != "p1":
        raise ValueError(f"p1_strategy must have player='p1', got {p1_strategy.player!r}")
    if p2_strategy.player != "p2":
        raise ValueError(f"p2_strategy must have player='p2', got {p2_strategy.player!r}")

    if initial_gamestate is None:
        base = GameEngine().get_gamestate()
    else:
        base = deepcopy(initial_gamestate)

    merged = merge_strategy_preferences(base, p1_strategy, p2_strategy)

    payoff_p1: List[List[int]] = []
    payoff_p2: List[List[int]] = []
    for a1 in ACTION_ORDER:
        row_p1: List[int] = []
        row_p2: List[int] = []
        for a2 in ACTION_ORDER:
            u1, u2 = _one_shot_payoffs(merged, a1, a2)
            row_p1.append(u1)
            row_p2.append(u2)
        payoff_p1.append(row_p1)
        payoff_p2.append(row_p2)

    return payoff_p1, payoff_p2


def find_pure_nash(
    payoff_p1: Sequence[Sequence[int]],
    payoff_p2: Sequence[Sequence[int]],
) -> List[Tuple[int, int]]:
    """Indices (i, j) that are pure-strategy Nash equilibria."""
    br_p1: Dict[int, List[int]] = {}
    for j in range(2):
        col = [payoff_p1[i][j] for i in range(2)]
        best = max(col)
        br_p1[j] = [i for i in range(2) if payoff_p1[i][j] == best]

    br_p2: Dict[int, List[int]] = {}
    for i in range(2):
        row = [payoff_p2[i][j] for j in range(2)]
        best = max(row)
        br_p2[i] = [j for j in range(2) if payoff_p2[i][j] == best]

    out: List[Tuple[int, int]] = []
    for i in range(2):
        for j in range(2):
            if i in br_p1[j] and j in br_p2[i]:
                out.append((i, j))
    return out


def find_mixed_nash(
    payoff_p1: Sequence[Sequence[int]],
    payoff_p2: Sequence[Sequence[int]],
) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """Mixed Nash equilibria via support enumeration (sigma for P1, rho for P2)."""
    import numpy as np
    import nashpy as nash

    a = np.array(payoff_p1, dtype=float)
    b = np.array(payoff_p2, dtype=float)
    game = nash.Game(a, b)
    seen: set[Tuple[Tuple[float, float], Tuple[float, float]]] = set()
    result: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    for sigma, rho in game.support_enumeration():
        sig_t = tuple(round(float(x), 6) for x in sigma)
        rho_t = tuple(round(float(y), 6) for y in rho)
        key = (sig_t, rho_t)
        if key not in seen:
            seen.add(key)
            result.append((sig_t, rho_t))
    return result


@dataclass
class NormalFormResult:
    payoff_p1: List[List[int]]
    payoff_p2: List[List[int]]
    p1_strategy_name: str
    p2_strategy_name: str
    action_labels: Tuple[str, str] = ACTION_LABELS
    pure_nash_indices: List[Tuple[int, int]] = field(default_factory=list)
    mixed_equilibria: List[Tuple[Tuple[float, float], Tuple[float, float]]] = field(
        default_factory=list
    )


def analyze_normal_form(
    p1_strategy: Strategy,
    p2_strategy: Strategy,
    initial_gamestate: Optional[Dict[str, Any]] = None,
    *,
    include_mixed: bool = True,
) -> NormalFormResult:
    """Build payoffs and compute pure (and optionally mixed) Nash equilibria."""
    p1_m, p2_m = build_payoff_matrices(p1_strategy, p2_strategy, initial_gamestate)
    pure = find_pure_nash(p1_m, p2_m)
    mixed: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    if include_mixed:
        mixed = find_mixed_nash(p1_m, p2_m)
    return NormalFormResult(
        payoff_p1=p1_m,
        payoff_p2=p2_m,
        p1_strategy_name=p1_strategy.__class__.__name__,
        p2_strategy_name=p2_strategy.__class__.__name__,
        pure_nash_indices=pure,
        mixed_equilibria=mixed,
    )


def format_nash_table(result: NormalFormResult) -> str:
    """ASCII table with pure Nash cells marked."""
    lbl = result.action_labels
    lines: List[str] = []
    ne_set = set(result.pure_nash_indices)

    lines.append("One-shot normal form (resilience payoffs after one round)")
    lines.append(f"P1: {result.p1_strategy_name}  |  P2: {result.p2_strategy_name}")
    lines.append("")
    lines.append(
        f"{'':>12}  P2:{lbl[0]:>7}     P2:{lbl[1]:>7}\n"
        f"{'(P1 row, P2 col)':>12}  {'(u1,u2)':^17}  {'(u1,u2)':^17}"
    )
    lines.append("-" * 56)

    for i, row_label in enumerate(lbl):
        parts: List[str] = []
        for j in range(2):
            u1 = result.payoff_p1[i][j]
            u2 = result.payoff_p2[i][j]
            cell = f"({u1},{u2})"
            if (i, j) in ne_set:
                cell += " NE"
            parts.append(f"{cell:^17}")
        lines.append(f"P1:{row_label:>7}   {parts[0]}  {parts[1]}")

    lines.append("")
    if result.pure_nash_indices:
        ne_str = ", ".join(str(x) for x in result.pure_nash_indices)
        lines.append(f"Pure Nash (row_i, col_j): {ne_str}")
    else:
        lines.append("Pure Nash: none")

    if result.mixed_equilibria:
        lines.append("Mixed Nash (P1 probs swerve/stay, P2 probs swerve/stay):")
        for sig, rho in result.mixed_equilibria:
            lines.append(f"  σ={sig}  ρ={rho}")
    else:
        lines.append("Mixed Nash: none found (or skipped)")

    return "\n".join(lines)


if __name__ == "__main__":
    try:
        from .strategies import AlwaysStayStrategy, AlwaysSwerveStrategy
    except ImportError:
        from strategies import AlwaysStayStrategy, AlwaysSwerveStrategy  # type: ignore

    r = analyze_normal_form(
        AlwaysStayStrategy("p1"),
        AlwaysSwerveStrategy("p2"),
        include_mixed=True,
    )
    print(format_nash_table(r))
