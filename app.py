"""SpotCheck – restaurant concept check for Bangalore (Streamlit, mobile-first).

A 4-step wizard (Where → Format → Menu → Price) feeds the two trained models through
predict.py; the app adds no model logic of its own. Results, what-if comparison,
a take-away summary and an About page follow. No login, nothing stored on a server.

Plan: pick a card in Compare → "Plan this concept" → a chat answers opening questions (size, staff,
investment, food cost, revenue, break-even) from the planner models in planner/ (SYNTHETIC data,
labelled as such). Gemini, if a key is set (GEMINI_API_KEY in Streamlit secrets), only reads the
user's message; every number comes from the models.

Run locally:  streamlit run app.py
Design: design/stitch_DESIGN.md and design/plan_export/ (Stitch exports), Zomato-style red; not affiliated with Zomato.
"""
import datetime as dt
import html
import os
import re
import sys
from pathlib import Path

import streamlit as st

from predict import ALLOWED, CUISINE_FLAGS, RANGES, predict_price, predict_rating, validate_inputs

sys.path.insert(0, str(Path(__file__).resolve().parent / "planner"))
from chat_engine import (OBJECTIVES, USER_FACTS, choose_objective, fmt_range, fmt_value,  # noqa: E402
                         gemini_reader, new_state as new_chat, respond, typical)
from plan_predict import ASSUMPTIONS, EXTRA_INPUTS, TARGETS  # noqa: E402

PRICE_BAND = 136            # ± typical error of the price model: Random Forest 10-fold CV MAE ₹136.4
STRONG, MODERATE = 0.60, 0.30   # rating verdicts, same thresholds as the workbook's 'Reference Tests' sheet
MAX_WHATIFS = 3             # what-if cards on top of the base concept
SLIDER_MIN, SLIDER_MAX, SLIDER_STEP = 100, 3000, 50

STEPS = ["Where", "Format", "Menu", "Price"]
POPULAR_AREAS = ["Koramangala 5th Block", "Indiranagar", "HSR", "Whitefield", "JP Nagar", "BTM",
                 "Jayanagar", "MG Road", "Marathahalli", "Bellandur", "Other"]
TYPE_EMOJI = {
    "Quick Bites": "🍔", "Casual Dining": "🍽️", "Cafe": "☕", "Delivery": "🛵", "Dessert Parlor": "🍨",
    "Bakery": "🥐", "Bar": "🍸", "Beverage Shop": "🧃", "Takeaway": "🥡", "Sweet Shop": "🍬",
    "Food Court": "🏬", "Other": "✨",
}
CUISINE_EMOJI = {
    "c_North_Indian": "🍛", "c_Chinese": "🥢", "c_South_Indian": "🥥", "c_Fast_Food": "🍟",
    "c_Biryani": "🍚", "c_Desserts": "🍰", "c_Beverages": "🥤", "c_Continental": "🥗",
    "c_Cafe": "☕", "c_Street_Food": "🌮", "c_Italian": "🍕", "c_Bakery": "🥐",
}
SERVICES = [  # (field, emoji, label, hint)
    ("has_bar", "🍷", "Serves alcohol", "Bar, pub or lounge licence"),
    ("online_order", "📱", "Online ordering", "Delivery apps or your own site"),
    ("book_table", "📅", "Table booking", "Guests can reserve a table"),
]
SHORT = {"has_bar": "alcohol", "online_order": "online ordering", "book_table": "table booking"}  # for chips and titles
TONES = {  # badge background, text colour
    "green": ("#EAF7EE", "#24963F"), "amber": ("#FEF8EC", "#A86A00"),
    "blue": ("#EFF6FF", "#2563EB"), "red": ("#FDECEE", "#C81E2C"),
}
KEEP_IN_MIND = [
    "Ratings also depend on food, service and hygiene – the models can't see these.",
    "Based on 9,244 Bangalore restaurants (Kaggle data, about 2019).",
    "Shows patterns in existing restaurants, not cause and effect.",
]
FOOTER = "Estimates, not guarantees · Trained on 9,244 Bangalore restaurants · Not affiliated with Zomato"
PLAN_ICON = {"floor_area_sqft": "📐", "staff_count": "👥", "investment_lakh": "💰", "food_cost_pct": "🥘",
             "revenue_lakh": "📈", "break_even": "⏱️", "all": "📋"}
QUICK_REPLIES = {  # tap-to-answer chips for the chat's follow-up questions (typing also works)
    "guests_per_day": ["80", "120", "150", "200"], "opening_hours": ["10", "12", "14", "16"],
    "delivery_share": ["0%", "20%", "40%", "60%"], "menu_items": ["25", "45", "70", "100"],
    "alcohol_share": ["15%", "30%", "45%"], "takeover": ["Yes", "No"],
}
SYNTHETIC_LINE = "Estimate from synthetic planning data (Linear Regression)"


# ---------------------------------------------------------------- logic (no Streamlit calls)
def rupees(x: float) -> str:
    return f"₹{x:,.0f}"


CUISINE_LABEL = {"c_Cafe": "Coffee"}  # display name only; the model column stays c_Cafe (avoids clashing with the Cafe type)


def cuisine_name(flag: str) -> str:
    return CUISINE_LABEL.get(flag, flag[2:].replace("_", " "))


def new_concept() -> dict:
    return {"location": None, "primary_type": None, "has_bar": "No", "online_order": "No",
            "book_table": "No", "cuisines": [], "n_cuisines": 0, "cost_for_two": 500}  # 0 until a cuisine is picked


def to_inputs(concept: dict) -> dict:
    """Concept (as the user entered it) → the input dict predict.py expects."""
    inputs = {k: concept[k] for k in ("location", "primary_type", "has_bar", "online_order", "book_table",
                                       "n_cuisines", "cost_for_two")}
    inputs.update({c: "Yes" if c in concept["cuisines"] else "No" for c in CUISINE_FLAGS})
    return inputs


def price_verdict(price: float, cost: float) -> tuple[str, str, str]:
    low, high = price - PRICE_BAND, price + PRICE_BAND
    if cost > high:
        return "Above market", "amber", f"Your {rupees(cost)} is above the usual top of {rupees(high)}."
    if cost < low:
        return "Below market", "blue", f"Your {rupees(cost)} is below the usual bottom of {rupees(low)}."
    return "In line with market", "green", f"Your {rupees(cost)} sits within the usual range."


def rating_verdict(prob: float) -> tuple[str, str, str]:
    if prob >= STRONG:
        return "Strong", "green", "Most places with this profile are rated 4.0 or higher."
    if prob >= MODERATE:
        return "Moderate", "amber", "A fair share of places like this reach 4.0+."
    return "Weak", "red", "Few places with this profile reach 4.0+."


def assess(inputs: dict) -> dict:
    """Both model outputs plus verdicts for one set of inputs."""
    price = predict_price(inputs)
    prob = predict_rating(inputs)
    cost = float(inputs["cost_for_two"])
    return {"price": price, "low": price - PRICE_BAND, "high": price + PRICE_BAND, "prob": prob, "cost": cost,
            "price_verdict": price_verdict(price, cost), "rating_verdict": rating_verdict(prob)}


CONCEPT_FIELDS = ["location", "primary_type", "has_bar", "online_order", "book_table", "cuisines", "n_cuisines",
                  "cost_for_two"]


def describe_change(field: str, old, new) -> tuple[str, str]:
    """(card title if this is the only change, 'what changed' text) for one setting of a what-if."""
    if field == "cost_for_two":
        return ("Higher price" if new > old else "Lower price"), f"💰 {rupees(old)} → {rupees(new)}"
    if field == "location":
        return new, f"📍 {old} → {new}"
    if field == "primary_type":
        return f"As a {new}", f"{TYPE_EMOJI[new]} {old} → {new}"
    if field == "cuisines":
        names = lambda cs: ", ".join(cuisine_name(x) for x in cs) or "none"
        return "Different menu", f"🍽️ Cuisines: {names(old)} → {names(new)}"
    if field == "n_cuisines":
        return ("More cuisines" if new > old else "Fewer cuisines"), f"🔢 Total cuisines: {old} → {new}"
    emoji, label = next((e, l) for f, e, l, _ in SERVICES if f == field)
    title = f"No {SHORT[field]}" if new == "No" else f"With {SHORT[field]}"
    return title, f"{emoji} {label}: {old} → {new}"


def diff(concept: dict, other: dict) -> dict:
    """Settings in `other` that differ from `concept` (cuisine order ignored)."""
    same = lambda f: sorted(concept[f]) == sorted(other[f]) if f == "cuisines" else concept[f] == other[f]
    return {f: other[f] for f in CONCEPT_FIELDS if not same(f)}


def step_error(step: int, concept: dict) -> str | None:
    """Friendly message if a wizard step can't be completed yet."""
    if step == 1 and not concept["location"]:
        return "Pick an area to continue. Choose “Other area” if yours isn't listed."
    if step == 2 and not concept["primary_type"]:
        return "Pick the kind of place to continue."
    if step == 3 and concept["n_cuisines"] < RANGES["n_cuisines"][0]:
        return "Pick at least one cuisine, or press + if yours isn't in the list."
    if step == 3 and len(concept["cuisines"]) > RANGES["n_cuisines"][1]:
        return (f"Pick at most {RANGES['n_cuisines'][1]} main cuisines – that's the most any restaurant "
                "in our data had.")
    if step == 3 and len(concept["cuisines"]) > concept["n_cuisines"]:
        n, total = len(concept["cuisines"]), concept["n_cuisines"]
        return f"You picked {n} cuisines but the total says {total}. Make the total at least {n}."
    if step == 4:
        problems = validate_inputs(to_inputs(concept), need_cost=True)
        return " ".join(problems) if problems else None
    return None


# ---------------------------------------------------------------- HTML pieces
def clean(markup: str) -> str:
    """Strip indentation so Streamlit never treats the HTML as a code block."""
    return " ".join(line.strip() for line in markup.splitlines() if line.strip())


def badge(text: str, tone: str) -> str:
    bg, fg = TONES[tone]
    return f'<span class="sc-badge" style="background:{bg};color:{fg};border-color:{fg}">{html.escape(text)}</span>'


def chips(items: list[str]) -> str:
    return '<div class="sc-chips">' + "".join(f'<span class="sc-chip">{html.escape(i)}</span>' for i in items) + "</div>"


def concept_chips(c: dict) -> list[str]:
    items = [f"📍 {c['location']}", f"{TYPE_EMOJI[c['primary_type']]} {c['primary_type']}"]
    items += [f"{e} {l}" if c[f] == "Yes" else f"🚫 No {SHORT[f]}" for f, e, l, _ in SERVICES]
    if c["cuisines"]:
        items.append("".join(CUISINE_EMOJI[x] for x in c["cuisines"]) + f" {len(c['cuisines'])} main cuisines")
    items += [f"{c['n_cuisines']} cuisines in total", f"💰 {rupees(c['cost_for_two'])} for two"]
    return items


def range_bar(res: dict) -> str:
    """Typical range as a band, the estimate as a dot and the user's price as a marker."""
    lo, hi, cost = res["low"], res["high"], res["cost"]
    smin, smax = min(lo, cost), max(hi, cost)
    pad = 0.15 * (smax - smin) + 1
    smin, smax = smin - pad, smax + pad
    pos = lambda x: (x - smin) / (smax - smin) * 100
    fg = TONES[res["price_verdict"][1]][1]
    return clean(f"""
    <div class="sc-range">
      <div class="sc-range-track"></div>
      <div class="sc-range-band" style="left:{pos(lo):.1f}%;width:{pos(hi) - pos(lo):.1f}%"></div>
      <div class="sc-range-dot" style="left:{pos(res['price']):.1f}%"></div>
      <div class="sc-range-you" style="left:{pos(cost):.1f}%;background:{fg}"></div>
      <div class="sc-range-youlabel" style="left:{pos(cost):.1f}%;color:{fg}">You {rupees(cost)}</div>
    </div>
    <div class="sc-muted sc-center">Typical range {rupees(lo)} – {rupees(hi)} · estimate {rupees(res['price'])}</div>""")


def price_card(res: dict) -> str:
    label, tone, sentence = res["price_verdict"]
    return clean(f"""
    <div class="sc-card">
      <div class="sc-card-head"><span class="sc-h3">💰 Price check</span>{badge("Main result", "red")}</div>
      <div class="sc-big">{rupees(res['price'])}<span class="sc-unit"> for two</span></div>
      <div class="sc-muted">Typical market price at places like yours</div>
      {range_bar(res)}
      <div class="sc-verdict" style="background:{TONES[tone][0]}">{badge(label, tone)}<div>{html.escape(sentence)}</div></div>
    </div>""")


def rating_badge(prob: float, tone: str, size: str = "") -> str:
    bg = TONES[tone][1]
    return f'<span class="sc-rating {size}" style="background:{bg}">{prob:.0%}<small> ★4.0+</small></span>'


def rating_card(res: dict) -> str:
    label, tone, sentence = res["rating_verdict"]
    fg = TONES[tone][1]
    return clean(f"""
    <div class="sc-card">
      <div class="sc-card-head"><span class="sc-h3">⭐ Rating outlook</span></div>
      <div class="sc-row">{rating_badge(res['prob'], tone, 'sc-rating-lg')}
        <div><div style="color:{fg};font-weight:700">{label}</div>
        <div>chance of a 4.0+ rating for places like yours</div></div></div>
      <div class="sc-inset">{html.escape(sentence)}
        <div class="sc-meter"><div style="width:{res['prob'] * 100:.0f}%;background:{fg}"></div></div></div>
      <div class="sc-legend"><span style="color:{TONES['green'][1]}">● Strong 60%+</span>
        <span style="color:{TONES['amber'][1]}">● Moderate 30–59%</span>
        <span style="color:{TONES['red'][1]}">● Weak &lt;30%</span></div>
    </div>""")


def scenario_card(sc: dict, selection: str = "") -> str:
    """selection: "" (nothing picked yet), "selected" or "faded" (another card is picked)."""
    res = sc["result"]
    label, tone, _ = res["price_verdict"]
    r_label, r_tone, _ = res["rating_verdict"]
    tags = (badge(sc['tag'], "red") if sc['tag'] else "") + (badge("Selected", "red") if selection == "selected" else "")
    return clean(f"""
    <div class="sc-card-body {'sc-faded' if selection == 'faded' else ''}">
      <div class="sc-card-head"><span class="sc-h3">{html.escape(sc['title'])} {tags}</span></div>
      <div class="sc-kv"><span>Market price</span><b>{rupees(res['price'])}</b></div>
      <div class="sc-kv sc-muted"><span>Typical range</span><span>{rupees(res['low'])} – {rupees(res['high'])}</span></div>
      <div class="sc-kv"><span>Your price</span><b>{rupees(res['cost'])}</b></div>
      <div class="sc-kv"><span>Price verdict</span>{badge(label, tone)}</div>
      <div class="sc-kv"><span>Chance of 4.0+</span>{rating_badge(res['prob'], r_tone)}</div>
      <div class="sc-kv"><span>Rating outlook</span><b style="color:{TONES[r_tone][1]}">{r_label}</b></div>
      <details class="sc-details"><summary>All settings</summary>{chips(concept_chips(sc['concept']))}</details>
    </div>""")


def scenarios(concept: dict, whatifs: list[dict]) -> list[dict]:
    """Title, tag, change lines, full settings and model result for the base concept and each what-if.

    A what-if is {"changes": {setting: new value, ...}} relative to the base concept.
    """
    out = [{"title": "Your concept", "tag": "Base", "changes": [], "concept": concept,
            "result": assess(to_inputs(concept))}]
    for i, w in enumerate(whatifs):
        changed = {**concept, **w["changes"]}
        described = [describe_change(f, concept[f], v) for f, v in w["changes"].items()]
        title = described[0][0] if len(described) == 1 else f"What-if {chr(66 + i)}"
        out.append({"title": title, "tag": "", "changes": [d[1] for d in described], "concept": changed,
                    "result": assess(to_inputs(changed))})
    return out


def scenario_label(rows: list[dict], i: int) -> str:
    """'No table booking (What-if B)'; a card already titled 'What-if B' isn't repeated."""
    title, tag = rows[i]["title"], "Base" if i == 0 else f"What-if {chr(65 + i)}"
    return title if title == tag else f"{title} ({tag})"


def facts_text(inputs: dict) -> str:
    parts = []
    if inputs.get("budget_lakh"):
        parts.append(f"budget ₹{inputs['budget_lakh']:g} lakh")
    if inputs.get("staff_available"):
        parts.append(f"{inputs['staff_available']:g} staff")
    return " · ".join(parts)


def plan_summary_html(plan: dict | None) -> str:
    """The 'My opening plan' section: every answered estimate, the user's stated facts and the data note."""
    answers = plan["chat"]["answers"] if plan else {}
    if not answers:
        return ""
    rows = "".join(f"<tr><td>{PLAN_ICON[t]} {html.escape(TARGETS[t]['label'])}</td>"
                   + (f"<td><b>{band_span(t, answers[t])}</b> <span class='sc-small'>(for your range)</span></td></tr>"
                      if answers[t].get("band") else
                      f"<td><b>≈ {fmt_value(t, answers[t]['value'])}</b>"
                      f" <span class='sc-small'>({fmt_range(t, answers[t]['low'], answers[t]['high'])})</span></td></tr>")
                   for t in TARGETS if t in answers)
    if "break_even" in answers:
        months = answers["break_even"]["months"]
        shown = (band_span("break_even", answers["break_even"]) if answers["break_even"].get("band")
                 else f'≈ {months:.0f} months' if months else 'Not reached')
        rows += (f"<tr><td>⏱️ Break-even</td><td><b>{shown}</b>"
                 f" <span class='sc-small'>(formula on the estimates above)</span></td></tr>")
    facts = facts_text(plan["chat"]["inputs"])
    return clean(f"""
      <h3>📋 My opening plan · {html.escape(plan['label'])}</h3>
      {f'<p class="sc-small">Your facts: {html.escape(facts)}</p>' if facts else ''}
      <table>{rows}</table>
      <p class="sc-small">Plan estimates come from synthetic planning data (Linear Regression); price and rating
      come from 9,244 real Zomato Bangalore restaurants.</p>""")


def summary_html(concept: dict, whatifs: list[dict], plan: dict | None = None) -> str:
    rows = scenarios(concept, whatifs)
    res = rows[0]["result"]
    cuisines = ", ".join(cuisine_name(c) for c in concept["cuisines"]) or "none of the 12 listed"
    services = " · ".join(f"{e} {l}: {concept[f]}" for f, e, l, _ in SERVICES)
    whatif_rows = "".join(
        f"<tr><td>{chr(65 + i)} {html.escape(sc['title'])}"
        + "".join(f'<div class="sc-small">{html.escape(line)}</div>' for line in sc["changes"])
        + f"</td><td>{rupees(sc['result']['price'])}</td><td>{sc['result']['price_verdict'][0]}</td>"
        f"<td>{sc['result']['prob']:.0%}</td></tr>" for i, sc in enumerate(rows))
    keep = "".join(f"<li>{html.escape(k)}</li>" for k in KEEP_IN_MIND)
    return clean(f"""
    <div class="sc-summary">
      <h2>📍🍽️ SpotCheck – concept summary</h2>
      <p class="sc-muted">{dt.date.today():%d %b %Y} · Nothing is saved online. Download this summary to keep it.</p>
      <h3>Your concept</h3>
      <p>📍 {html.escape(concept['location'])} · {TYPE_EMOJI[concept['primary_type']]} {html.escape(concept['primary_type'])}<br>
      {services}<br>Main cuisines: {html.escape(cuisines)} · {concept['n_cuisines']} cuisines in total<br>
      💰 Planned {rupees(concept['cost_for_two'])} for two</p>
      <h3>Results</h3>
      <p>Typical market price <b>{rupees(res['price'])}</b> (range {rupees(res['low'])} – {rupees(res['high'])}) –
      <b>{res['price_verdict'][0]}</b>.<br>Chance of a 4.0+ rating <b>{res['prob']:.0%}</b> – <b>{res['rating_verdict'][0]}</b>.</p>
      <h3>What-ifs</h3>
      <table><tr><th>Scenario</th><th>Market price</th><th>Price verdict</th><th>4.0+ chance</th></tr>{whatif_rows}</table>
      {plan_summary_html(plan)}
      <h3>Keep in mind</h3><ul>{keep}</ul>
      <p class="sc-small">Data: 'Zomato Bangalore Restaurants' by Himanshu Poddar, Kaggle (about 2019).
      Models: Random Forest (price), Logistic Regression (rating). SpotCheck – MICA ML Capstone. Not affiliated with Zomato.</p>
    </div>""")


# ---------------------------------------------------------------- Plan chat pieces
def md_inline(text: str) -> str:
    """The chat engine's tiny markdown (**bold**, _italic_, line breaks) → safe HTML."""
    out = html.escape(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"(?<![\w])_(.+?)_(?![\w])", r"<i>\1</i>", out)
    return out.replace("\n\n", "<br><br>")


def input_text(field: str, value) -> str:
    """'150 guests/day' style text for a planner input the user gave."""
    unit = {"guests_per_day": " guests/day", "opening_hours": " h/day", "delivery_share": "% delivery",
            "menu_items": " menu items", "alcohol_share": "% alcohol sales"}.get(field)
    if field == "takeover":
        return "Taking over a site" if value == "Yes" else "New fit-out"
    if isinstance(value, tuple):  # a range the user gave
        return f"{value[0]:g}–{value[1]:g}{unit}"
    return f"{value:g}{unit}"


def bubble(role: str, body: str, extra: str = "") -> str:
    if role == "user":
        return f'<div class="sc-msg sc-msg-user"><div class="sc-bubble-user">{body}</div>{extra}</div>'
    return f'<div class="sc-msg"><span class="sc-avatar">🍽️</span><div class="sc-bubble-bot">{body}</div></div>{extra}'


def mini_range(low: float, value: float, high: float, target: str) -> str:
    return clean(f"""<div class="sc-mini-range"><div class="sc-mini-track"><div class="sc-mini-dot"></div></div>
        <div class="sc-kv sc-small" style="border:0;padding:2px 0"><span>{fmt_value(target, low)}</span>
        <span>{fmt_value(target, high)}</span></div></div>""")


def band_value(target: str, d: dict) -> str:
    if target == "break_even":
        return f"≈ {d['months']:.0f} months" if d["months"] else "not reached"
    return f"≈ {fmt_value(target, d['value'])}"


def band_span(target: str, data: dict) -> str:
    """'≈ ₹47.4–₹53.1 lakh' across a ranged answer's two ends (low end first)."""
    lo, hi = data["band"]["low"], data["band"]["high"]
    if target == "break_even":
        months = sorted(m for m in (lo["months"], hi["months"]) if m)
        return f"≈ {months[0]:.0f}–{months[-1]:.0f} months" if months else "Not reached"
    a, b = sorted((lo["value"], hi["value"]))
    return f"≈ {fmt_range(target, a, b)}"


def band_rows(target: str, data: dict) -> str:
    """'With 100 guests/day → ≈ ₹47.4 lakh' for each end of the user's range(s)."""
    band = data["band"]
    side = lambda end: ", ".join(input_text(f, rng[0 if end == "low" else 1]) for f, rng in band["fields"].items())
    return "".join(f'<div class="sc-kv"><span>With {html.escape(side(end))}</span><b>{band_value(target, band[end])}</b></div>'
                   for end in ("low", "high"))


def answer_card(target: str, data: dict, concept: dict) -> str:
    """Stitch 'answer card': big estimate, range, comparison with the user's facts, inputs used, data label."""
    if target == "all":
        return full_plan_card(data, concept)
    if target == "break_even":
        return break_even_card(data)
    note = data.get("note")
    note_html = ""
    if note:
        good = "covers" in note or "more than needed" in note or "exactly" in note
        note_html = f'<div class="sc-verdict" style="background:{TONES["green" if good else "amber"][0]}">{"✓" if good else "⚠️"} {html.escape(note)}</div>'
    based = [concept["primary_type"], concept["location"], f"{rupees(concept['cost_for_two'])} for two"]
    ranged = data.get("band", {}).get("fields", {})
    based += [input_text(f, ranged.get(f, v)) for f, v in data["based_on"].items()]
    return clean(f"""
    <div class="sc-answer">
      <div class="sc-card-head"><span class="sc-h3">{PLAN_ICON[target]} {html.escape(TARGETS[target]['label'])}</span></div>
      {f'<div class="sc-answer-big">{band_span(target, data)}</div><div class="sc-small">for the range you gave</div>'
       f'<div class="sc-inset">{band_rows(target, data)}</div>' if data.get("band") else
       f'<div class="sc-answer-big">≈ {fmt_value(target, data["value"])}</div>'
       + mini_range(data['low'], data['value'], data['high'], target)}
      {note_html}
      <div class="sc-small" style="margin-top:10px">Based on</div>{chips(based)}
      <div class="sc-small"><i>{SYNTHETIC_LINE}</i></div>
    </div>""")


def break_even_card(b: dict) -> str:
    c, months = b["costs"], b["months"]
    lakh = lambda x: f"₹{x / 100_000:,.1f} lakh"
    rows = "".join(f'<div class="sc-kv"><span>− {name}</span><span>{lakh(c[key])}</span></div>'
                   for key, name in (("food", "Food"), ("staff", "Staff"), ("rent", "Rent"), ("other", "Other costs")))
    assumptions = (f"₹{ASSUMPTIONS['salary_per_staff']:,} per staff member a month; rent ₹{ASSUMPTIONS['base_rent_per_sqft']}"
                   f"/sq ft in a typical area, adjusted by the area's price level; other costs {ASSUMPTIONS['other_costs_pct']}% of sales.")
    if months:
        head = f'<div class="sc-answer-big">≈ {months:.0f} months</div><div class="sc-small">to earn back the investment</div>'
        tail = f'<div class="sc-inset sc-small">Investment {lakh(b["investment"] * 100_000)} ÷ profit {lakh(b["profit"])} a month = ≈ {months:.0f} months</div>'
        cls = "sc-answer"
    else:
        head = '<div class="sc-answer-big" style="color:#A86A00">Not reached</div>'
        tail = ('<div class="sc-verdict" style="background:#FEF8EC">⚠️ Monthly costs exceed sales under these assumptions. '
                'Try a higher price or fewer staff in Compare.</div>')
        cls = "sc-answer sc-answer-warn"
    return clean(f"""
    <div class="{cls}">
      <div class="sc-card-head"><span class="sc-h3">⏱️ Break-even</span></div>
      {head}
      <div class="sc-inset"><div class="sc-kv"><span>Sales</span><b>{lakh(b['revenue'])}</b></div>{rows}
        <div class="sc-kv" style="border:0"><b>= Profit</b><b>{lakh(b['profit'])} / month</b></div></div>
      {tail}
      {f'<div class="sc-small" style="margin-top:8px">For the range you gave: {band_span("break_even", b)}</div>'
       f'<div class="sc-inset">{band_rows("break_even", b)}</div>' if b.get("band") else ""}
      <details class="sc-details"><summary>Assumptions (not models)</summary><div class="sc-small">{assumptions}</div></details>
      <div class="sc-small"><i>{SYNTHETIC_LINE}; break-even is a formula on those estimates</i></div>
    </div>""")


def full_plan_card(data: dict, concept: dict) -> str:
    tiles = "".join(f'<div class="sc-tile"><div class="sc-small">{PLAN_ICON[t]} {html.escape(TARGETS[t]["label"])}</div>'
                    + (f'<b>{band_span(t, d)}</b><div class="sc-small">for your range</div></div>' if d.get("band") else
                       f'<b>≈ {fmt_value(t, d["value"])}</b><div class="sc-small">{fmt_range(t, d["low"], d["high"])}</div></div>')
                    for t, d in data["targets"].items())
    months = data["break_even"]["months"]
    tiles += (f'<div class="sc-tile sc-tile-wide"><div class="sc-small">⏱️ Break-even</div>'
              f'<b>{band_span("break_even", data["break_even"]) if data["break_even"].get("band") else f"≈ {months:.0f} months" if months else "Not reached"}</b></div>')
    notes = "".join(f'<div class="sc-small" style="margin-top:6px">• {html.escape(d["note"])}</div>'
                    for d in data["targets"].values() if d.get("note"))
    return clean(f"""
    <div class="sc-answer">
      <div class="sc-card-head"><span class="sc-h3">📋 Opening plan</span></div>
      <div class="sc-tiles">{tiles}</div>{notes}
      <div class="sc-small" style="margin-top:8px"><i>{SYNTHETIC_LINE}</i></div>
    </div>""")


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
.stApp, .stApp *:not([data-testid="stIconMaterial"]) {font-family: 'Inter', sans-serif;}
.stApp {background: #F8F8F8;}
header[data-testid="stHeader"] {display: none;}
.block-container {max-width: 480px; padding: 0.75rem 1rem 7rem;}
.sc-top {display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;}
.sc-logo {color: #E23744; font-weight: 800; font-size: 1.35rem; letter-spacing: -0.02em;}
.sc-pill {font-size: 0.72rem; font-weight: 700; color: #24963F; background: #EAF7EE; border-radius: 9999px; padding: 3px 10px;}
.sc-hero {background: linear-gradient(135deg, #E23744, #B7122A); color: #fff; border-radius: 16px; padding: 18px 16px; margin-bottom: 14px;}
.sc-hero h1 {color: #fff; font-size: 1.6rem; font-weight: 800; line-height: 1.2; margin: 0 0 6px; padding: 0;}
.sc-hero p {margin: 0; opacity: 0.92; font-size: 0.92rem;}
.sc-h2 {font-size: 1.35rem; font-weight: 800; letter-spacing: -0.02em; margin: 4px 0 2px; color: #1C1C1C;}
.sc-h3 {font-size: 1.05rem; font-weight: 700; color: #1C1C1C;}
.sc-muted {color: #696969; font-size: 0.86rem;}
.sc-small {color: #696969; font-size: 0.75rem;}
.sc-center {text-align: center;}
.sc-card, .sc-swipe-card {background: #fff; border: 1px solid #E8E8E8; border-radius: 16px; padding: 16px;
  box-shadow: 0 2px 8px rgba(28,28,28,0.04); margin-bottom: 14px;}
.sc-card-head {display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; gap: 8px;}
.sc-big {font-size: 2.3rem; font-weight: 800; letter-spacing: -0.03em; font-feature-settings: "tnum" 1;}
.sc-unit {font-size: 0.95rem; font-weight: 500; color: #696969;}
.sc-badge {display: inline-block; border: 1px solid; border-radius: 6px; padding: 2px 8px; font-size: 0.75rem; font-weight: 700; white-space: nowrap;}
.sc-verdict {border-radius: 12px; padding: 10px 12px; margin-top: 12px; font-size: 0.88rem; display: flex; flex-direction: column; gap: 4px;}
.sc-range {position: relative; height: 44px; margin: 18px 4px 4px;}
.sc-range-track {position: absolute; top: 22px; left: 0; right: 0; height: 10px; background: #EEE; border-radius: 9999px;}
.sc-range-band {position: absolute; top: 22px; height: 10px; background: #FFB3B1; border-radius: 9999px;}
.sc-range-dot {position: absolute; top: 18px; width: 18px; height: 18px; margin-left: -9px; background: #E23744; border: 3px solid #fff; border-radius: 50%; box-shadow: 0 1px 4px rgba(0,0,0,.25);}
.sc-range-you {position: absolute; top: 19px; width: 14px; height: 14px; margin-left: -7px; transform: rotate(45deg); border: 2px solid #fff;}
.sc-range-youlabel {position: absolute; top: 0; transform: translateX(-50%); font-size: 0.75rem; font-weight: 700; white-space: nowrap;}
.sc-row {display: flex; align-items: center; gap: 12px;}
.sc-rating {display: inline-block; color: #fff; font-weight: 800; border-radius: 8px; padding: 3px 8px; font-size: 0.85rem; white-space: nowrap; font-feature-settings: "tnum" 1;}
.sc-rating small {font-weight: 600; font-size: 0.7em;}
.sc-rating-lg {font-size: 1.8rem; padding: 8px 14px; border-radius: 14px; flex: 0 0 auto; text-align: center; line-height: 1.1;}
.sc-rating-lg small {display: block; font-size: 0.45em;}
.sc-list {margin: 0; padding-left: 18px; font-size: 0.88rem; color: #3B3B3B;}
.sc-list li {margin-bottom: 4px;}
.sc-inset {background: #F6F3F2; border-radius: 12px; padding: 12px; margin-top: 12px; font-size: 0.9rem;}
.sc-meter {height: 8px; background: #E5E2E1; border-radius: 9999px; margin-top: 10px; overflow: hidden;}
.sc-meter div {height: 100%; border-radius: 9999px;}
.sc-legend {display: flex; flex-wrap: wrap; gap: 10px; font-size: 0.74rem; font-weight: 700; margin-top: 10px;}
.sc-chips {display: flex; gap: 6px; overflow-x: auto; padding-bottom: 4px; margin: 6px 0 12px; scrollbar-width: none;}
.sc-chip {background: #fff; border: 1px solid #E8E8E8; border-radius: 9999px; padding: 5px 11px; font-size: 0.8rem; white-space: nowrap;}
.sc-swipe {display: flex; gap: 12px; overflow-x: auto; scroll-snap-type: x mandatory; padding: 4px 2px 10px; -webkit-overflow-scrolling: touch;}
.sc-swipe-card {flex: 0 0 82%; scroll-snap-align: start; margin-bottom: 0;}
.sc-details {margin-top: 8px; font-size: 0.82rem;}
.sc-details summary {cursor: pointer; color: #B7122A; font-weight: 600;}
.sc-details .sc-chips {flex-wrap: wrap; overflow: visible; margin: 8px 0 0;}
.sc-changed {background: #FFF0F1; color: #B7122A; border-radius: 8px; padding: 6px 10px; font-size: 0.82rem; font-weight: 600; margin-bottom: 10px;}
.sc-kv {display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px dashed #EEE; font-size: 0.88rem;}
.sc-note {background: #FEF8EC; border: 1px solid #F2D58A; border-radius: 12px; padding: 12px; font-size: 0.86rem; margin: 6px 0 14px;}
.sc-step {font-size: 0.8rem; font-weight: 700; color: #E23744; letter-spacing: 0.02em;}
.sc-summary h2 {font-size: 1.2rem; font-weight: 800; margin: 0 0 4px;}
.sc-summary p, .sc-summary li {font-size: 0.9rem;}
.sc-summary h3 {font-size: 1rem; font-weight: 700; color: #B7122A; margin: 14px 0 4px;}
.sc-summary table {width: 100%; border-collapse: collapse; font-size: 0.82rem;}
.sc-summary th, .sc-summary td {text-align: left; padding: 5px 4px; border-bottom: 1px solid #EEE;}
.sc-footer {text-align: center; color: #696969; font-size: 0.72rem; padding: 18px 8px 8px;}
.stButton button, .stDownloadButton button {border-radius: 9999px; font-weight: 600; min-height: 46px;}
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {min-height: 52px; box-shadow: 0 4px 12px rgba(226,55,68,0.25);}
.st-key-playcard, .st-key-whatif_form, .st-key-services {background: #fff; border: 1px solid #E8E8E8; border-radius: 16px; padding: 16px;}
.st-key-bottomnav {position: fixed; bottom: 0; left: 50%; transform: translateX(-50%); width: 100%; max-width: 480px;
  background: #fff; border-top: 1px solid #EEE; box-shadow: 0 -4px 16px rgba(0,0,0,0.06);
  padding: 0 8px env(safe-area-inset-bottom); z-index: 1000;}
.st-key-bottomnav [data-testid="stButtonGroup"] {width: 100%;}
.st-key-bottomnav [data-testid="stButtonGroup"] > div {gap: 0 !important; border: none !important;}
.st-key-bottomnav [data-testid="stButtonGroup"] button {flex: 1 1 0; min-width: 0; min-height: 52px; padding: 0 2px;
  border: none !important; border-top: 3px solid transparent !important; border-radius: 0 !important;
  background: transparent !important; color: #696969 !important; box-shadow: none !important;}
.st-key-bottomnav [data-testid="stButtonGroup"] button p {font-size: 0.86rem; font-weight: 600; white-space: nowrap;}
.st-key-bottomnav [data-testid="stButtonGroup"] button[aria-checked="true"] {color: #E23744 !important; border-top-color: #E23744 !important;}
.st-key-bottomnav [data-testid="stButtonGroup"] button[aria-checked="true"] p {color: #E23744; font-weight: 700;}
.st-key-cardrow {flex-wrap: nowrap !important; overflow-x: auto; scroll-snap-type: x mandatory; gap: 12px !important;
  align-items: stretch !important; padding: 4px 2px 12px; -webkit-overflow-scrolling: touch; scrollbar-width: none;}
.st-key-cardrow > [data-testid="stLayoutWrapper"] {flex: 0 0 86% !important; width: 86% !important; max-width: 86% !important;
  min-width: 0; display: flex; scroll-snap-align: start;}  /* every card the same width; the next one peeks in */
[class*="st-key-card_"] {flex: 1 1 auto; width: 100% !important; position: relative; background: #fff;
  border: 1px solid #E8E8E8; border-radius: 16px; padding: 16px; box-shadow: 0 2px 8px rgba(28,28,28,0.04); gap: 8px !important;}
[class*="st-key-card_"] > div:last-child {margin-top: auto;}  /* "Choose this one" lines up at the bottom of every card */
[class*="st-key-card_"][class*="_sel"] {border: 2px solid #E23744; box-shadow: 0 4px 16px rgba(226,55,68,0.18);}
.sc-card-body .sc-kv span:first-child {white-space: nowrap;}
.sc-card-body .sc-h3 {display: flex; flex-wrap: wrap; align-items: center; gap: 6px;}
[class*="st-key-pick_"] {position: absolute; top: 12px; right: 12px; width: auto !important; z-index: 2;}
[class*="st-key-pick_"] button {width: 30px; height: 30px; min-height: 30px !important; padding: 0; border-radius: 50%;
  border: 2px solid #D0C4C3; background: #fff; color: transparent; font-weight: 800;}
[class*="st-key-pick_"][class*="_on"] button {background: #E23744; border-color: #E23744; color: #fff;}
.sc-card-body .sc-card-head {padding-right: 36px;}
.sc-faded {opacity: 0.8;}
.st-key-plancta {margin: 2px 0 6px;}
.sc-empty {text-align: center; padding: 26px 18px;}
.sc-empty-icon {font-size: 3rem; background: #F6F3F2; border-radius: 50%; width: 96px; height: 96px; display: inline-flex;
  align-items: center; justify-content: center; margin-bottom: 10px;}
.sc-strip {background: #fff; border: 1px solid #E8E8E8; border-radius: 16px; padding: 12px 14px; margin-bottom: 8px;}
.sc-banner {background: #EFF6FF; color: #1E3A8A; border-radius: 12px; padding: 10px 12px; font-size: 0.82rem; margin-bottom: 10px;}
.sc-msg {display: flex; gap: 8px; align-items: flex-start; margin: 10px 0;}
.sc-msg-user {flex-direction: column; align-items: flex-end;}
.sc-avatar {flex: 0 0 30px; height: 30px; border-radius: 50%; background: #E23744; display: inline-flex;
  align-items: center; justify-content: center; font-size: 0.9rem;}
.sc-bubble-bot {background: #EFEDED; border-radius: 4px 16px 16px 16px; padding: 10px 13px; font-size: 0.9rem; max-width: 86%;}
.sc-bubble-user {background: #E23744; color: #fff; border-radius: 16px 4px 16px 16px; padding: 10px 13px; font-size: 0.9rem; max-width: 86%;}
.sc-qnum {display: block; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.05em; color: #696969; margin-bottom: 3px;}
.sc-facts {display: flex; gap: 6px; margin-top: 4px;}
.sc-fact {background: #EFEDED; border-radius: 9999px; padding: 2px 9px; font-size: 0.72rem; font-weight: 600;}
.sc-answer {background: #fff; border: 1px solid #E8E8E8; border-left: 4px solid #E23744; border-radius: 16px; padding: 14px;
  margin: 6px 0 6px 38px; box-shadow: 0 2px 8px rgba(28,28,28,0.05);}
.sc-answer-warn {border-left-color: #F9A825;}
.sc-answer-big {font-size: 1.9rem; font-weight: 800; color: #E23744; letter-spacing: -0.02em;}
.sc-mini-range {margin: 8px 0 2px;}
.sc-mini-track {position: relative; height: 8px; background: #FFB3B1; border-radius: 9999px;}
.sc-mini-dot {position: absolute; left: 50%; top: -4px; width: 16px; height: 16px; margin-left: -8px; background: #E23744;
  border: 3px solid #fff; border-radius: 50%; box-shadow: 0 1px 4px rgba(0,0,0,.25);}
.sc-tiles {display: grid; grid-template-columns: 1fr 1fr; gap: 8px;}
.sc-tile {background: #F6F3F2; border-radius: 12px; padding: 10px;}
.sc-tile-wide {grid-column: 1 / -1;}
.st-key-planchat [data-testid="stChatInput"] {margin-top: 8px;}
</style>
"""


# ---------------------------------------------------------------- state helpers
def init_state() -> None:
    defaults = {"page": "check", "step": 1, "concept": new_concept(), "whatifs": [], "error": None, "assessed": False}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    # Sessions started before what-ifs could change several settings stored one {"field", "value"} each.
    st.session_state.whatifs = [w if "changes" in w else {"changes": {w["field"]: w["value"]}}
                                for w in st.session_state.whatifs]


def bind(key: str, value) -> None:
    """Give a widget its starting value from the concept the first time it is drawn (avoids default/state clashes)."""
    if key not in st.session_state:
        st.session_state[key] = value


def store(field: str, key: str) -> None:
    st.session_state.concept[field] = st.session_state[key]


def go(page: str, step: int | None = None) -> None:
    st.session_state.page = page
    st.session_state.error = None
    if step is not None:
        st.session_state.step = step


def next_step() -> None:
    step = st.session_state.step
    st.session_state.error = step_error(step, st.session_state.concept)
    if st.session_state.error:
        return
    if step < len(STEPS):
        st.session_state.step = step + 1
    else:
        st.session_state.assessed = True
        go("results")


def back_step() -> None:
    st.session_state.error = None
    st.session_state.step = max(1, st.session_state.step - 1)


def reset_all() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]


# ---------------------------------------------------------------- pages
def top_bar() -> None:
    st.html('<div class="sc-top"><span class="sc-logo">📍🍽️ SpotCheck</span><span class="sc-pill">No sign-up</span></div>')


def footer() -> None:
    st.html(f'<div class="sc-footer">{FOOTER}</div>')


def page_check() -> None:
    c, step = st.session_state.concept, st.session_state.step
    if step == 1:
        st.html(clean("""<div class="sc-hero"><h1>Will your restaurant idea work?</h1>
            <p>Check your price and rating chances in 2 minutes. Based on 9,244 Bangalore restaurants. No sign-up.</p></div>"""))
    st.progress(step / len(STEPS), text=f"Step {step} of {len(STEPS)} · {STEPS[step - 1]}")
    if st.session_state.error:
        st.error(f"⚠️ {st.session_state.error}")

    if step == 1:
        st.html('<div class="sc-h2">Where will it be?</div>')

        def chip_changed():
            value = st.session_state.w_area_chip
            if value:
                c["location"] = value
                st.session_state.w_area_search = value

        def search_changed():
            value = st.session_state.w_area_search
            c["location"] = value
            st.session_state.w_area_chip = value if value in POPULAR_AREAS else None

        bind("w_area_search", c["location"])
        bind("w_area_chip", c["location"] if c["location"] in POPULAR_AREAS else None)
        st.selectbox("Search all 40 Bangalore areas", ALLOWED["location"], key="w_area_search",
                     placeholder="🔍 Search 40 Bangalore areas…", on_change=search_changed)
        st.pills("Popular areas", POPULAR_AREAS, key="w_area_chip", on_change=chip_changed,
                 format_func=lambda a: "✨ Other area" if a == "Other" else a)
        st.caption("Choose “Other area” if yours isn't listed.")

    elif step == 2:
        st.html('<div class="sc-h2">What kind of place?</div>')
        bind("w_type", c["primary_type"])
        st.pills("Restaurant type", ALLOWED["primary_type"], key="w_type", on_change=store, args=("primary_type", "w_type"),
                 format_func=lambda t: f"{TYPE_EMOJI[t]} {t}", label_visibility="collapsed")
        with st.container(key="services"):
            st.markdown("**Services**")
            for field, emoji, label, hint in SERVICES:
                bind(f"w_{field}", c[field] == "Yes")
                st.toggle(f"{emoji} {label}", key=f"w_{field}", help=hint,
                          on_change=lambda f=field: c.__setitem__(f, "Yes" if st.session_state[f"w_{f}"] else "No"))

    elif step == 3:
        st.html('<div class="sc-h2">What\'s on the menu?</div>')
        high = RANGES["n_cuisines"][1]

        def cuisines_changed():
            # The total follows the chips; cuisines added with + (not in the list) are kept on top.
            extras = c["n_cuisines"] - len(c["cuisines"]) if st.session_state.get("extras_added") else 0
            c["cuisines"] = list(st.session_state.w_cuisines)
            c["n_cuisines"] = min(high, len(c["cuisines"]) + max(0, extras))  # 0 when nothing is picked
            st.session_state.w_n_cuisines = c["n_cuisines"]

        def total_changed():
            c["n_cuisines"] = st.session_state.w_n_cuisines
            st.session_state.extras_added = c["n_cuisines"] > len(c["cuisines"])

        bind("w_cuisines", list(c["cuisines"]))
        st.pills("Tap all main cuisines you'll serve", CUISINE_FLAGS, selection_mode="multi", key="w_cuisines",
                 on_change=cuisines_changed, format_func=lambda f: f"{CUISINE_EMOJI[f]} {cuisine_name(f)}")
        st.caption(f"{len(c['cuisines'])} selected · the total below updates as you tap")
        bind("w_n_cuisines", int(c["n_cuisines"]))
        st.number_input("Total number of cuisines on your menu", min_value=0, max_value=high, step=1,
                        key="w_n_cuisines", on_change=total_changed,
                        help=f"Press + for cuisines that aren't in the list above (up to {high} in total).")

    else:
        st.html('<div class="sc-h2">What will two people pay?</div>')

        def slider_changed():
            c["cost_for_two"] = st.session_state.w_cost_slider
            st.session_state.w_cost_exact = c["cost_for_two"]

        def exact_changed():
            c["cost_for_two"] = int(st.session_state.w_cost_exact)
            st.session_state.w_cost_slider = min(max(c["cost_for_two"], SLIDER_MIN), SLIDER_MAX)

        bind("w_cost_slider", min(max(int(c["cost_for_two"]), SLIDER_MIN), SLIDER_MAX))
        bind("w_cost_exact", int(c["cost_for_two"]))
        st.html(f'<div class="sc-big">{rupees(c["cost_for_two"])}<span class="sc-unit"> for two</span></div>')
        st.slider("Planned cost for two", SLIDER_MIN, SLIDER_MAX, step=SLIDER_STEP, key="w_cost_slider",
                  format="₹%d", on_change=slider_changed, label_visibility="collapsed")
        low, high = RANGES["cost_for_two"]
        with st.expander("Type an exact amount"):
            st.number_input(f"Exact cost for two (₹{low:,} – ₹{high:,})", min_value=low, max_value=high, step=10,
                            key="w_cost_exact", on_change=exact_changed)
        if c["location"] and c["primary_type"]:
            st.html('<div class="sc-muted">Your concept so far</div>' + chips(concept_chips(c)))

    with st.container(horizontal=True):
        if step > 1:
            st.button("← Back", on_click=back_step, width="stretch")
        label = "Check my concept ✨" if step == len(STEPS) else f"Next: {STEPS[step]} →"
        st.button(label, type="primary", on_click=next_step, width="stretch")


def page_results() -> None:
    c = st.session_state.concept
    res = assess(to_inputs(c))
    st.button("← Edit concept", on_click=go, args=("check", 1), type="tertiary")
    st.html('<div class="sc-h2">Your concept check</div>' + chips(concept_chips(c)))
    st.html(price_card(res))
    st.html(rating_card(res))

    with st.container(key="playcard"):
        st.html(f'<div class="sc-card-head"><span class="sc-h3">🎚️ Play with your price</span>{badge("Interactive", "red")}</div>'
                '<div class="sc-muted">Drag to see how your price compares – results update instantly.</div>')
        bind("w_play", min(max(int(c["cost_for_two"]), SLIDER_MIN), SLIDER_MAX))
        play = st.slider("Testing price for two", SLIDER_MIN, SLIDER_MAX, step=SLIDER_STEP, key="w_play", format="₹%d")
        test = assess({**to_inputs(c), "cost_for_two": play})
        label, tone, sentence = test["price_verdict"]
        st.html(clean(f"""<div class="sc-inset"><b>At {rupees(play)} for two:</b>
            <div class="sc-row" style="margin-top:8px;flex-wrap:wrap">{badge(label, tone)}
            {rating_badge(test['prob'], test['rating_verdict'][1])}</div>
            <div class="sc-small" style="margin-top:8px">{html.escape(sentence)} Pricier places tend to be rated higher – a pattern, not a cause.</div></div>"""))

    with st.expander("ℹ️ Keep in mind", expanded=True):
        st.html('<ul class="sc-list">' + "".join(f"<li>{html.escape(k)}</li>" for k in KEEP_IN_MIND) + "</ul>")
    with st.expander("Details for experienced owners"):
        st.html(clean(f"""<ul class="sc-list">
            <li><b>Price model:</b> Random Forest (100 trees), typically within ₹{PRICE_BAND} of real prices
            (10-fold cross-validation, R² 0.73).</li>
            <li><b>Rating model:</b> Logistic Regression, AUC 0.81; its percentages are well calibrated.</li>
            <li>Your estimate: {rupees(res['price'])}; chance of 4.0+: {res['prob']:.1%}.</li></ul>"""))
    st.button("Try a what-if 🔁", type="primary", on_click=go, args=("compare",), width="stretch")
    st.button("📄 Get my summary", on_click=go, args=("summary",), width="stretch")


WI_KEYS = {"location": "wi_location", "primary_type": "wi_type", "has_bar": "wi_has_bar",
           "online_order": "wi_online_order", "book_table": "wi_book_table", "cuisines": "wi_cuisines",
           "n_cuisines": "wi_n", "cost_for_two": "wi_cost"}


def add_whatif() -> None:
    """Form submit: build the what-if from every setting, check it, and add it as a card."""
    ss, c = st.session_state, st.session_state.concept
    new = {f: ss[k] for f, k in WI_KEYS.items()}
    for f, _, _, _ in SERVICES:
        new[f] = "Yes" if new[f] else "No"
    new["cuisines"] = [x for x in CUISINE_FLAGS if x in new["cuisines"]]
    new["n_cuisines"] = max(int(new["n_cuisines"]), len(new["cuisines"]))
    new["cost_for_two"] = int(new["cost_for_two"])
    changes = diff(c, new)
    problem = (step_error(3, new) or step_error(4, new)
               or ("Change at least one setting to make a what-if." if not changes else None)
               or ("You've already added this what-if." if {"changes": changes} in ss.whatifs else None))
    ss.wi_error = problem
    if not problem:
        ss.whatifs.append({"changes": changes})
        for k in [*WI_KEYS.values(), "wi_prev"]:  # the next card starts again from the concept
            ss.pop(k, None)


def wi_cuisines_changed() -> None:
    """What-if card: the cuisine total follows the chips, keeping any extra cuisines added with + on top."""
    ss = st.session_state
    extras = max(0, int(ss.wi_n) - len(ss.get("wi_prev", [])))
    ss.wi_prev = list(ss.wi_cuisines)
    ss.wi_n = min(RANGES["n_cuisines"][1], len(ss.wi_cuisines) + extras)


def whatif_form(c: dict, whatifs: list[dict]) -> None:
    for f, k in WI_KEYS.items():
        value = c[f] == "Yes" if f in SHORT else list(c[f]) if f == "cuisines" else c[f]
        bind(k, value)
    bind("wi_prev", list(c["cuisines"]))
    use_slider = SLIDER_MIN <= c["cost_for_two"] <= SLIDER_MAX
    with st.container(key="whatif_form"):
        st.markdown(f"**➕ Add what-if card {len(whatifs) + 1} of {MAX_WHATIFS}**")
        st.caption("Starts from your concept – change as many settings as you like, then add the card.")
        if st.session_state.get("wi_error"):
            st.error(f"⚠️ {st.session_state.wi_error}")
        st.selectbox("📍 Location", ALLOWED["location"], key="wi_location")
        st.selectbox("Restaurant type", ALLOWED["primary_type"], key="wi_type",
                     format_func=lambda t: f"{TYPE_EMOJI[t]} {t}")
        for field, emoji, label, hint in SERVICES:
            st.toggle(f"{emoji} {label}", key=f"wi_{field}", help=hint)
        st.pills("Main cuisines", CUISINE_FLAGS, selection_mode="multi", key="wi_cuisines",
                 on_change=wi_cuisines_changed, format_func=lambda f: f"{CUISINE_EMOJI[f]} {cuisine_name(f)}")
        high = RANGES["n_cuisines"][1]
        st.caption(f"{len(st.session_state.wi_cuisines)} selected · the total below updates as you tap")
        st.number_input("Total number of cuisines", min_value=0, max_value=high, step=1, key="wi_n",
                        help=f"Press + for cuisines that aren't in the list above (up to {high} in total).")
        if use_slider:
            st.slider("💰 Planned price for two", SLIDER_MIN, SLIDER_MAX, step=SLIDER_STEP, key="wi_cost",
                      format="₹%d")
        else:
            st.number_input("💰 Planned price for two (₹)", *RANGES["cost_for_two"], step=10, key="wi_cost")
        st.button("+ Add what-if card", type="primary", on_click=add_whatif, width="stretch")


def page_compare() -> None:
    st.html('<div class="sc-h2">Compare your options</div><div class="sc-muted">Compare your concept with up to 3 what-ifs. '
            'Pick the version you\'ll open, then plan it.</div>')
    if not st.session_state.assessed:
        st.info("Check a concept first – then try what-ifs here.")
        st.button("Start with my concept →", type="primary", on_click=go, args=("check", 1), width="stretch")
        return
    c, whatifs = st.session_state.concept, st.session_state.whatifs
    rows = scenarios(c, whatifs)
    if st.session_state.get("plan_pick") not in range(len(rows)):
        st.session_state.plan_pick = None  # nothing picked yet, or the picked what-if was removed
    pick = st.session_state.plan_pick
    selection = lambda i: "" if pick is None else "selected" if i == pick else "faded"
    set_pick = lambda i: st.session_state.__setitem__("plan_pick", i)
    with st.container(key="cardrow", horizontal=True):  # swipeable row of tappable cards
        for i, sc in enumerate(rows):
            with st.container(key=f"card_{i}{'_sel' if i == pick else ''}"):
                st.button("✓", key=f"pick_{i}{'_on' if i == pick else ''}", on_click=set_pick, args=(i,),
                          help="Choose this concept")
                st.html(scenario_card(sc, selection(i)))
                st.button("✓ Selected" if i == pick else "Choose this one", key=f"choose_{i}", on_click=set_pick,
                          args=(i,), type="primary" if i == pick else "secondary", width="stretch")
    with st.container(key="plancta"):
        if pick is None:
            st.button("Select a card to continue", disabled=True, width="stretch", key="plan_go_off")
        else:
            st.button("Plan this concept →", type="primary", width="stretch", key="plan_go",
                      on_click=plan_this, args=(scenario_label(rows, pick), rows[pick]["concept"]))
    if st.session_state.get("plan_switch"):
        switch_plan_dialog()
    if len(rows) > 1:
        st.caption("Swipe sideways to see every card. Tap “All settings” on a card to see its full setup.")
        with st.container(horizontal=True):
            for i, sc in enumerate(rows[1:]):
                st.button(f"✕ Remove “{sc['title']}”", key=f"rm_{i}", type="tertiary",
                          on_click=lambda i=i: st.session_state.whatifs.pop(i))

    if len(whatifs) < MAX_WHATIFS:
        whatif_form(c, whatifs)
    else:
        st.caption(f"Up to {MAX_WHATIFS} what-if cards – remove one to add another.")

    st.html(clean("""<div class="sc-note">💡 <b>Why can a higher price raise the rating chance?</b> In the data, pricier
        restaurants tend to be rated higher. That's a pattern, not a promise – raising your price alone won't improve
        your rating.</div>"""))
    st.button("📄 Get my summary", on_click=go, args=("summary",), width="stretch")
    st.button("← Back to results", on_click=go, args=("results",), width="stretch")


# ---------------------------------------------------------------- Plan
def plan_this(label: str, concept: dict) -> None:
    """'Plan this concept': open the Plan chat for the picked card (asks first if it would clear a plan)."""
    current = st.session_state.get("plan")
    if current and current["concept"] == concept:
        current["label"] = label
    elif current and current["chat"]["history"]:
        st.session_state.plan_switch = {"label": label, "concept": concept}
        return
    else:
        start_plan(label, concept)
    go("plan")


def start_plan(label: str, concept: dict) -> None:
    st.session_state.plan = {"label": label, "concept": dict(concept), "chat": new_chat(to_inputs(concept))}


@st.dialog("Start a new plan?")
def switch_plan_dialog() -> None:
    switch, current = st.session_state.plan_switch, st.session_state.plan
    st.write("You picked a different concept. Your current plan answers will be cleared.")
    st.html(clean(f"""<div class="sc-inset sc-small"><b>From:</b> {html.escape(current['label'])}<br>↓<br>
        <b>To:</b> {html.escape(switch['label'])}</div>"""))
    if st.button("Start new plan", type="primary", width="stretch"):
        start_plan(switch["label"], switch["concept"])
        del st.session_state.plan_switch
        go("plan")
        st.rerun()
    if st.button("Keep current plan", type="tertiary", width="stretch"):
        del st.session_state.plan_switch
        st.rerun()


def gemini() -> object | None:
    """Gemini message reader if a key is configured (and not switched off for tests), else None (rules)."""
    if os.environ.get("PLANNER_NO_LLM"):
        return None
    try:
        key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        model = st.secrets.get("GEMINI_MODEL") or "gemini-3.5-flash-lite"
    except Exception:  # noqa: BLE001 – no secrets file
        key, model = os.environ.get("GEMINI_API_KEY"), "gemini-3.5-flash-lite"
    return gemini_reader(key, model) if key else None


def send(text: str) -> None:
    with st.spinner("SpotCheck is reading your message…"):
        respond(st.session_state.plan["chat"], text, gemini())


def page_plan() -> None:
    plan = st.session_state.get("plan")
    if not plan:
        st.html(clean("""<div class="sc-card sc-empty"><div class="sc-empty-icon">📋</div>
            <div class="sc-h2">Plan your opening</div>
            <p class="sc-muted">First choose the concept you'll open in <b>Compare</b>. Then ask me about space, staff,
            money, food cost, revenue and break-even.</p></div>"""))
        if st.session_state.assessed:
            st.button("Go to Compare →", type="primary", on_click=go, args=("compare",), width="stretch")
        else:
            st.button("Start with my concept →", type="primary", on_click=go, args=("check", 1), width="stretch")
        st.caption("Plan estimates come from synthetic planning data.")
        return

    c, chat = plan["concept"], plan["chat"]
    st.button("‹ Compare", on_click=go, args=("compare",), type="tertiary")
    st.html('<div class="sc-h2">Plan my restaurant</div>')
    services = [l for f, _, l, _ in SERVICES if c[f] == "Yes"]
    st.html(clean(f"""<div class="sc-strip"><div class="sc-card-head" style="margin:0">
        <b>{TYPE_EMOJI[c['primary_type']]} {html.escape(c['primary_type'])} · 📍 {html.escape(c['location'])}</b>
        <span class="sc-small">{html.escape(plan['label'])}</span></div>
        <div class="sc-muted">{rupees(c['cost_for_two'])} for two</div>
        {chips(services + [f"{c['n_cuisines']} cuisines"])}</div>"""))
    st.button("↺ Change concept", on_click=go, args=("compare",), type="tertiary")
    st.html('<div class="sc-banner">ℹ️ Estimates from <b>synthetic planning data</b>, not real Bangalore figures.</div>')
    with st.expander("Why synthetic?"):
        st.caption("Size, staff, money, food cost and revenue aren't in the Zomato data. These five estimates come from "
                   "Linear Regression models trained on generated data built from industry-style assumptions, so they "
                   "show how a plan could look, not facts. Price and rating still come from 9,244 real restaurants. "
                   + ("Your messages are read by Google Gemini only to understand the question; every number comes from "
                      "SpotCheck's models." if gemini() else "Messages are read by SpotCheck's built-in rules (no AI)."))

    parts = [bubble("bot", md_inline(f"Hi! Ask me anything about opening this {c['primary_type'].lower()}: size, staff, "
                                     "money to open, food cost, revenue or break-even. You can also tell me details, "
                                     "like “we'll be open 12 hours”."))]
    for msg in chat["history"]:
        if msg["role"] == "user":
            facts = "".join(f'<span class="sc-fact">{html.escape(USER_FACTS[f]["label"].capitalize())}: '
                            f'{"₹" + format(v, "g") + " lakh" if f == "budget_lakh" else format(v, "g")}</span>'
                            for f, v in msg.get("facts", {}).items())
            parts.append(bubble("user", html.escape(msg["content"]), f'<div class="sc-facts">{facts}</div>' if facts else ""))
        elif msg.get("answer"):
            parts.append(f'<div class="sc-msg"><span class="sc-avatar">🍽️</span><span class="sc-small">Here is your estimate:</span></div>'
                         + answer_card(msg["answer"], msg["data"], c))
        else:
            qnum = (f'<span class="sc-qnum">QUESTION {msg["q_index"]} OF {msg["q_total"]}</span>'
                    if msg.get("q_index") and msg.get("q_total", 0) > 1 else "")
            parts.append(bubble("bot", qnum + md_inline(msg["content"])))
    st.html("".join(parts))

    n = len(chat["history"])
    with st.container(key="planchat"):
        if chat["awaiting_objective"]:
            choice = st.pills("Your objective", list(OBJECTIVES), format_func=OBJECTIVES.get, key=f"obj_{n}")
            if choice:
                choose_objective(chat, choice)
                st.rerun()
        elif chat["asking"]:
            field = chat["asking"]
            options = QUICK_REPLIES[field] + [f"Not sure (use {typical(field)})"]
            choice = st.pills("Quick replies", options, key=f"qr_{n}", label_visibility="collapsed")
            if choice:
                send(choice)
                st.rerun()
        elif chat["answers"]:
            remaining = [o for o in OBJECTIVES if o not in chat["answers"] and o != "all"] + ["all"]
            choice = st.pills("Ask next", remaining, format_func=OBJECTIVES.get, key=f"next_{n}")
            if choice:
                choose_objective(chat, choice)
                st.rerun()
            st.button("📄 View my plan in the Summary", on_click=go, args=("summary",), width="stretch")
        placeholder = ("Type your objective…" if chat["awaiting_objective"] else
                       "Type your answer or tap a chip…" if chat["asking"] else
                       "Ask about size, staff, money, food cost…")
        typed = st.chat_input(placeholder, key="plan_input")
        if typed:
            send(typed)
            st.rerun()


def page_summary() -> None:
    if not st.session_state.assessed:
        st.info("Check a concept first – your summary appears here.")
        st.button("Start with my concept →", type="primary", on_click=go, args=("check", 1), width="stretch")
        return
    body = summary_html(st.session_state.concept, st.session_state.whatifs, st.session_state.get("plan"))
    st.html(f'<div class="sc-card">{body}</div>')
    document = (f'<!doctype html><html><head><meta charset="utf-8"><title>SpotCheck summary</title>{CSS}</head>'
                f'<body style="max-width:640px;margin:24px auto;padding:0 16px">{body}</body></html>')
    st.download_button("⬇️ Download summary", document, file_name="spotcheck_summary.html", mime="text/html",
                       type="primary", width="stretch")
    if st.session_state.get("plan"):
        st.button("← Back to Plan", on_click=go, args=("plan",), width="stretch")
    st.button("Start a new concept", on_click=reset_all, width="stretch")


def page_about() -> None:
    st.html(clean(f"""
    <div class="sc-h2">How SpotCheck works</div>
    <div class="sc-card"><div class="sc-row">📝<div><b>Describe your idea in 4 steps</b></div></div></div>
    <div class="sc-card"><div class="sc-row">🤖<div><b>Two models compare it with 9,244 Bangalore restaurants</b></div></div></div>
    <div class="sc-card"><div class="sc-row">📊<div><b>Get a price check and a rating outlook</b></div></div></div>
    <div class="sc-h2" style="margin-top:12px">How accurate is it?</div>
    <div class="sc-card"><div class="sc-h3">💰 Price: typically within ₹{PRICE_BAND}</div>
      <div class="sc-muted">Average error on restaurants the model hadn't seen (10-fold cross-validation).
      Random Forest model; it holds up on restaurant chains it never saw during training.</div></div>
    <div class="sc-card"><div class="sc-h3">⭐ Rating: ranks correctly 81% of the time</div>
      <div class="sc-muted">Ranks a 4.0+ place above a lower-rated one 81% of the time (AUC 0.81). When it says 30%,
      about 30% of such places really are rated 4.0+. Logistic Regression model.</div></div>
    <div class="sc-h2" style="margin-top:12px">The data</div>
    <div class="sc-card sc-muted">9,244 Bangalore restaurants with ratings from the Kaggle dataset 'Zomato Bangalore
      Restaurants' by Himanshu Poddar (scraped about 2019). We only use what you decide before opening – location,
      format, menu and price – never reviews or votes.</div>
    <div class="sc-h2" style="margin-top:12px">Limitations</div>
    <div class="sc-card"><ul style="margin:0;padding-left:18px">
      <li>⚠️ Food, service and hygiene aren't in the data.</li><li>⚠️ Closed restaurants are missing.</li>
      <li>⚠️ A single snapshot from about 2019.</li><li>⚠️ Patterns, not cause and effect.</li><li>⚠️ Bangalore only.</li></ul></div>
    <div class="sc-muted sc-center">SpotCheck is a student project for the MICA ML Capstone.<br>
      Not affiliated with Zomato. No sign-up, no data stored.</div>"""))


PAGES = {"check": page_check, "results": page_results, "compare": page_compare, "plan": page_plan,
         "summary": page_summary, "about": page_about}
NAV = {"predictor": "Predictor", "compare": "Compare", "plan": "Plan", "about": "About"}


def bottom_nav() -> None:
    page = st.session_state.page
    st.session_state.w_nav = page if page in ("compare", "plan", "about") else "predictor"

    def nav_changed():
        target = st.session_state.w_nav
        if target == "predictor":
            go("results" if st.session_state.assessed else "check")
        else:
            go(target)

    with st.container(key="bottomnav"):
        st.segmented_control("Navigation", list(NAV), key="w_nav", format_func=NAV.get, required=True,
                             on_change=nav_changed, label_visibility="collapsed", width="stretch")


def main() -> None:
    st.set_page_config(page_title="SpotCheck – restaurant concept check", page_icon="🍽️", layout="centered")
    st.html(CSS)
    init_state()
    top_bar()
    PAGES[st.session_state.page]()
    footer()
    bottom_nav()


if __name__ == "__main__":
    main()
