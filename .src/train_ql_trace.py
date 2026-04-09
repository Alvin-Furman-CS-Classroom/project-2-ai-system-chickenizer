"""Per-engine-round training trace: actions, margins, and Q-learning TD rewards.

Use with ``train_ql_agent(..., training_round_trace_out=[], training_round_trace_max_engine_rounds=n)``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from ql_strategy import (
    QLearningStrategy,
    agent_resilience_margin,
    terminal_margin_bonus,
)


def agent_decision_margins_from_history(
    history: Sequence[Dict[str, Any]], agent_plays_p1: bool
) -> Dict[int, float]:
    """Agent margin at each decision point, keyed by completed-round count at decision time.

    Keys are ``len(score)`` (P1) or ``len(p1_action_history)`` (P2). Using a map avoids a
    bug where the first history row can be a stale end-of-previous-game snapshot, which
    would poison list index ``0`` if we ordered margins by encounter order only.
    """
    role = "p1" if agent_plays_p1 else "p2"
    out: Dict[int, float] = {}
    for gs in history:
        h1 = gs.get("p1_action_history") or []
        h2 = gs.get("p2_action_history") or []
        sc = gs.get("score") or []
        if agent_plays_p1:
            if len(h1) != len(h2) or len(h1) != len(sc):
                continue
            key = len(sc)
        else:
            if len(h1) != len(h2) + 1:
                continue
            key = len(h1)
        if key in out:
            continue
        out[key] = agent_resilience_margin(role, gs)
    return out


def _snapshot_after_round(
    history: Sequence[Dict[str, Any]], round_1based: int
) -> Optional[Dict[str, Any]]:
    for gs in history:
        if len(gs.get("score") or []) == round_1based:
            return gs
    return None


def _agent_decision_meta_by_completed_round(
    agent_trace: Optional[List[Dict[str, Any]]]
) -> Dict[int, Dict[str, Any]]:
    if not agent_trace:
        return {}
    out: Dict[int, Dict[str, Any]] = {}
    for e in agent_trace:
        k = int(e["completed_rounds_before"])
        out[k] = {
            "agent_explored": bool(e["explored"]),
            "agent_stay": bool(e["stay"]),
        }
    return out


def extract_episode_round_trace(
    simulate_result: Dict[str, Any],
    *,
    episode_index: int,
    agent_plays_p1: bool,
    agent: QLearningStrategy,
) -> List[Dict[str, Any]]:
    """One row per completed engine round: joint play, margins, and matching Q TD reward.

    ``ql_td_reward`` matches the learner's margin-delta shaping for that transition
    (last round includes terminal bonus from ``terminal_margin_bonus``).
    """
    history = simulate_result.get("history") or []
    fs = simulate_result["final_state"]
    score = fs.get("score") or []
    h1 = fs.get("p1_action_history") or []
    h2 = fs.get("p2_action_history") or []
    role = "p1" if agent_plays_p1 else "p2"
    margins = agent_decision_margins_from_history(history, agent_plays_p1)
    meta = _agent_decision_meta_by_completed_round(agent._episode_decision_trace)

    R = len(score)
    rows: List[Dict[str, Any]] = []
    margin_final = agent_resilience_margin(role, fs)
    term = terminal_margin_bonus(
        role,
        fs,
        terminal_win=agent.terminal_win,
        terminal_loss=agent.terminal_loss,
    )

    def _m(k: int) -> Optional[float]:
        return margins.get(k)

    for r in range(R):
        snap = _snapshot_after_round(history, r + 1)
        mafter = (
            agent_resilience_margin(role, snap)
            if snap is not None
            else margin_final
        )
        # P1 margin keys match len(score) at decision: 0..R-1.
        # P2 acts after P1 each round, so keys are len(p1_hist) = 1..R (never 0).
        k_cur = r if agent_plays_p1 else (r + 1)
        cur = _m(k_cur)
        m_dec = float(cur) if cur is not None else float("nan")
        if r < R - 1:
            k_next = (r + 1) if agent_plays_p1 else (r + 2)
            nxt = _m(k_next)
            if cur is not None and nxt is not None:
                ql_td = float(nxt - cur)
            else:
                ql_td = float("nan")
        else:
            if cur is not None:
                ql_td = float(margin_final - cur + term)
            else:
                ql_td = float("nan")

        am = meta.get(r, {})
        rows.append(
            {
                "train_episode": episode_index,
                "round_in_episode": r + 1,
                "p1_action": h1[r] if r < len(h1) else None,
                "p2_action": h2[r] if r < len(h2) else None,
                "outcome": score[r] if r < len(score) else None,
                "agent_margin_at_decision": m_dec,
                "agent_margin_after_round": mafter,
                "ql_td_reward": ql_td,
                "agent_stay": am.get("agent_stay"),
                "agent_explored": am.get("agent_explored"),
            }
        )
    return rows


def _fmt_f(x: Any, width: int) -> str:
    if isinstance(x, (int, float)) and x == x:
        return f"{float(x):>{width}.1f}"
    return f"{'nan':>{width}}"


def format_training_round_trace(rows: Sequence[Dict[str, Any]]) -> str:
    """Fixed-width table for CLI or logs."""
    if not rows:
        return "(no trace rows)\n"
    w_ep, w_rn = 4, 5
    w_act, w_out = 9, 8
    w_m1, w_m2, w_q = 11, 11, 10
    w_agent, w_ex = 7, 7
    hdr = (
        f"{'Ep':>{w_ep}}  {'Round':>{w_rn}}  "
        f"{'P1':<{w_act}}  {'P2':<{w_act}}  {'Outcome':<{w_out}}  "
        f"{'Margin@move':>{w_m1}}  {'Margin_end':>{w_m2}}  {'Q_reward':>{w_q}}  "
        f"{'RL_move':>{w_agent}}  {'Explore':>{w_ex}}"
    )
    lines = [
        "Training round trace — Margin@move: agent's resilience margin when they choose an action;",
        "Margin_end: margin after both play and the round resolves.",
        "Q_reward: margin change to the next agent decision; LAST row adds terminal bonus for",
        "resilience tap-out, or HP knockout when resilience_diff != 0 — not on round_cap or tied diff.",
        "RL_move / Explore: learned agent's action and whether ε exploration was used.",
        hdr,
        "-" * len(hdr),
    ]
    for row in rows:
        ag = row.get("agent_stay")
        ag_s = "stay" if ag is True else ("swerve" if ag is False else "—")
        ex = row.get("agent_explored")
        ex_s = "yes" if ex is True else ("no" if ex is False else "—")
        lines.append(
            f"{row['train_episode']:>{w_ep}}  {row['round_in_episode']:>{w_rn}}  "
            f"{str(row.get('p1_action')):<{w_act}}  {str(row.get('p2_action')):<{w_act}}  "
            f"{str(row.get('outcome')):<{w_out}}  "
            f"{_fmt_f(row.get('agent_margin_at_decision'), w_m1)}  "
            f"{_fmt_f(row.get('agent_margin_after_round'), w_m2)}  "
            f"{_fmt_f(row.get('ql_td_reward'), w_q)}  "
            f"{ag_s:>{w_agent}}  {ex_s:>{w_ex}}"
        )
    return "\n".join(lines) + "\n"
