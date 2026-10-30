"""Standalone test page for the "Plan my restaurant" chat (not yet wired into app.py).

Run from the Session 19 folder:   ../../.venv/bin/streamlit run planner/chat_demo.py
Optional Gemini key (never commit it): planner/.streamlit/secrets.toml → GEMINI_API_KEY = "..."
or the GEMINI_API_KEY environment variable. Without a key the rule-based reader is used.
"""
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from chat_engine import OBJECTIVES, choose_objective, gemini_reader, new_state, respond
from plan_predict import CUISINES

HERE = Path(__file__).resolve().parent
CONCEPT_FIELDS = ["location", "primary_type", "has_bar", "online_order", "book_table", *CUISINES]


def secret(name: str, default: str | None = None) -> str | None:
    try:
        return st.secrets.get(name) or os.environ.get(name) or default
    except Exception:  # noqa: BLE001 – no secrets.toml
        return os.environ.get(name) or default


@st.cache_data
def reference_concepts() -> dict[str, dict]:
    ref = pd.read_csv(HERE.parent / "reference_tests.csv", dtype=str, keep_default_na=False)
    out = {}
    for _, r in ref.iterrows():
        concept = {f: r[f] for f in CONCEPT_FIELDS}
        concept.update(n_cuisines=int(float(r["n_cuisines"])), cost_for_two=float(r["cost_for_two"]))
        out[f"{r['TestID']} {r['restaurant_name']}"] = concept
    return out


def main() -> None:
    st.set_page_config(page_title="SpotCheck – Plan chat (test)", page_icon="💬")
    st.title("Plan my restaurant 💬")
    st.caption("Test page. In the app, the concept comes from the SpotCheck wizard.")

    concepts = reference_concepts()
    choice = st.selectbox("Concept (reference restaurant)", list(concepts), index=2)
    if st.session_state.get("concept_choice") != choice or st.button("Start a new chat"):
        st.session_state.concept_choice = choice
        st.session_state.chat = new_state(concepts[choice])
    state = st.session_state.chat
    c = state["inputs"]
    st.markdown(f"**{c['primary_type']}** in **{c['location']}** · ₹{c['cost_for_two']:,.0f} for two · "
                f"{c['n_cuisines']} cuisines · alcohol {c['has_bar']} · online {c['online_order']} · "
                f"booking {c['book_table']}")

    key = None if os.environ.get("PLANNER_NO_LLM") else secret("GEMINI_API_KEY")
    llm = gemini_reader(key, secret("GEMINI_MODEL", "gemini-3.5-flash-lite")) if key else None
    st.info("Answers are **estimates from synthetic planning data** (Linear Regression), not real Bangalore figures. "
            + ("Your messages are sent to Google Gemini only to understand the question; "
               "every number comes from SpotCheck's models." if llm else "Question reader: built-in rules (no AI)."),
            icon="ℹ️")

    for msg in state["history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if not state["history"]:
        with st.chat_message("assistant"):
            st.markdown("Hi! Ask me anything about opening this restaurant: size, staff, money to open, food cost, "
                        "revenue or break-even. You can also tell me details like “we'll be open 12 hours”.")
    if state["awaiting_objective"]:
        picked = st.pills("Your objective", list(OBJECTIVES), format_func=OBJECTIVES.get,
                          key=f"objective_{len(state['history'])}")
        if picked:
            choose_objective(state, picked)
            st.rerun()
    typed = st.chat_input("Type your objective…" if state["awaiting_objective"] else
                          "Ask about size, staff, investment, food cost, revenue or break-even…")
    if typed:
        respond(state, typed, llm)
        st.rerun()


if __name__ == "__main__":
    main()
