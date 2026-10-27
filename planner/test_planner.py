"""Checks for the planner: saved models reproduce planner_reference.csv, and the chat behaves.

Run from the Session 19 folder:  ../../.venv/bin/python planner/test_planner.py
"""
import os
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from chat_engine import choose_objective, new_state, read_message, respond
from plan_predict import TARGETS, break_even, missing_inputs, predict

HERE = Path(__file__).resolve().parent


def holdout() -> pd.DataFrame:
    return pd.read_csv(HERE / "data" / "planner_holdout.csv", keep_default_na=False)


def concept(test_id: str) -> dict:
    """The main-form inputs only (no chat extras), as the app would pass them."""
    row = holdout().set_index("TestID").loc[test_id].to_dict()
    extras = {"guests_per_day", "opening_hours", "delivery_share", "menu_items", "alcohol_share", "takeover"}
    return {k: v for k, v in row.items() if k not in extras and k not in TARGETS and k != "restaurant_name"}


def test_models_match_reference():
    ref = pd.read_csv(HERE / "data" / "planner_reference.csv")
    for _, row in holdout().iterrows():
        expected = ref.set_index("TestID").loc[row["TestID"]]
        for target in TARGETS:
            got = predict(target, row.to_dict())["value"]
            assert abs(got - expected[f"{target} (predicted)"]) < 1e-3, (row["TestID"], target)


def test_missing_inputs():
    c = concept("T03")  # no bar → alcohol share never asked
    assert missing_inputs("floor_area_sqft", c) == ["guests_per_day", "delivery_share"]
    assert "alcohol_share" not in missing_inputs("break_even", c)
    assert "alcohol_share" in missing_inputs("food_cost_pct", concept("T06"))  # T06 is a bar


def test_break_even_adds_up():
    row = holdout().iloc[2].to_dict()
    b = break_even(row)
    assert abs(b["revenue"] - sum(b["costs"].values()) - b["profit"]) < 1e-6
    assert b["months"] and abs(b["months"] - b["predictions"]["investment_lakh"] * 1e5 / b["profit"]) < 1e-9


def test_chat_asks_then_answers():
    state = new_state(concept("T03"))
    assert "guests" in respond(state, "How many staff do I need?")[0]
    respond(state, "150")
    assert "typical value: 12 hours" in respond(state, "not sure")[0]
    respond(state, "60")
    reply = respond(state, "50")[-1]
    expected = predict("staff_count", state["inputs"])["value"]
    assert f"about {round(expected)} people" in reply and "synthetic" in reply
    assert state["inputs"]["guests_per_day"] == 150 and state["inputs"]["opening_hours"] == 12


def test_chat_free_text_and_ranges():
    state = new_state(concept("T03"))
    respond(state, "How big a place do I need?")
    assert "between 20 and 350" in respond(state, "500")[0]                  # out of range → asked again
    respond(state, "I expect 200 guests and 30% delivery")                    # both values from one message
    assert state["inputs"]["guests_per_day"] == 200 and state["inputs"]["delivery_share"] == 30


def test_objective_required():
    state = new_state(concept("T03"))
    reply = respond(state, "We'll have 180 guests a day")[0]                  # inputs only, no objective
    assert "What is your objective?" in reply and "guests per day 180" in reply and state["awaiting_objective"]
    assert "What is your objective?" in respond(state, "hello")[0]           # still unclear → asked again
    assert state["intent"] is None and state["awaiting_objective"]
    assert "hours" in respond(state, "staff needed")[0]                       # typed objective counts
    assert not state["awaiting_objective"] and state["intent"] == "staff_count"

    state = new_state(concept("T03"))                                         # team's case, 2026-10-27
    reply = respond(state, "I have an investment of 1 Cr, and a staff of 20 members with me")[0]
    assert "What is your objective?" in reply and state["intent"] is None     # a statement, not a question
    assert state["inputs"]["budget_lakh"] == 100 and state["inputs"]["staff_available"] == 20
    choose_objective(state, "investment_lakh")
    respond(state, "200")
    assert "covers this" in respond(state, "No")[0]                           # budget compared with the estimate

    state = new_state(concept("T03"))
    respond(state, "not sure what to ask")
    assert "guests" in choose_objective(state, "floor_area_sqft")[0]          # tapped objective counts
    assert not state["awaiting_objective"] and state["inputs"].get("guests_per_day") is None


def test_gemini_problems_fall_back_to_rules():
    def broken(message, state):
        raise TimeoutError

    def bad_intent(message, state):
        return {"intent": "predict_my_price_please", "values": {}}

    def good(message, state):
        return {"intent": "revenue_lakh", "values": {"opening_hours": 14, "made_up_field": 3}}

    state = new_state(concept("T03"))
    assert read_message("how many staff", state, broken)[0] == "staff_count"
    assert read_message("how many staff", state, bad_intent)[2].startswith("rules")
    intent, values, used = read_message("how long will I stay open and what will I sell", state, good)
    assert (intent, used) == ("revenue_lakh", "gemini") and "made_up_field" not in values


def test_demo_page_renders():
    os.environ["PLANNER_NO_LLM"] = "1"  # rule-based reader: no Gemini calls from tests
    at = AppTest.from_file(str(HERE / "chat_demo.py"), default_timeout=30).run()
    assert not at.exception
    at.chat_input[0].set_value("When will I break even?").run()
    assert not at.exception and at.session_state["chat"]["asking"] == "guests_per_day"
    [b for b in at.button if b.label == "Start a new chat"][0].click().run()
    at.chat_input[0].set_value("hello").run()                                  # unclear → objective buttons
    assert at.session_state["chat"]["awaiting_objective"]
    at.button_group[0].set_value("revenue_lakh").run()
    assert not at.exception and at.session_state["chat"]["intent"] == "revenue_lakh"


if __name__ == "__main__":
    tests = [test_models_match_reference, test_missing_inputs, test_break_even_adds_up, test_chat_asks_then_answers,
             test_chat_free_text_and_ranges, test_objective_required, test_gemini_problems_fall_back_to_rules, test_demo_page_renders]
    for test in tests:
        test()
        print(f"✔ {test.__name__}")
    print("PASSED")
