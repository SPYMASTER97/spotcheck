"""The "Plan my restaurant" chat: understands a question, asks for missing inputs, answers from the models.

Gemini (optional) only reads the user's message: it picks which question was asked and pulls out values
the user stated ("open 14 hours"). It never produces a number shown as an answer; every number comes from
plan_predict (trained models + the break-even formula). Without a key, or if Gemini fails or returns
anything unexpected, the rule-based reader below is used instead.

    state = new_state(concept)                 # concept = the main SpotCheck inputs
    replies = respond(state, "How many staff do I need?", llm=None)

Every message must lead to an objective. If a message has no clear objective (only inputs, or unclear), the chat
asks "What is your objective?" and sets state["awaiting_objective"]; the page shows the OBJECTIVES buttons
(choose_objective() when tapped). Typing still works: a message that clearly names an objective counts,
anything else asks again.
"""
import json
import re
from typing import Callable

import requests

from plan_predict import ASSUMPTIONS, EXTRA_INPUTS, TARGETS, break_even, missing_inputs, predict

INTENTS = [*TARGETS, "break_even", "all", "help"]
KEYWORDS = {  # checked in this order; first match wins
    "break_even": ["break even", "break-even", "breakeven", "payback", "pay back", "recover", "profit", "roi",
                   "worth it", "how long"],
    "food_cost_pct": ["food cost", "cogs", "ingredient", "raw material", "cost of goods"],
    "investment_lakh": ["invest", "capital", "capex", "budget", "to open", "to start", "set up", "setup",
                        "how much money", "fund", "start-up"],
    "revenue_lakh": ["revenue", "sales", "earn", "income", "turnover", "per month", "make"],
    "staff_count": ["staff", "employee", "hire", "people", "team", "headcount", "worker", "chef", "waiter"],
    "floor_area_sqft": ["area", "size", "sq ft", "sqft", "square", "space", "how big", "big", "seat"],
    "all": ["everything", "full plan", "whole plan", "all of", "summary", "overview"],
    "help": ["help", "what can you", "what do you", "options"],
}
VALUE_PATTERNS = {  # free-text values the rule-based reader understands
    "guests_per_day": r"(\d+)\s*(?:guests|customers|covers|people a day|people per day|footfall)",
    "opening_hours": r"(\d+(?:\.\d+)?)\s*(?:hours|hrs|hr|h)\b",
    "delivery_share": r"(\d+)\s*%?\s*(?:percent\s*)?(?:of\s*(?:my\s*)?orders\s*)?(?:delivery|delivered)",
    "menu_items": r"(\d+)\s*(?:menu items|items|dishes)",
    "alcohol_share": r"(\d+)\s*%?\s*(?:percent\s*)?(?:of\s*(?:my\s*)?sales\s*)?(?:from\s*)?(?:alcohol|liquor|drinks|bar)",
}
OBJECTIVES = {  # the buttons shown for "What is your objective?"
    "floor_area_sqft": "📐 Size of the place",
    "staff_count": "👥 Staff needed",
    "investment_lakh": "💰 Money to open",
    "food_cost_pct": "🥘 Food cost",
    "revenue_lakh": "📈 Monthly revenue",
    "break_even": "⏱️ Break-even",
    "all": "📋 Full plan",
}
OBJECTIVE_QUESTION = "**What is your objective?** Tap one below or type it, e.g. “staff needed”."
# Facts the user may state about what they already have. Not model inputs: only compared with the estimates.
USER_FACTS = {
    "budget_lakh": {"label": "budget", "unit": "₹ lakh", "range": (1, 5000)},
    "staff_available": {"label": "staff you have", "unit": "people", "range": (1, 500)},
}
# A message counts as asking for an estimate only with one of these (or "?"); statements like
# "I have a budget of 1 Cr" are facts, not objectives.
REQUEST_WORDS = r"\b(how|what|when|which|whats|estimate|calculate|predict|tell me|show me|give me|need|needed|should|" \
                r"expect|will|can|could|would|much|many|long|plan|want to know|find out)\b"
NOT_SURE = ("not sure", "don't know", "dont know", "no idea", "typical", "default", "skip")
SYNTHETIC_NOTE = "_Estimate from SpotCheck's synthetic planning data (Linear Regression), not real Bangalore figures._"
LLMReader = Callable[[str, dict], dict]


def new_state(concept: dict) -> dict:
    return {"inputs": dict(concept), "intent": None, "asking": None, "awaiting_objective": False, "history": [], "answers": {}}


def typical(field: str) -> str:
    spec = EXTRA_INPUTS[field]
    return f"{spec['default']}%" if spec["unit"] == "%" else f"{spec['default']} {spec['unit']}".strip()


def fmt_value(target: str, value: float) -> str:
    if target == "floor_area_sqft":
        return f"{round(value, -1):,.0f} sq ft"
    if target == "staff_count":
        return f"{max(round(value), 1)} people"
    if target == "food_cost_pct":
        return f"{value:.1f}% of sales"
    return f"₹{value:,.1f} lakh"


def fmt_range(target: str, low: float, high: float) -> str:
    low_text, high_text = fmt_value(target, low), fmt_value(target, high)
    unit = high_text.split(" ", 1)[1] if " " in high_text else ""
    return f"{low_text.removesuffix(' ' + unit)}–{high_text}" if unit and low_text.endswith(unit) else f"{low_text}–{high_text}"


def rupees(amount: float) -> str:
    return f"₹{amount / 100_000:,.1f} lakh"


# ---------- reading the message ----------

def is_request(message: str) -> bool:
    return "?" in message or re.search(REQUEST_WORDS, message.lower()) is not None


def rule_intent(message: str, awaiting_objective: bool = False) -> str | None:
    """The objective a message asks for. Mentioning a topic is not enough unless the chat asked for an objective."""
    text = message.lower()
    if not (awaiting_objective or is_request(message)):
        return None
    for intent, words in KEYWORDS.items():
        if any(w in text for w in words):
            return intent
    return None


def rule_values(message: str, asking: str | None) -> dict:
    """Values stated in free text, plus a bare answer to the question being asked."""
    text = message.lower()
    values = {f: float(m.group(1)) for f, pat in VALUE_PATTERNS.items() if (m := re.search(pat, text))}
    if m := re.search(r"(\d+(?:\.\d+)?)\s*(cr|crore)s?\b", text):
        values["budget_lakh"] = float(m.group(1)) * 100
    elif (m := re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)\b", text)) and re.search(r"budget|invest|capital|fund|have", text):
        values["budget_lakh"] = float(m.group(1))
    if m := re.search(r"(\d+)\s*(?:staff|employees|members|team members|workers)", text):
        values["staff_available"] = float(m.group(1))
    if re.search(r"take over|takeover|taking over|existing (?:restaurant|site|place)", text):
        values["takeover"] = "Yes"
    if asking == "takeover":
        if re.search(r"\b(yes|yeah|yep|y)\b", text):
            values["takeover"] = "Yes"
        elif re.search(r"\b(no|nope|new|n)\b", text):
            values["takeover"] = "No"
    elif asking and not values and (m := re.search(r"(\d+(?:\.\d+)?)", text)):  # a bare number answers the question
        values[asking] = float(m.group(1))
    return values


def valid_values(values: dict) -> tuple[dict, list[str]]:
    """Keep only known fields within range; return the kept values and messages about rejected ones."""
    kept, problems = {}, []
    for field, value in values.items():
        spec = EXTRA_INPUTS.get(field) or USER_FACTS.get(field)
        if spec is None:
            continue
        if "options" in spec:
            if value in spec["options"]:
                kept[field] = value
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        low, high = spec["range"]
        if low <= number <= high:
            kept[field] = number
        else:
            what = spec["question"].split("?")[0] + "?" if "question" in spec else f"Your {spec['label']}:"
            problems.append(f"{what} Please give a value between {low} and {high} {spec['unit']}.")
    return kept, problems


def gemini_reader(api_key: str, model: str = "gemini-3.5-flash-lite", timeout: float = 8) -> LLMReader:
    """Gemini as a message reader only. Returns {"intent": ..., "values": {...}}; raises on any failure."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    fields = {f: (s.get("options") or f"number {s['range'][0]}-{s['range'][1]} {s['unit']}") for f, s in
              {**EXTRA_INPUTS, **USER_FACTS}.items()}

    def read(message: str, state: dict) -> dict:
        prompt = (
            "You classify one message sent to a restaurant-planning assistant. Do NOT answer it and do NOT "
            "estimate anything.\n"
            f"Allowed intents: {INTENTS} (floor_area_sqft = size of the place, staff_count = employees, "
            "investment_lakh = money needed to open, food_cost_pct = ingredient cost/COGS, revenue_lakh = monthly "
            "sales, break_even = payback/profit timing, all = full plan, help = what can you do).\n"
            "Set intent ONLY if the user asks for that estimate (a question or request), or names it as their objective "
            f"when the assistant is waiting for one (waiting now: {bool(state.get('awaiting_objective'))}). "
            "Statements about what the user already has (\"I have 1 Cr\", \"I have 20 staff\") are NOT intents: "
            "use null and extract them as budget_lakh / staff_available (1 crore = 100 lakh).\n"
            f"Extract only values the user explicitly states, for these fields: {json.dumps(fields)}. "
            f"The assistant just asked for: {state.get('asking')}. A bare number answers that field.\n"
            'Reply with JSON only: {"intent": <intent or null>, "values": {<field>: <value>}}\n'
            f"Message: {message!r}"
        )
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}
        r = requests.post(url, json=body, headers={"x-goog-api-key": api_key}, timeout=timeout)
        r.raise_for_status()
        return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])

    return read


def read_message(message: str, state: dict, llm: LLMReader | None) -> tuple[str | None, dict, str]:
    """(intent, values, reader used). Gemini output is checked; anything unexpected falls back to the rules."""
    intent = rule_intent(message, state.get("awaiting_objective", False))
    values, used = rule_values(message, state["asking"]), "rules"
    if llm is not None:
        try:
            out = llm(message, state)
            llm_intent = out.get("intent")
            llm_values = out.get("values") or {}
            if llm_intent is not None and llm_intent not in INTENTS:
                raise ValueError(f"unknown intent {llm_intent!r}")
            if not isinstance(llm_values, dict):
                raise ValueError("values is not an object")
            intent = llm_intent  # Gemini read the whole sentence; trust its "no objective" too
            values = {**values, **{k: v for k, v in llm_values.items() if k in EXTRA_INPUTS or k in USER_FACTS}}
            used = "gemini"
        except Exception:  # noqa: BLE001 – any Gemini problem means: use the rule-based reading
            used = "rules (Gemini unavailable)"
    return intent, values, used


# ---------- answering ----------

def answer(target: str, inputs: dict) -> str:
    if target == "all":
        return "\n\n".join(answer(t, inputs) for t in [*TARGETS, "break_even"])
    if target == "break_even":
        b = break_even(inputs)
        c = b["costs"]
        lines = [f"**Break-even: about {b['months']:.0f} months**" if b["months"] else
                 "**Break-even: not reached under these assumptions** (monthly costs exceed sales)."]
        lines.append(f"Monthly sales {rupees(b['revenue'])} − food {rupees(c['food'])} − staff {rupees(c['staff'])} − "
                     f"rent {rupees(c['rent'])} − other costs {rupees(c['other'])} = profit {rupees(b['profit'])} a month; "
                     f"investment {fmt_value('investment_lakh', b['predictions']['investment_lakh'])}.")
        lines.append(f"Assumptions (not models): ₹{ASSUMPTIONS['salary_per_staff']:,} per staff member a month, "
                     f"rent ₹{ASSUMPTIONS['base_rent_per_sqft']}/sq ft in a typical area (scaled by area price level), "
                     f"other costs {ASSUMPTIONS['other_costs_pct']}% of sales.")
        return "\n\n".join([*lines, SYNTHETIC_NOTE])
    r = predict(target, inputs)
    spec = TARGETS[target]
    note = compare_with_facts(target, r["value"], inputs)
    used = ", ".join(f"{f.replace('_', ' ')} {inputs[f]:g}" if isinstance(inputs[f], float) else
                     f"{f.replace('_', ' ')} {inputs[f]}" for f in spec["features"] if f in EXTRA_INPUTS and f in inputs)
    return (f"**{spec['label']}: about {fmt_value(target, r['value'])}** "
            f"(typical range {fmt_range(target, r['low'], r['high'])}).\n\n"
            f"Based on your concept ({inputs['primary_type']}, {inputs['location']}, ₹{inputs['cost_for_two']:,.0f} for two)"
            + (f" and {used}." if used else ".") + (f"\n\n{note}" if note else "") + f"\n\n{SYNTHETIC_NOTE}")


def compare_with_facts(target: str, value: float, inputs: dict) -> str | None:
    """Compare an estimate with what the user said they have (budget, staff)."""
    if target == "investment_lakh" and inputs.get("budget_lakh"):
        gap = inputs["budget_lakh"] - value
        return (f"Your budget of ₹{inputs['budget_lakh']:g} lakh covers this, with about ₹{gap:,.1f} lakh to spare."
                if gap >= 0 else f"Your budget of ₹{inputs['budget_lakh']:g} lakh is about ₹{-gap:,.1f} lakh short.")
    if target == "staff_count" and inputs.get("staff_available"):
        gap = round(inputs["staff_available"]) - max(round(value), 1)
        return ("You have exactly the staff this needs." if gap == 0 else
                f"You have {round(inputs['staff_available'])} people: about {abs(gap)} "
                + ("more than needed." if gap > 0 else "short."))
    return None


def answer_data(target: str, inputs: dict) -> dict:
    """The numbers behind an answer, for drawing answer cards and the summary (same values as answer())."""
    if target == "all":
        return {"targets": {t: answer_data(t, inputs) for t in TARGETS}, "break_even": answer_data("break_even", inputs)}
    if target == "break_even":
        b = break_even(inputs)
        return {**b, "investment": b["predictions"]["investment_lakh"]}
    r = predict(target, inputs)
    based_on = {f: inputs[f] for f in TARGETS[target]["features"] if f in EXTRA_INPUTS and f in inputs}
    return {**r, "note": compare_with_facts(target, r["value"], inputs), "based_on": based_on}


def start_objective(state: dict, objective: str) -> None:
    state["intent"], state["awaiting_objective"] = objective, False
    state["q_total"] = len(missing_inputs("break_even" if objective == "all" else objective, state["inputs"]))


def ask_next(state: dict) -> str | None:
    """Ask for the next missing input of the current question, or answer it if nothing is missing.

    Sets state["_meta"] for the reply: {"asking", "q_index", "q_total"} or {"answer", "data"}.
    """
    intent = state["intent"]
    missing = missing_inputs("break_even" if intent == "all" else intent, state["inputs"])
    if missing:
        state["asking"] = missing[0]
        total = max(state.get("q_total", 0), len(missing))
        state["_meta"] = {"asking": missing[0], "q_index": total - len(missing) + 1, "q_total": total}
        spec = EXTRA_INPUTS[missing[0]]
        return f"{spec['question']} _(Say “not sure” to use a typical value: {typical(missing[0])}.)_"
    state["asking"] = None
    data = answer_data(intent, state["inputs"])
    answers = state.setdefault("answers", {})
    if intent == "all":
        answers.update(data["targets"], break_even=data["break_even"])
    else:
        answers[intent] = data
    state["_meta"] = {"answer": intent, "data": data}
    reply = answer(intent, state["inputs"])
    state["intent"] = None
    return reply


def _say(state: dict, text: str, reader: str, meta: dict | None = None) -> None:
    state["history"].append({"role": "assistant", "content": text, "reader": reader, **(meta or {})})
def describe(values: dict) -> str:
    return ", ".join(f"{USER_FACTS[f]['label'] if f in USER_FACTS else f.replace('_', ' ')} {typical_value(f, v)}"
                     for f, v in values.items())


def typical_value(field: str, value) -> str:
    unit = (EXTRA_INPUTS.get(field) or USER_FACTS[field])["unit"]
    if unit == "₹ lakh":
        return f"₹{value:g} lakh"
    if isinstance(value, str):
        return value
    return f"{value:g}%" if unit == "%" else f"{value:g} {unit}"


def choose_objective(state: dict, objective: str) -> list[str]:
    """The user tapped an objective button."""
    if objective not in OBJECTIVES:
        raise ValueError(f"unknown objective {objective!r}")
    state["history"].append({"role": "user", "content": f"Objective: {OBJECTIVES[objective]}", "objective": objective})
    start_objective(state, objective)
    reply = ask_next(state)
    _say(state, reply, "button", state.pop("_meta", None))
    return [reply]


def respond(state: dict, message: str, llm: LLMReader | None = None) -> list[str]:
    user = {"role": "user", "content": message}
    state["history"].append(user)
    intent, values, used = read_message(message, state, llm)
    kept, problems = valid_values(values)
    state["inputs"].update(kept)
    if facts := {f: v for f, v in kept.items() if f in USER_FACTS}:
        user["facts"] = facts
    replies: list[tuple[str, dict | None]] = []

    if state["asking"] and state["asking"] not in kept and any(p in message.lower() for p in NOT_SURE):
        spec = EXTRA_INPUTS[state["asking"]]
        state["inputs"][state["asking"]] = spec["default"]
        replies.append((f"OK, I'll use a typical value: {typical(state['asking'])}.", None))
    if problems:
        replies += [(p, None) for p in problems]
    elif intent in OBJECTIVES and intent != state["intent"] and not (state["asking"] and kept):
        start_objective(state, intent)  # a new question (an answer to the current question keeps the current one)

    if state["intent"] is None:  # no objective yet: note any inputs, then the user must pick one
        state["awaiting_objective"] = True
        replies.append(((f"Noted: {describe(kept)}. " if kept else "") + OBJECTIVE_QUESTION, {"objective_question": True}))
    elif not problems:
        text = ask_next(state)
        replies.append((text, state.pop("_meta", None)))
    elif state["asking"]:
        spec = EXTRA_INPUTS[state["asking"]]
        replies.append((spec["question"], {"asking": state["asking"], "q_index": None, "q_total": None}))

    for text, meta in replies:
        _say(state, text, used, meta)
    return [text for text, _ in replies]
