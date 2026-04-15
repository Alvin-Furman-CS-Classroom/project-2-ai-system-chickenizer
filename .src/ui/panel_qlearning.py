"""Streamlit panel for Q-learning training + Q-table inspection."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from ql_strategy import QLearningStrategy
from train_ql import OPPONENT_CHOICES, train_ql_agent


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
    """Render train-and-inspect RL panel inside an expander."""
    with st.expander("Q-learning: train & inspect Q-table", expanded=False):
        st.markdown(
            "Train a tabular Q-agent offline and inspect **Q(s,·)**. In code, use "
            "`agent.q_table_records()` for a list of rows, or `agent.q_table_payload()` for JSON."
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            ql_episodes = st.number_input(
                "Episodes", min_value=5, max_value=2000, value=80, step=5, key="ql_episodes"
            )
        with c2:
            ql_max_rounds = st.number_input(
                "Max rounds / game", min_value=3, max_value=30, value=12, key="ql_max_rounds"
            )
        with c3:
            ql_seed = st.number_input("Agent seed", min_value=0, value=0, key="ql_seed")
        ql_opp = st.selectbox("Opponent", options=OPPONENT_CHOICES, index=0, key="ql_opponent")
        if st.button("Run Q-learning training", key="ql_train_btn"):
            demo = QLearningStrategy("p1", seed=int(ql_seed))
            with st.spinner("Training…"):
                train_ql_agent(
                    demo,
                    opponent=ql_opp,
                    episodes=int(ql_episodes),
                    max_rounds=int(ql_max_rounds),
                    epsilon_start=0.25,
                    epsilon_end=0.05,
                )
            st.session_state["ql_demo_agent"] = demo
        agent: Any = st.session_state.get("ql_demo_agent")
        if agent is not None:
            render_learned_q_table(agent)

