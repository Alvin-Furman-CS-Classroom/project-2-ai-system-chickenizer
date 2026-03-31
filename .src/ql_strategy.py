"""Tabular Q-learning strategy for Chickenizer.

State uses binned *own* resilience and last observable actions — not opponent
resilience. Reward = change in own resilience between decisions (full rounds in
effect for the acting player) plus terminal win/loss bonuses in
``finalize_episode``. ``GameSimulator`` calls ``finalize_episode`` when present.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Optional, Tuple, Union

from strategies import Strategy


StateKey = Tuple[int, int, int]  # (own_res_bin, my_last, opp_last)

# Action codes from last moves (see _act_code): 0 swerve, 1 stay, 2 unknown/start.
_ACTION_CODE_LABEL: Dict[int, str] = {0: "swerve", 1: "stay", 2: "(none)"}


def resilience_bin_label(bin_index: int) -> str:
    """Human-readable label for own-resilience bin used in ``encode_ql_state``."""
    width = 40
    low = -80 + int(bin_index) * width
    high = low + width - 1
    return f"bin {bin_index} [{low}, {high}]"


def _act_code(last_move: str) -> int:
    if last_move == "stay":
        return 1
    if last_move == "swerve":
        return 0
    return 2


def _bin_own_resilience(r: int) -> int:
    width = 40
    b = (int(r) + 80) // width
    return max(0, min(4, int(b)))


def encode_ql_state(player: str, gamestate: Dict[str, Any]) -> StateKey:
    """Observable features only: own resilience bucket + action codes.

    Before P1 acts, len(p1_hist) == len(p2_hist). Before P2 acts, len(p1_hist) == len(p2_hist) + 1.
    """
    own = int(gamestate.get(f"{player}_resilience", 0))
    b = _bin_own_resilience(own)

    h1 = gamestate.get("p1_action_history") or []
    h2 = gamestate.get("p2_action_history") or []

    if player == "p1":
        if not h1 and not h2:
            return (b, 2, 2)
        if len(h1) != len(h2):
            return (b, 2, 2)
        my_last = _act_code(h1[-1])
        opp_last = _act_code(h2[-1])
        return (b, my_last, opp_last)

    # P2: P1 has already acted this round
    if len(h1) != len(h2) + 1:
        if len(h1) == len(h2):
            my_last = _act_code(h2[-1]) if h2 else 2
            opp_last = _act_code(h1[-1]) if h1 else 2
            return (b, my_last, opp_last)
        return (b, 2, 2)

    my_last = _act_code(h2[-1]) if h2 else 2
    opp_last = _act_code(h1[-1])
    return (b, my_last, opp_last)


def _own_resilience(player: str, gamestate: Dict[str, Any]) -> int:
    return int(gamestate.get(f"{player}_resilience", 0))


class QLearningStrategy(Strategy):
    """Epsilon-greedy tabular Q-learning (own resilience + actions; no opp resilience)."""

    def __init__(
        self,
        player: str,
        *,
        alpha: float = 0.15,
        gamma: float = 0.95,
        epsilon: float = 0.15,
        terminal_win: float = 50.0,
        terminal_loss: float = 50.0,
        learn: bool = True,
        seed: Optional[int] = None,
    ):
        super().__init__(player)
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.terminal_win = terminal_win
        self.terminal_loss = terminal_loss
        self.learn = learn
        self.rng = random.Random(seed)

        self.q: DefaultDict[StateKey, Dict[bool, float]] = defaultdict(
            lambda: {False: 0.0, True: 0.0}
        )

        self._prev_s: Optional[StateKey] = None
        self._prev_a: Optional[bool] = None
        self._res_before_action: Optional[int] = None

    def q_table_records(self) -> List[Dict[str, Any]]:
        """One row per visited state: columns are stable for ``st.dataframe`` / CSV / charts."""
        rows: List[Dict[str, Any]] = []
        for key in sorted(self.q.keys()):
            own_bin, my_c, opp_c = key
            qd = self.q[key]
            q_swerve = float(qd[False])
            q_stay = float(qd[True])
            greedy_stay = q_stay >= q_swerve
            rows.append(
                {
                    "own_res_bin": own_bin,
                    "own_resilience_bin": resilience_bin_label(own_bin),
                    "my_last_code": my_c,
                    "my_last": _ACTION_CODE_LABEL.get(my_c, str(my_c)),
                    "opp_last_code": opp_c,
                    "opp_last": _ACTION_CODE_LABEL.get(opp_c, str(opp_c)),
                    "q_swerve": q_swerve,
                    "q_stay": q_stay,
                    "greedy_action": "stay" if greedy_stay else "swerve",
                }
            )
        return rows

    def q_table_payload(self) -> Dict[str, Any]:
        """JSON-friendly snapshot for UI download APIs and inspection after training."""
        return {
            "schema_version": 1,
            "player": self.player,
            "hyperparameters": {
                "alpha": self.alpha,
                "gamma": self.gamma,
                "epsilon": self.epsilon,
                "terminal_win": self.terminal_win,
                "terminal_loss": self.terminal_loss,
            },
            "visited_states": len(self.q),
            "rows": self.q_table_records(),
        }

    def write_q_table_json(self, path: Union[str, Path]) -> None:
        """Persist ``q_table_payload()`` for the UI or external tools."""
        Path(path).write_text(
            json.dumps(self.q_table_payload(), indent=2), encoding="utf-8"
        )

    def reset_episode(self) -> None:
        self._prev_s = None
        self._prev_a = None
        self._res_before_action = None

    def abandon_episode(self) -> None:
        """Clear TD bookkeeping without a learning update (e.g. simulation crashed)."""
        self.reset_episode()

    def _engine_cls(self):
        try:
            from .engine import GameEngine
        except ImportError:
            from engine import GameEngine  # type: ignore
        return GameEngine

    def _terminal_extra(self, gs: Dict[str, Any]) -> float:
        th = self._engine_cls().RESILIENCE_THRESHOLD
        if self.player == "p1":
            if gs.get("p2_hp", 1) <= 0:
                return self.terminal_win
            if gs.get("p1_hp", 1) <= 0:
                return -self.terminal_loss
            d = gs.get("resilience_diff", 0)
            if d >= th:
                return self.terminal_win
            if d <= -th:
                return -self.terminal_loss
        else:
            if gs.get("p1_hp", 1) <= 0:
                return self.terminal_win
            if gs.get("p2_hp", 1) <= 0:
                return -self.terminal_loss
            d = gs.get("resilience_diff", 0)
            if d <= -th:
                return self.terminal_win
            if d >= th:
                return -self.terminal_loss
        return 0.0

    def _update(
        self,
        s: StateKey,
        a: bool,
        reward: float,
        s_next: StateKey,
        done: bool,
    ) -> None:
        if not self.learn:
            return
        q_sa = self.q[s][a]
        if done:
            target = reward
        else:
            q_next = self.q[s_next]
            max_next = max(q_next[False], q_next[True])
            target = reward + self.gamma * max_next
        self.q[s][a] = (1.0 - self.alpha) * q_sa + self.alpha * target

    def decide(self, gamestate: Dict[str, Any]) -> bool:
        if (
            gamestate.get("round", 0) == 0
            and not gamestate.get("p1_action_history")
            and not gamestate.get("p2_action_history")
        ):
            self.reset_episode()

        s = encode_ql_state(self.player, gamestate)
        res_now = _own_resilience(self.player, gamestate)

        if (
            self._prev_s is not None
            and self._prev_a is not None
            and self._res_before_action is not None
        ):
            r = float(res_now - self._res_before_action)
            self._update(self._prev_s, self._prev_a, r, s, done=False)

        if self.rng.random() < self.epsilon:
            action = self.rng.choice([False, True])
        else:
            q = self.q[s]
            qf, qt = q[False], q[True]
            action = True if qt >= qf else False

        self._prev_s = s
        self._prev_a = action
        self._res_before_action = res_now
        return action

    def finalize_episode(self, final_gamestate: Dict[str, Any]) -> None:
        """Last transition when no further ``decide`` call happens for this agent."""
        if self._prev_s is None or self._prev_a is None or self._res_before_action is None:
            return

        res_end = _own_resilience(self.player, final_gamestate)
        shaping = float(res_end - self._res_before_action)
        extra = self._terminal_extra(final_gamestate)
        r = shaping + extra
        s_next = encode_ql_state(self.player, final_gamestate)
        self._update(self._prev_s, self._prev_a, r, s_next, done=True)

        self._prev_s = None
        self._prev_a = None
        self._res_before_action = None
