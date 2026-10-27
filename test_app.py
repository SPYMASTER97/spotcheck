"""App checks: the app shows exactly the predict.py outputs in reference_tests.csv, and every page renders.

Run:  python test_app.py      (or: pytest test_app.py)
"""
import os
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

os.environ["PLANNER_NO_LLM"] = "1"  # the Plan chat uses its rule-based reader in tests: no Gemini calls

import app  # noqa: E402
from plan_predict import predict as plan_predict  # noqa: E402  (app puts planner/ on the path)
from predict import CUISINE_FLAGS  # noqa: E402

HERE = Path(__file__).resolve().parent
APP_FILE = str(HERE / "app.py")


def reference_concepts() -> list[tuple[pd.Series, dict]]:
    ref = pd.read_csv(HERE / "reference_tests.csv", dtype=str, keep_default_na=False)
    out = []
    for _, r in ref.iterrows():
        concept = {"location": r["location"], "primary_type": r["primary_type"], "has_bar": r["has_bar"],
                   "online_order": r["online_order"], "book_table": r["book_table"],
                   "cuisines": [c for c in CUISINE_FLAGS if r[c] == "Yes"],
                   "n_cuisines": int(r["n_cuisines"]), "cost_for_two": int(float(r["cost_for_two"]))}
        out.append((r, concept))
    return out


def test_results_match_reference():
    for r, concept in reference_concepts():
        res = app.assess(app.to_inputs(concept))
        assert abs(res["price"] - float(r["Predicted cost (₹)"])) <= 1, r["TestID"]
        assert abs(res["prob"] - float(r["P(4.0+)"])) <= 0.001, r["TestID"]
        assert app.step_error(4, concept) is None, r["TestID"]


def test_verdict_rules():
    assert app.price_verdict(718, 800)[0] == "In line with market"
    assert app.price_verdict(718, 855)[0] == "Above market"
    assert app.price_verdict(718, 581)[0] == "Below market"
    assert [app.rating_verdict(p)[0] for p in (0.60, 0.59, 0.30, 0.29)] == ["Strong", "Moderate", "Moderate", "Weak"]


def test_step_errors():
    concept = app.new_concept()
    assert app.step_error(1, concept) and app.step_error(2, concept)
    assert concept["n_cuisines"] == 0 and concept["online_order"] == "No"     # nothing picked, online off by default
    assert "at least one cuisine" in app.step_error(3, concept)
    assert app.cuisine_name("c_Cafe") == "Coffee"
    concept.update(cuisines=CUISINE_FLAGS[:4], n_cuisines=2)
    assert "4 cuisines" in app.step_error(3, concept)
    concept.update(cuisines=CUISINE_FLAGS[:9], n_cuisines=8)
    assert "at most 8" in app.step_error(3, concept)


def test_cuisine_total_follows_chips():
    at = AppTest.from_file(APP_FILE, default_timeout=30)
    concept = app.new_concept()
    concept.update(location="BTM", primary_type="Cafe")
    at.session_state["concept"] = concept
    at.session_state["step"] = 3
    at.run()
    at.button_group(key="w_cuisines").set_value(CUISINE_FLAGS[:4]).run()
    assert at.number_input(key="w_n_cuisines").value == 4                  # chips set the total
    at.number_input(key="w_n_cuisines").increment().run()                  # one cuisine outside the list
    assert at.session_state["concept"]["n_cuisines"] == 5
    at.button_group(key="w_cuisines").set_value(CUISINE_FLAGS[:3]).run()   # remove a chip, keep the extra
    assert at.number_input(key="w_n_cuisines").value == 4
    assert not at.exception


def run_page(page: str, concept: dict, whatifs: list | None = None) -> AppTest:
    at = AppTest.from_file(APP_FILE, default_timeout=30)
    at.session_state["page"] = page
    at.session_state["concept"] = concept
    at.session_state["assessed"] = True
    at.session_state["whatifs"] = whatifs or []
    return at.run()


def test_pages_render():
    _, t03 = reference_concepts()[2]  # T03 Roundup Cafe
    results = run_page("results", t03)
    assert not results.exception
    text = " ".join(h.proto.body for h in results.html)
    assert "₹718" in text and "92%" in text  # the numbers the demo checks
    whatifs = [{"changes": {"book_table": "No"}}, {"changes": {"cost_for_two": 1200}}]
    for page in ("check", "compare", "summary", "about"):
        at = run_page(page, t03, whatifs)
        assert not at.exception, (page, at.exception)
    compare_text = " ".join(h.proto.body for h in run_page("compare", t03, whatifs).html)
    assert "₹628" in compare_text and "68%" in compare_text and "95%" in compare_text


def test_whatif_form_multiple_changes():
    _, t03 = reference_concepts()[2]
    at = run_page("compare", t03)
    submit = lambda: [b for b in at.button if b.label == "+ Add what-if card"][0].click().run()
    submit()                                                    # nothing changed → friendly error, no card
    assert at.session_state["whatifs"] == [] and at.error
    at.toggle(key="wi_book_table").set_value(False)
    at.slider(key="wi_cost").set_value(1200)
    submit()                                                    # two settings changed in one card
    assert at.session_state["whatifs"] == [{"changes": {"book_table": "No", "cost_for_two": 1200}}]
    expected = app.assess(app.to_inputs({**t03, "book_table": "No", "cost_for_two": 1200}))
    card = app.scenarios(t03, at.session_state["whatifs"])[1]
    assert card["title"] == "What-if B" and len(card["changes"]) == 2
    assert abs(card["result"]["prob"] - expected["prob"]) < 1e-12
    for area in ("Indiranagar", "HSR"):                         # up to 3 what-ifs, then the form is hidden
        at.selectbox(key="wi_location").set_value(area)
        submit()
    assert len(at.session_state["whatifs"]) == 3
    assert not [b for b in at.button if b.label == "+ Add what-if card"] and not at.exception


def test_whatif_cuisine_total_follows_chips():
    _, t03 = reference_concepts()[2]                                           # 3 cuisines, total 3
    at = run_page("compare", t03)
    picked = CUISINE_FLAGS[:7]
    at.button_group(key="wi_cuisines").set_value(picked).run()               # team's case: 7 chips showed total 4
    assert at.number_input(key="wi_n").value == 7 and not at.exception
    at.number_input(key="wi_n").increment().run()                            # one cuisine outside the list
    at.button_group(key="wi_cuisines").set_value(picked[:5]).run()           # remove 2 chips, keep the extra
    assert at.number_input(key="wi_n").value == 6


def test_wizard_blocks_missing_location():
    at = AppTest.from_file(APP_FILE, default_timeout=30).run()
    assert not at.exception
    next_button = [b for b in at.button if b.label.startswith("Next")][0]
    next_button.click().run()
    assert at.session_state["step"] == 1 and at.error, "step 1 must not advance without a location"


def html_text(at: AppTest) -> str:
    return " ".join(h.proto.body for h in at.html)


def test_plan_needs_a_selected_card():
    _, t03 = reference_concepts()[2]
    at = run_page("compare", t03, [{"changes": {"book_table": "No"}}])
    assert [b for b in at.button if b.label == "Select a card to continue"][0].disabled
    at.button(key="choose_1").click().run()
    assert at.session_state["plan_pick"] == 1 and "Selected" in html_text(at)
    at.button(key="plan_go").click().run()
    assert at.session_state["page"] == "plan" and not at.exception
    plan = at.session_state["plan"]
    assert plan["label"] == "No table booking (What-if B)" and plan["concept"]["book_table"] == "No"
    assert "Plan my restaurant" in html_text(at)


def test_plan_empty_state():
    at = run_page("plan", reference_concepts()[2][1])
    assert "Plan your opening" in html_text(at) and not at.exception
    assert [b for b in at.button if b.label == "Go to Compare →"]


def test_plan_chat_flow_and_summary():
    _, t03 = reference_concepts()[2]
    at = run_page("compare", t03)
    at.button(key="choose_0").click().run()
    at.button(key="plan_go").click().run()
    at.chat_input(key="plan_input").set_value("I have an investment of 1 Cr, and a staff of 20 members").run()
    chat = at.session_state["plan"]["chat"]
    assert chat["awaiting_objective"] and "Budget: ₹100 lakh" in html_text(at)        # facts, then the objective
    at.button_group(key=f"obj_{len(chat['history'])}").set_value("investment_lakh").run()
    for reply in ("150", "No"):                                                      # quick-reply chips
        chat = at.session_state["plan"]["chat"]
        at.button_group(key=f"qr_{len(chat['history'])}").set_value(reply).run()
    chat = at.session_state["plan"]["chat"]
    expected = plan_predict("investment_lakh", chat["inputs"])["value"]
    text = html_text(at)
    assert f"≈ ₹{expected:,.1f} lakh" in text and "to spare" in text and "synthetic" in text
    assert chat["answers"]["investment_lakh"]["value"] == expected and not at.exception
    [b for b in at.button if b.label.startswith("📄 View my plan")][0].click().run()
    summary = html_text(at)
    assert at.session_state["page"] == "summary" and "Your facts: budget ₹100 lakh · 20 staff" in summary
    assert "My opening plan · Your concept (Base)" in summary and f"₹{expected:,.1f} lakh" in summary


def test_plan_range_answer_card():
    _, t03 = reference_concepts()[2]
    at = run_page("compare", t03)
    at.button(key="choose_0").click().run()
    at.button(key="plan_go").click().run()
    for text in ("How much money do I need to open?", "100-200 guests", "No"):
        at.chat_input(key="plan_input").set_value(text).run()
    band = at.session_state["plan"]["chat"]["answers"]["investment_lakh"]["band"]
    text = html_text(at)
    assert "for the range you gave" in text and "With 100 guests/day" in text and "With 200 guests/day" in text
    assert f"≈ ₹{band['low']['value']:,.1f}–₹{band['high']['value']:,.1f} lakh" in text and not at.exception


def test_plan_switch_asks_first():
    _, t03 = reference_concepts()[2]
    at = run_page("compare", t03, [{"changes": {"book_table": "No"}}])
    at.button(key="choose_0").click().run()
    at.button(key="plan_go").click().run()
    at.chat_input(key="plan_input").set_value("How many staff do I need?").run()      # the plan now has history
    at.session_state["page"] = "compare"
    at.run()
    at.button(key="choose_1").click().run()
    at.button(key="plan_go").click().run()
    assert at.session_state["plan_switch"]["label"] == "No table booking (What-if B)"
    assert at.session_state["plan"]["label"] == "Your concept (Base)" and not at.exception  # nothing cleared yet


if __name__ == "__main__":
    tests = [test_results_match_reference, test_verdict_rules, test_step_errors, test_cuisine_total_follows_chips,
             test_pages_render, test_whatif_form_multiple_changes, test_whatif_cuisine_total_follows_chips,
             test_wizard_blocks_missing_location,
             test_plan_needs_a_selected_card, test_plan_empty_state, test_plan_chat_flow_and_summary,
             test_plan_range_answer_card, test_plan_switch_asks_first]
    for test in tests:
        test()
        print(f"✔ {test.__name__}")
    print("PASSED")
