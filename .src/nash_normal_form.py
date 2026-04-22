"""One-shot normal-form Nash analysis for Chickenizer.

For each pair of actions (swerve/stay × swerve/stay), simulates one counterfactual
round via ``GameEngine`` and records resilience payoffs. Utilities come from ``merge_strategy_preferences`` (engine defaults + each strategy’s
``implied_preferences``). In the UI, **cares** sliders are merged **on top** by key so
user weights override; those ``p1_preferences`` / ``p2_preferences`` drive resilience
in each counterfactual round. One-shot cells use **current** resilience in ``state`` as
the baseline (not reset to zero), so entries are **post-round cumulative** resilience.
Nash is defined on this induced matrix, not on full dynamic play.

Pure Nash: best-response enumeration. Mixed Nash: ``nashpy`` (lazy-imported).
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import warnings
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, cast

try:
    from .engine import GameEngine
    from .strategies import (
        Strategy,
        merge_strategy_preferences,
        resilience_leader_p1_seat,
        resilience_margin_p1_minus_p2,
    )
except ImportError:
    from engine import GameEngine  # type: ignore
    from strategies import (  # type: ignore
        Strategy,
        merge_strategy_preferences,
        resilience_leader_p1_seat,
        resilience_margin_p1_minus_p2,
    )

ACTION_ORDER: Tuple[bool, bool] = (False, True)
ACTION_LABELS: Tuple[str, str] = ("Swerve", "Stay")


def _reset_for_one_shot(state: Dict[str, Any]) -> Dict[str, Any]:
    """Isolate one counterfactual round without wiping resilience.

    We clear round/history/score so the hypothetical is a single joint move, but we
    **keep** ``p1_resilience``, ``p2_resilience``, ``p1_reputation``, and ``p2_reputation``
    from ``state``. Each matrix cell
    is then **final resilience after that counterfactual round** from the current
    baseline (so values move with the match and coloring stays meaningful). Pure
    Nash indices are unchanged vs a zero baseline (payoffs are an additive shift).
    """
    s = deepcopy(state)
    s["p1_stay"] = False
    s["p2_stay"] = False
    s["round"] = 0
    s["p1_action_history"] = []
    s["p2_action_history"] = []
    s["score"] = []
    p1r = int(s.get("p1_resilience", 0))
    p2r = int(s.get("p2_resilience", 0))
    s["p1_resilience"] = p1r
    s["p2_resilience"] = p2r
    s["resilience_diff"] = p1r - p2r
    s["p1_reputation"] = int(s.get("p1_reputation", 0))
    s["p2_reputation"] = int(s.get("p2_reputation", 0))
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


def build_payoff_matrices_at_merged_state(
    merged_gamestate: Dict[str, Any],
) -> Tuple[List[List[int]], List[List[int]]]:
    """Build 2×2 resilience payoffs from an **already merged** gamestate.

    Use this when preferences already include ``merge_strategy_preferences`` and
    user ``p1_preferences`` / ``p2_preferences`` — calling ``build_payoff_matrices``
    again would double-apply implied strategy preferences.
    """
    base = deepcopy(merged_gamestate)
    payoff_p1: List[List[int]] = []
    payoff_p2: List[List[int]] = []
    for a1 in ACTION_ORDER:
        row_p1: List[int] = []
        row_p2: List[int] = []
        for a2 in ACTION_ORDER:
            u1, u2 = _one_shot_payoffs(base, a1, a2)
            row_p1.append(u1)
            row_p2.append(u2)
        payoff_p1.append(row_p1)
        payoff_p2.append(row_p2)
    return payoff_p1, payoff_p2


@dataclass
class RoundNormalFormSnapshot:
    """One-shot 2×2 normal form evaluated at the **start** of a round."""

    round_index: int
    payoff_p1: List[List[int]]
    payoff_p2: List[List[int]]
    pure_nash_indices: List[Tuple[int, int]]
    baseline_p1_resilience: int = 0
    baseline_p2_resilience: int = 0


def collect_per_round_normal_forms(
    p1_strategy: Strategy,
    p2_strategy: Strategy,
    merged_initial: Dict[str, Any],
    max_rounds: int,
) -> List[RoundNormalFormSnapshot]:
    """For each round (until cap or game over), capture the induced 2×2 matrix at round **start**.

    The match advances with the same turn order as ``GameEngine.run_game``: P1 acts,
    then P2, then the round resolves. Before any action in round *k*, we snapshot
    ``build_payoff_matrices_at_merged_state`` so HP / state carry across rounds.
    """
    if p1_strategy.player != "p1":
        raise ValueError(f"p1_strategy must have player='p1', got {p1_strategy.player!r}")
    if p2_strategy.player != "p2":
        raise ValueError(f"p2_strategy must have player='p2', got {p2_strategy.player!r}")

    engine = GameEngine(gamestate=deepcopy(merged_initial))
    out: List[RoundNormalFormSnapshot] = []
    cap = max(1, int(max_rounds))

    for k in range(1, cap + 1):
        is_over, _reason = engine.is_game_over()
        if is_over:
            break

        gs = engine.get_gamestate()
        br1 = int(gs.get("p1_resilience", 0))
        br2 = int(gs.get("p2_resilience", 0))
        p1_m, p2_m = build_payoff_matrices_at_merged_state(gs)
        pure = find_pure_nash(p1_m, p2_m)
        out.append(
            RoundNormalFormSnapshot(
                round_index=k,
                payoff_p1=p1_m,
                payoff_p2=p2_m,
                pure_nash_indices=pure,
                baseline_p1_resilience=br1,
                baseline_p2_resilience=br2,
            )
        )

        current = engine.generate_gamestate(increment_round=False)
        p1_action = p1_strategy(current)
        engine.play_action("p1", p1_action)
        current = engine.generate_gamestate(increment_round=False)
        p2_action = p2_strategy(current)
        engine.play_action("p2", p2_action)
        engine.generate_gamestate(increment_round=True)

    return out


def best_response_correspondences(
    payoff_p1: Sequence[Sequence[int]],
    payoff_p2: Sequence[Sequence[int]],
) -> Dict[str, Any]:
    """Pure best-response sets for the 2×2 normal form.

    Row index i and column index j follow ``ACTION_ORDER`` / ``ACTION_LABELS``
    (0 = Swerve, 1 = Stay for each player).

    Returns:
        ``p1_best_rows_given_p2_col``: for each P2 column j, list of P1 row indices
        that maximize P1's payoff in that column.
        ``p2_best_cols_given_p1_row``: for each P1 row i, list of P2 column indices
        that maximize P2's payoff in that row.
    """
    br_p1_by_col: List[List[int]] = []
    for j in range(2):
        col = [payoff_p1[i][j] for i in range(2)]
        best = max(col)
        br_p1_by_col.append([i for i in range(2) if payoff_p1[i][j] == best])

    br_p2_by_row: List[List[int]] = []
    for i in range(2):
        row = [payoff_p2[i][j] for j in range(2)]
        best = max(row)
        br_p2_by_row.append([j for j in range(2) if payoff_p2[i][j] == best])

    return {
        "p1_best_rows_given_p2_col": br_p1_by_col,
        "p2_best_cols_given_p1_row": br_p2_by_row,
    }


def find_pure_nash(
    payoff_p1: Sequence[Sequence[int]],
    payoff_p2: Sequence[Sequence[int]],
) -> List[Tuple[int, int]]:
    """Indices (i, j) that are pure-strategy Nash equilibria."""
    br = best_response_correspondences(payoff_p1, payoff_p2)
    p1_br = br["p1_best_rows_given_p2_col"]
    p2_br = br["p2_best_cols_given_p1_row"]
    out: List[Tuple[int, int]] = []
    for i in range(2):
        for j in range(2):
            if i in p1_br[j] and j in p2_br[i]:
                out.append((i, j))
    return out


def _mixed_probs_to_pair(vec: Any) -> Tuple[float, float]:
    """Normalize nashpy / numpy strategy vector to (p_swerve, p_stay) with length 2."""
    import numpy as np

    arr = np.asarray(vec, dtype=float).reshape(-1)
    if arr.size != 2:
        raise ValueError(f"expected 2-action support; got size {arr.size}")
    return (round(float(arr[0]), 6), round(float(arr[1]), 6))


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
    # nashpy stubs are incomplete; cast so unpack + ndarray handling type-check.
    # Degenerate 2×2 games can emit RuntimeWarning (even # of equilibria); safe to ignore here.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r".*equilibria was returned.*",
            category=RuntimeWarning,
            module=r"nashpy\.algorithms\.support_enumeration",
        )
        equilibria = cast(Iterable[Tuple[Any, Any]], game.support_enumeration())
    for sigma, rho in equilibria:
        sig_t = _mixed_probs_to_pair(sigma)
        rho_t = _mixed_probs_to_pair(rho)
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


def _joint_flat_index_from_row_col(i: int, j: int) -> int:
    """Row i / col j follow ``ACTION_ORDER`` (0=Swerve, 1=Stay)."""
    return 2 * int(i) + int(j)


def empirical_joint_action_counts(
    final_state: Dict[str, Any],
) -> Tuple[int, int, int, int]:
    """Count joint (P1 row, P2 col) over completed rounds; order matches payoff matrix."""
    h1 = final_state.get("p1_action_history") or []
    h2 = final_state.get("p2_action_history") or []
    if len(h1) != len(h2):
        raise ValueError(
            f"P1/P2 history length mismatch: {len(h1)} vs {len(h2)}"
        )
    counts = [0, 0, 0, 0]
    for a1, a2 in zip(h1, h2):
        if a1 not in ("stay", "swerve") or a2 not in ("stay", "swerve"):
            raise ValueError(f"invalid action strings: {a1!r}, {a2!r}")
        i = 1 if a1 == "stay" else 0
        j = 1 if a2 == "stay" else 0
        counts[_joint_flat_index_from_row_col(i, j)] += 1
    return (int(counts[0]), int(counts[1]), int(counts[2]), int(counts[3]))


def hypothesis_joint_distribution(
    hypothesis: NormalFormResult,
    *,
    mixed_index: int = 0,
) -> Tuple[float, float, float, float]:
    """Per-cell probabilities Pr(P1 row, P2 col) under a **hypothesis** NE (i.i.d. per round).

    - If ``mixed_equilibria`` is non-empty: independent mixing from
      ``mixed_equilibria[mixed_index]`` (σ over P1 rows, ρ over P2 cols).
    - Else if ``pure_nash_indices`` is non-empty: **uniform** mixture over those
      pure cells (each equilibrium cell gets equal total mass).
    - Else: uniform ``1/4`` on all cells.

    For pure-only hypotheses, cells off all pure supports have **zero** expected
    mass; use ``joint_play_ratio_strings`` for display rules.
    """
    if hypothesis.mixed_equilibria:
        idx = max(0, min(mixed_index, len(hypothesis.mixed_equilibria) - 1))
        sig, rho = hypothesis.mixed_equilibria[idx]
        flat: List[float] = []
        for i in range(2):
            for j in range(2):
                flat.append(float(sig[i]) * float(rho[j]))
        return (flat[0], flat[1], flat[2], flat[3])
    if hypothesis.pure_nash_indices:
        n = len(hypothesis.pure_nash_indices)
        pt = [0.0, 0.0, 0.0, 0.0]
        for (i, j) in hypothesis.pure_nash_indices:
            k = _joint_flat_index_from_row_col(int(i), int(j))
            pt[k] += 1.0 / float(n)
        return (pt[0], pt[1], pt[2], pt[3])
    return (0.25, 0.25, 0.25, 0.25)


def hypothesis_joint_distribution_for_joint_display(
    hypothesis: NormalFormResult,
    *,
    mixed_index: int = 0,
) -> Tuple[float, float, float, float]:
    """Baseline joint probabilities for **Play vs expected** UI and ASCII joint tables.

    When **pure** Nash equilibria exist, use a **uniform mixture over those pure cells**
    (standard ``(1/n)`` on each equilibrium outcome). This matches common chicken intuition:
    the two asymmetric equilibria each get equal expected weight, mutual swerve / mutual stay
    are off-support unless they are themselves pure NE.

    When there are **no** pure equilibria, fall back to :func:`hypothesis_joint_distribution`
    (mixed selection, or uniform ``1/4``).
    """
    if hypothesis.pure_nash_indices:
        n = len(hypothesis.pure_nash_indices)
        pt = [0.0, 0.0, 0.0, 0.0]
        for (i, j) in hypothesis.pure_nash_indices:
            k = _joint_flat_index_from_row_col(int(i), int(j))
            pt[k] += 1.0 / float(n)
        return (pt[0], pt[1], pt[2], pt[3])
    return hypothesis_joint_distribution(hypothesis, mixed_index=mixed_index)


def joint_play_ratio_strings(
    counts: Sequence[int],
    expected_probs: Sequence[float],
    *,
    n_rounds: int,
) -> Tuple[str, str, str, str]:
    """Text ratio ``observed / (N · p_cell)`` for each flat joint index."""
    out: List[str] = []
    for k in range(4):
        obs = int(counts[k])
        exp_n = float(n_rounds) * float(expected_probs[k])
        if exp_n <= 1e-12:
            out.append("—" if obs == 0 else ">∞")
        else:
            out.append(f"{obs / exp_n:.2f}")
    return (out[0], out[1], out[2], out[3])


def format_joint_play_vs_hypothesis_ascii(
    counts: Sequence[int],
    hypothesis: NormalFormResult,
    *,
    n_rounds: int,
    mixed_index: int = 0,
) -> str:
    """2×2 ASCII table: observed / expected frequency under hypothesis NE (i.i.d. per round)."""
    probs = hypothesis_joint_distribution_for_joint_display(hypothesis, mixed_index=mixed_index)
    ratios = joint_play_ratio_strings(counts, probs, n_rounds=n_rounds)
    exp_counts = [float(n_rounds) * float(p) for p in probs]
    lbl = hypothesis.action_labels
    if hypothesis.pure_nash_indices:
        hyp_src = f"uniform over {len(hypothesis.pure_nash_indices)} pure NE cell(s)"
    elif hypothesis.mixed_equilibria:
        hyp_src = f"mixed[{mixed_index}]"
    else:
        hyp_src = "uniform 1/4"
    w = max(6, max(len(r) for r in ratios) + 2)
    lines = [
        "=" * 62,
        "Joint play vs hypothesis NE (each cell: observed / (N · Pr_cell under NE))",
        f"  N = {n_rounds} completed rounds  |  hypothesis source: {hyp_src}",
        f"  counts (Sw+Sw / Sw+St / St+Sw / St+St) = {tuple(counts)}",
        f"  N·p expected counts ≈ {[round(x, 3) for x in exp_counts]}",
        "",
        f"{'':>10}  {'P2 ' + lbl[0]:<{w}}  {'P2 ' + lbl[1]:<{w}}",
        f"{'P1 ' + lbl[0]:>10}  {ratios[0]:^{w}}  {ratios[1]:^{w}}",
        f"{'P1 ' + lbl[1]:>10}  {ratios[2]:^{w}}  {ratios[3]:^{w}}",
    ]
    return "\n".join(lines)


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


def analyze_normal_form_from_merged_state(
    p1_strategy: Strategy,
    p2_strategy: Strategy,
    merged_gamestate: Dict[str, Any],
    *,
    include_mixed: bool = True,
) -> NormalFormResult:
    """Build payoffs from an already-merged gamestate and compute Nash equilibria.

    Does **not** call ``merge_strategy_preferences`` again; use when preferences
    already reflect implied + cares (e.g. ``merge_gamestate_with_strategy_and_cares``).
    """
    if p1_strategy.player != "p1":
        raise ValueError(f"p1_strategy must have player='p1', got {p1_strategy.player!r}")
    if p2_strategy.player != "p2":
        raise ValueError(f"p2_strategy must have player='p2', got {p2_strategy.player!r}")
    p1_m, p2_m = build_payoff_matrices_at_merged_state(merged_gamestate)
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


def normal_form_to_dict(
    result: NormalFormResult,
    *,
    include_best_responses: bool = True,
) -> Dict[str, Any]:
    """JSON-friendly snapshot of a normal-form analysis (for UI/APIs).

    ``pure_nash_indices`` entries are ``[row_i, col_j]`` lists.
    Mixed equilibria use parallel lists ``p1_probs_swerve_stay`` and
    ``p2_probs_swerve_stay`` (same order as ``ACTION_ORDER``).
    """
    out: Dict[str, Any] = {
        "p1_strategy_name": result.p1_strategy_name,
        "p2_strategy_name": result.p2_strategy_name,
        "action_labels": list(result.action_labels),
        "payoff_p1": [list(row) for row in result.payoff_p1],
        "payoff_p2": [list(row) for row in result.payoff_p2],
        "pure_nash_indices": [[int(i), int(j)] for i, j in result.pure_nash_indices],
        "mixed_equilibria": [
            {
                "p1_probs_swerve_stay": list(sig),
                "p2_probs_swerve_stay": list(rho),
            }
            for sig, rho in result.mixed_equilibria
        ],
    }
    if include_best_responses:
        out["best_responses"] = best_response_correspondences(
            result.payoff_p1, result.payoff_p2
        )
    return out


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


# Width of each matrix cell interior (ASCII grid).
_ASCII_CELL_WIDTH = 22


def _nash_cell_text(
    u1: int, u2: int, is_pure_ne: bool, width: int = _ASCII_CELL_WIDTH
) -> str:
    body = f"({u1},{u2})"
    if is_pure_ne:
        body += " *NE*"
    if len(body) > width:
        body = body[: max(0, width - 1)] + "…"
    return body.ljust(width)


def format_nash_grid_ascii(
    result: NormalFormResult,
    *,
    include_header: bool = True,
    header_title: str = "One-shot normal form (resilience utilities)",
    inner_width: int = _ASCII_CELL_WIDTH,
    include_mixed_footer: bool = True,
) -> str:
    """Draw a 2×2 matrix with borders; pure Nash cells tagged ``*NE*``.

    Set ``include_header=False`` for embedded panels (e.g. hypothesis vs final).
    """
    ne_set = set(result.pure_nash_indices)
    lbl = result.action_labels
    row_w = max(len("P1 " + lbl[0]), len("P1 " + lbl[1]), 6)
    bar = "+" + "+".join("-" * (inner_width + 2) for _ in range(2)) + "+"

    lines: List[str] = []
    if include_header:
        lines.append(header_title)
        lines.append(
            f"P1: {result.p1_strategy_name}  vs  P2: {result.p2_strategy_name}"
        )
        lines.append("")

    # Column labels (P2 actions), then top rule.
    lines.append(
        f"{'':>{row_w}}  "
        f"{'P2 ' + lbl[0]:<{inner_width + 3}}  "
        f"{'P2 ' + lbl[1]:<{inner_width + 3}}"
    )
    lines.append(f"{'':>{row_w}} {bar}")
    for i, row_lbl in enumerate(lbl):
        cells = "|".join(
            f" {_nash_cell_text(result.payoff_p1[i][j], result.payoff_p2[i][j], (i, j) in ne_set, inner_width)} "
            for j in range(2)
        )
        lines.append(f"{'P1 ' + row_lbl:>{row_w}} |{cells}|")
        lines.append(f"{'':>{row_w}} {bar}")
    lines.append("")
    lines.append(
        f"Pure NE (row_i, col_j): {result.pure_nash_indices or 'none'}"
    )
    if include_mixed_footer and result.mixed_equilibria:
        lines.append("Mixed NE (σ swerve/stay, ρ swerve/stay):")
        for sig, rho in result.mixed_equilibria:
            lines.append(f"  σ={sig}  ρ={rho}")
    elif include_mixed_footer:
        lines.append("Mixed NE: (none or not computed)")
    return "\n".join(lines)


def _nash_comparison_footer(
    hypothesis: NormalFormResult, final: NormalFormResult
) -> str:
    same_matrix = (
        hypothesis.payoff_p1 == final.payoff_p1
        and hypothesis.payoff_p2 == final.payoff_p2
    )
    same_pure = set(hypothesis.pure_nash_indices) == set(final.pure_nash_indices)
    return "\n".join(
        [
            "--- Comparison ---",
            f"Payoff matrices identical: {same_matrix}",
            f"Pure NE set identical: {same_pure}",
            f"  hypothesis pure NE: {sorted(hypothesis.pure_nash_indices)}",
            f"  final pure NE:      {sorted(final.pure_nash_indices)}",
        ]
    )


def format_nash_hypothesis_vs_final_ascii(
    hypothesis: NormalFormResult,
    final: NormalFormResult,
    *,
    hypothesis_caption: str = "Hypothesis NE (pre-match normal form)",
    final_caption: str = "Final NE (one-shot form using post-match gamestate)",
) -> str:
    """Stack two ASCII grids plus a short comparison footer.

    ``hypothesis`` is typically ``analyze_normal_form`` on the starting state;
    ``final`` uses the same strategies on ``final_state`` after a simulation.
    """
    blocks = [
        "=" * 62,
        hypothesis_caption,
        format_nash_grid_ascii(
            hypothesis, include_header=False, include_mixed_footer=False
        ),
        "",
        "=" * 62,
        final_caption,
        format_nash_grid_ascii(
            final, include_header=False, include_mixed_footer=False
        ),
        "",
        _nash_comparison_footer(hypothesis, final),
    ]
    return "\n".join(blocks)


def report_match_hypothesis_vs_final_nash(
    p1_strategy: Strategy,
    p2_strategy: Strategy,
    *,
    max_rounds: int = 10,
    initial_gamestate: Optional[Dict[str, Any]] = None,
    include_mixed: bool = False,
    joint_mixed_index: int = 0,
) -> str:
    """Simulate a match, then ASCII-report hypothesis vs post-match normal-form NE.

    The one-shot payoffs for the "final" panel use ``merge_strategy_preferences``
    on a deep copy of the match ``final_state`` (HP, etc.), so the matrix can
    differ from the hypothesis when injuries change counterfactual round utilities.

    Appends a **joint-play vs hypothesis** table: observed counts per cell divided by
    ``N · Pr(cell)`` under the hypothesis NE (``joint_mixed_index`` selects which mixed
    equilibrium when several exist; pure NE uses a uniform mixture over listed cells).

    Uses a lazy import of ``GameSimulator`` to limit import cycles.
    """
    try:
        from .strategies import GameSimulator
    except ImportError:
        from strategies import GameSimulator  # type: ignore

    if initial_gamestate is None:
        base_for_hyp = GameEngine().get_gamestate()
    else:
        base_for_hyp = deepcopy(initial_gamestate)

    hypothesis = analyze_normal_form(
        p1_strategy,
        p2_strategy,
        base_for_hyp,
        include_mixed=include_mixed,
    )
    sim = GameSimulator()
    outcome = sim.simulate(
        p1_strategy,
        p2_strategy,
        max_rounds=max_rounds,
        initial_gamestate=initial_gamestate,
    )
    final_gs = deepcopy(outcome["final_state"])
    final = analyze_normal_form(
        p1_strategy,
        p2_strategy,
        final_gs,
        include_mixed=include_mixed,
    )
    summ = outcome.get("summary", {})
    margin = float(
        summ.get("resilience_margin_p1_minus_p2", resilience_margin_p1_minus_p2(final_gs))
    )
    leader = str(
        summ.get("resilience_leader", resilience_leader_p1_seat(final_gs))
    )
    leader_txt = {
        "p1": "P1 ahead on resilience",
        "p2": "P2 ahead on resilience",
        "tie": "tied on resilience",
    }.get(leader, leader)
    # ``p1_wins`` / ``p2_wins`` are per-round ``score`` labels, not margin “wins”.
    header = (
        f"Match recap: max_rounds={max_rounds}  |  "
        f"resilience margin (P1−P2): {margin:+.1f}  →  {leader_txt}  |  "
        f"round score tallies: P1={summ.get('p1_wins')}  P2={summ.get('p2_wins')}  "
        f"TIE={summ.get('ties')}  CRASH={summ.get('crashes')}  |  "
        f"final HP P1={final_gs.get('p1_hp')}  P2={final_gs.get('p2_hp')}"
    )
    joint_section = ""
    try:
        n_r = len(final_gs.get("p1_action_history") or [])
        if n_r > 0:
            counts = empirical_joint_action_counts(final_gs)
            joint_section = "\n\n" + format_joint_play_vs_hypothesis_ascii(
                counts,
                hypothesis,
                n_rounds=n_r,
                mixed_index=joint_mixed_index,
            )
    except ValueError as exc:
        joint_section = f"\n\n(joint-frequency table skipped: {exc})"

    return "\n".join(
        [
            header,
            "",
            format_nash_hypothesis_vs_final_ascii(
                hypothesis,
                final,
                hypothesis_caption="Hypothesis NE (pre-match normal form)",
                final_caption="Final NE (post-match gamestate → one-shot matrix)",
            ),
            joint_section,
        ]
    )


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
