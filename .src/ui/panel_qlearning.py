"""Streamlit panel for Q-learning training, greedy evaluation, and Q-table inspection."""

from __future__ import annotations

import json
from typing import Optional

import streamlit as st

from ui.loading_indicator import loading_row

from ql_strategy import QLearningStrategy
from train_ql import OPPONENT_CHOICES, run_greedy_evaluation_episodes, train_ql_agent

# Offline demo defaults (panel-only; training script may use other schedules).
_QL_EPSILON_START = 0.25
_QL_EPSILON_END = 0.05
_QL_MINIMAX_DEPTH_DEFAULT = 2


def render_learned_q_table(agent: QLearningStrategy) -> None:
    """Show learned Q-table and JSON download button."""
    st.subheader("Learned Q-table (RL)")
    st.caption(
        "Each row is a visited state. **q_swerve** / **q_stay** are Q(s, swerve) and Q(s, stay) "
        "(bool actions False / True)."
    )
    st.dataframe(agent.q_table_records(), use_container_width=True, hide_index=True)
    st.download_button(
        label="Download Q-table JSON",
        data=json.dumps(agent.q_table_payload(), indent=2),
        file_name="q_table_payload.json",
        mime="application/json",
        key="download_q_table_json",
    )


def render_qlearning_panel() -> None:
    """Optional offline Q-learning lab (separate from the main match sidebar)."""
    with st.expander("Optional: offline Q-learning lab", expanded=False):
        st.markdown(
            "**Main match:** pick **Q-learning (tabular)** in the P1 or P2 strategy dropdown above. "
            "On **Start New Game**, the agent trains vs the other player’s strategy, runs a short greedy "
            "eval, then plays in the arena with NE / history like any other strategy.\n\n"
            "Below: train against **named** built-in opponents only, inspect **Q(s,·)**, and run extra greedy "
            "evals without touching the live match."
        )

        ql_seat = st.radio(
            "Agent seat",
            options=("p1", "p2"),
            format_func=lambda s: "Player 1" if s == "p1" else "Player 2",
            horizontal=True,
            index=0,
            key="ql_agent_seat",
            help="Q-table state encoding depends on seat; train and evaluate with the same seat.",
        )
        agent_plays_p1 = ql_seat == "p1"

        c1, c2, c3 = st.columns(3)
        with c1:
            ql_episodes = st.number_input(
                "Training episodes",
                min_value=5,
                max_value=2000,
                value=80,
                step=5,
                key="ql_episodes",
            )
        with c2:
            ql_max_rounds = st.number_input(
                "Max rounds / game",
                min_value=3,
                max_value=30,
                value=12,
                key="ql_max_rounds",
            )
        with c3:
            ql_seed = st.number_input("Agent / opponent RNG seed", min_value=0, value=0, key="ql_seed")

        ql_opp = st.selectbox("Opponent (train & eval)", options=OPPONENT_CHOICES, index=0, key="ql_opponent")
        ql_minimax_depth = st.number_input(
            "Minimax depth (only if opponent is minimax)",
            min_value=1,
            max_value=6,
            value=_QL_MINIMAX_DEPTH_DEFAULT,
            step=1,
            key="ql_minimax_depth",
        )

        if st.button("Run Q-learning training", key="ql_train_btn"):
            demo = QLearningStrategy(ql_seat, seed=int(ql_seed))
            with loading_row("Training…"):
                train_ql_agent(
                    demo,
                    opponent=ql_opp,
                    episodes=int(ql_episodes),
                    max_rounds=int(ql_max_rounds),
                    agent_plays_p1=agent_plays_p1,
                    epsilon_start=_QL_EPSILON_START,
                    epsilon_end=_QL_EPSILON_END,
                    minimax_depth=int(ql_minimax_depth),
                    random_seed=int(ql_seed),
                )
            st.session_state["ql_demo_agent"] = demo
            st.session_state["ql_trained_opponent"] = ql_opp
            st.session_state["ql_trained_seat"] = ql_seat
            st.success(
                f"Trained **{ql_seat}** vs **{ql_opp}** for {int(ql_episodes)} episodes "
                f"(max {int(ql_max_rounds)} rounds per game)."
            )

        agent: Optional[QLearningStrategy] = st.session_state.get("ql_demo_agent")
        trained_seat: Optional[str] = st.session_state.get("ql_trained_seat")

        st.divider()
        st.subheader("Greedy evaluation (no weight updates)")
        st.caption(
            "Runs the **current** Q-policy with exploration off, against the **same opponent** "
            "selected above. Episode wins/losses/ties use final **resilience margin** (same as training)."
        )
        ql_eval_eps = st.number_input(
            "Evaluation episodes",
            min_value=1,
            max_value=500,
            value=20,
            step=1,
            key="ql_eval_episodes",
        )
        if st.button("Run greedy evaluation vs opponent", key="ql_eval_btn"):
            if agent is None:
                st.warning("Train an agent first.")
            elif agent.player != ql_seat:
                st.warning(
                    f"The loaded agent was built for seat **{agent.player}**, but you selected **{ql_seat}**. "
                    "Re-train with the seat you want, or switch the seat radio to match the agent."
                )
            else:
                with loading_row("Evaluating (greedy)…"):
                    stats = run_greedy_evaluation_episodes(
                        agent,
                        ql_opp,
                        episodes=int(ql_eval_eps),
                        max_rounds=int(ql_max_rounds),
                        agent_plays_p1=agent_plays_p1,
                        minimax_depth=int(ql_minimax_depth),
                        random_seed=int(ql_seed),
                    )
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Wins", stats.wins)
                m2.metric("Losses", stats.losses)
                m3.metric("Ties", stats.ties)
                m4.metric("Opponent", stats.opponent)
                st.caption(
                    f"Agent seat: **{stats.agent_role}** · Episodes: **{stats.episodes}** · "
                    f"Per-round score tallies (auxiliary): P1={stats.total_p1_wins_in_score}, "
                    f"P2={stats.total_p2_wins_in_score}"
                )

        if agent is not None and trained_seat is not None and trained_seat != ql_seat:
            st.info(
                f"Trained agent is in seat **{trained_seat}**. Seat radio is **{ql_seat}** — "
                "use matching seat for greedy eval, or re-train."
            )

        if agent is not None:
            render_learned_q_table(agent)
