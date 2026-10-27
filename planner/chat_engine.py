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

from plan_predict import ASSUMPTIONS, EXTRA_INPUTS, TARGETS, break_even, missing_inputs, needed_inputs, predict

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
    return {"inputs": dict(concept), "intent": None, "asking": None, "awaiting_objective": False, "history": [], "answers": {},
            "ranges": {}}  # field → (low, high) when the user gave a range, e.g. "100-200 guests"


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


TIME = r"(noon|midnight|\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.|in the morning|morning|in the evening|evening|at night|night)?)"


def clock(token: str) -> tuple[float, str | None]:
    """'5pm' → (5, 'pm'); '11 in the morning' → (11, 'am'); '7:30' → (7.5, None)."""
    token = token.strip()
    if token == "noon":
        return 12, "pm"
    if token == "midnight":
        return 12, "am"
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(.*)", token)
    hour = int(m.group(1)) + int(m.group(2) or 0) / 60
    rest = m.group(3).replace(".", "")
    part = "am" if ("am" in rest or "morning" in rest) else "pm" if any(w in rest for w in ("pm", "evening", "night")) else None
    return hour, part


def opening_hours(text: str) -> float | None:
    """Hours open from a time range, wrapping past midnight: 'from 5pm to 3am' → 10, '11 to 11' → 12."""
    m = re.search(TIME + r"\s*(?:to|till|until|-|–)\s*" + TIME, text)
    if not m:
        return None
    (h1, p1), (h2, p2) = clock(m.group(1)), clock(m.group(2))
    if h1 >= 24 or h2 >= 24:
        return None
    if h1 > 12 or h2 > 12 or (p1 is None and p2 is None and h1 >= h2):  # 24-hour clock, or "11 to 11" (morning to night)
        p1 = p1 or ("am" if h1 <= 12 else None)
        p2 = p2 or ("pm" if h2 <= 12 else None)
    to24 = lambda h, p: h % 12 + (12 if p == "pm" else 0) if p else h
    p1 = p1 or (p2 if p2 and to24(h1, p2) < to24(h2, p2) else ("am" if p2 == "pm" else "pm" if p2 else None))
    hours = (to24(h2, p2) - to24(h1, p1)) % 24
    return round(hours or 24, 1)


SHARE_WORDS = [("three quarters", 75), ("three-quarters", 75), ("half", 50), ("a third", 33), ("one third", 33),
               ("quarter", 25), ("a fifth", 20), ("a tenth", 10), ("none", 0), ("nothing", 0), ("zero", 0), ("no ", 0)]


def share_words(text: str) -> float | None:
    """'maybe a quarter delivery' → 25 (for % questions)."""
    return next((float(v) for w, v in SHARE_WORDS if w in text + " "), None)


NUM_RANGE = r"(\d+(?:\.\d+)?)\s*%?\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*"
RANGE_UNITS = {  # "100-200 guests", "10 to 14 hours", "30-40% delivery", "40-60 items", "20-30% alcohol"
    "guests_per_day": r"%?(?:guests|customers|covers|people)",
    "opening_hours": r"(?:hours|hrs|hr|h)\b",
    "delivery_share": r"%?\s*(?:percent\s*)?(?:of\s*(?:my\s*)?orders\s*)?(?:delivery|delivered)",
    "menu_items": r"(?:menu items|items|dishes)",
    "alcohol_share": r"%?\s*(?:percent\s*)?(?:of\s*(?:my\s*)?sales\s*)?(?:from\s*)?(?:alcohol|liquor|drinks|bar)",
}


def rule_ranges(text: str, asking: str | None) -> dict:
    """Ranges the user gave: {field: (low, high)}. A bare "100-200" answers the question being asked."""
    found = {f: (float(m.group(1)), float(m.group(2))) for f, unit in RANGE_UNITS.items()
             if (m := re.search(NUM_RANGE + unit, text))}
    if not found and asking in RANGE_UNITS and asking != "opening_hours" and (m := re.fullmatch(r"\D*" + NUM_RANGE + r"\D*", text)):
        found[asking] = (float(m.group(1)), float(m.group(2)))
    return found


def rule_values(message: str, asking: str | None) -> dict:
    """Values stated in free text, plus a bare answer to the question being asked. Ranges come as (low, high)."""
    text = message.lower()
    values = {f: float(m.group(1)) for f, pat in VALUE_PATTERNS.items() if (m := re.search(pat, text))}
    about_time = asking == "opening_hours" or re.search(r"\b(am|pm|open|opening|morning|evening|night|noon|midnight)\b", text)
    ranges = rule_ranges(text, asking)
    if about_time and "opening_hours" not in ranges and (hours := opening_hours(text)) is not None:
        values["opening_hours"] = hours
    values.update(ranges)
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
    elif asking in ("delivery_share", "alcohol_share") and not values and (share := share_words(text)) is not None:
        values[asking] = share
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
        if isinstance(value, (list, tuple)) and len(value) == 2 and "question" in spec:  # a range
            try:
                low_v, high_v = sorted(float(v) for v in value)
            except (TypeError, ValueError):
                continue
            low, high = spec["range"]
            if low <= low_v and high_v <= high:
                kept[field] = (low_v, high_v) if low_v < high_v else low_v
            else:
                problems.append(f"{spec['question'].split('?')[0]}? Please keep both ends between {low} and {high} {spec['unit']}.")
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


def gemini_reader(api_key: str, model: str = "gemini-3.5-flash-lite", timeout: float = 15) -> LLMReader:
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
            "For opening_hours, turn a time range into the number of hours open, wrapping past midnight "
            "(\"5pm to 3am\" = 10, \"11 in the morning till 11 at night\" = 12, \"9 to 5\" = 8).\n"
            f"Extract only values the user explicitly states, for these fields: {json.dumps(fields)}. "
            f"The assistant just asked for: {state.get('asking')}. A bare number answers that field. "
            "If the user gives a range (\"100-200 guests\", \"between 30 and 40%\"), return [low, high].\n"
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
    """(intent, values, reader used). The fast rules read first; Gemini is asked only when they find nothing
    (e.g. "maybe a quarter delivery"). Gemini output is checked; anything unexpected falls back to the rules."""
    intent = rule_intent(message, state.get("awaiting_objective", False))
    values, used = rule_values(message, state["asking"]), "rules"
    understood = intent or values or any(p in message.lower() for p in NOT_SURE)
    if llm is not None and not understood:
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


def answer_data(target: str, inputs: dict, ranges: dict | None = None) -> dict:
    """The numbers behind an answer, for drawing answer cards and the summary (same values as answer()).

    With ranges ({field: (low, high)}) that this answer uses, data["band"] also holds the answer at the low and
    at the high end of every range: {"fields": {...}, "low": data at the lows, "high": data at the highs}.
    """
    ranges = ranges or {}
    if target == "all":
        return {"targets": {t: answer_data(t, inputs, ranges) for t in TARGETS},
                "break_even": answer_data("break_even", inputs, ranges)}
    if target == "break_even":
        b = break_even(inputs)
        data = {**b, "investment": b["predictions"]["investment_lakh"]}
    else:
        r = predict(target, inputs)
        based_on = {f: inputs[f] for f in TARGETS[target]["features"] if f in EXTRA_INPUTS and f in inputs}
        data = {**r, "note": compare_with_facts(target, r["value"], inputs), "based_on": based_on}
    used = {f: rng for f, rng in ranges.items() if f in needed_inputs(target)}
    if used:
        data["band"] = {"fields": used,
                        "low": answer_data(target, {**inputs, **{f: lo for f, (lo, _) in used.items()}}),
                        "high": answer_data(target, {**inputs, **{f: hi for f, (_, hi) in used.items()}})}
    return data


def band_text(target: str, data: dict) -> str | None:
    """'With 100 guests/day: ≈ ₹45.1 lakh · with 200 guests/day: ≈ ₹51.1 lakh' for a ranged answer."""
    band = data.get("band")
    if not band:
        return None
    side = lambda end: ", ".join(typical_value(f, rng[0 if end == "low" else 1]) for f, rng in band["fields"].items())
    value = lambda d: ((f"≈ {d['months']:.0f} months" if d["months"] else "not reached") if target == "break_even"
                       else f"≈ {fmt_value(target, d['value'])}")
    return f"**Range:** with {side('low')}: {value(band['low'])} · with {side('high')}: {value(band['high'])}."


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
    data = answer_data(intent, state["inputs"], state.get("ranges"))
    answers = state.setdefault("answers", {})
    if intent == "all":
        answers.update(data["targets"], break_even=data["break_even"])
    else:
        answers[intent] = data
    state["_meta"] = {"answer": intent, "data": data}
    reply = answer(intent, state["inputs"])
    parts = data["targets"].items() if intent == "all" else [(intent, data)]
    bands = [b for t, d in [*parts, *([("break_even", data["break_even"])] if intent == "all" else [])]
             if (b := band_text(t, d))]
    if bands:
        reply = "\n\n".join([*bands, reply])
    state["intent"] = None
    return reply


def _say(state: dict, text: str, reader: str, meta: dict | None = None) -> None:
    state["history"].append({"role": "assistant", "content": text, "reader": reader, **(meta or {})})
def describe(values: dict) -> str:
    return ", ".join(f"{USER_FACTS[f]['label'] if f in USER_FACTS else f.replace('_', ' ')} {typical_value(f, v)}"
                     for f, v in values.items())


def typical_value(field: str, value) -> str:
    unit = (EXTRA_INPUTS.get(field) or USER_FACTS[field])["unit"]
    if isinstance(value, tuple):
        low, high = value
        return f"{low:g}–{high:g}%" if unit == "%" else f"{low:g}–{high:g} {unit}"
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
    for field, value in kept.items():  # a range is stored as its middle (for the models) plus its two ends
        if isinstance(value, tuple):
            state["ranges"][field] = value
            state["inputs"][field] = sum(value) / 2
        else:
            state["ranges"].pop(field, None)
            state["inputs"][field] = value
    if facts := {f: v for f, v in kept.items() if f in USER_FACTS}:
        user["facts"] = facts
    replies: list[tuple[str, dict | None]] = []

    if state["asking"] and state["asking"] not in kept and any(p in message.lower() for p in NOT_SURE):
        spec = EXTRA_INPUTS[state["asking"]]
        state["inputs"][state["asking"]] = spec["default"]
        replies.append((f"OK, I'll use a typical value: {typical(state['asking'])}.", None))
    answered = state["asking"]
    if answered in kept and not re.fullmatch(r"\s*(?:yes|no|y|n|\d+(?:\.\d+)?\s*%?)\s*", message.lower()):  # say how a worded answer was read
        replies.append((f"Got it: {typical_value(answered, kept[answered])}.", None))
    elif kept and answered not in kept and state["intent"] and not problems:  # details for a later question
        replies.append((f"Noted: {describe(kept)}.", None))
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
    elif state["asking"]:  # the range message already repeats the question: just keep its quick replies
        replies[-1] = (replies[-1][0], {"asking": state["asking"], "q_index": None, "q_total": None})

    for text, meta in replies:
        _say(state, text, used, meta)
    return [text for text, _ in replies]
