"""Predictions for the SpotCheck "Plan" chat: 5 Linear Regression models trained on SYNTHETIC data.

Every number the chat shows comes from here (models in planner/models/planner_models.joblib)
or from the break-even formula below. No AI service produces a number.

    from plan_predict import predict, break_even, missing_inputs
"""
import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

HERE = Path(__file__).resolve().parent
MODEL_PATH = HERE / "models" / "planner_models.joblib"
METRICS_PATH = HERE / "models" / "planner_metrics.json"
LOCATION_INDEX_PATH = HERE / "data" / "location_index.csv"

CUISINES = ["c_North_Indian", "c_Chinese", "c_South_Indian", "c_Fast_Food", "c_Biryani", "c_Desserts",
            "c_Beverages", "c_Continental", "c_Cafe", "c_Street_Food", "c_Italian", "c_Bakery"]

# Extra inputs the chat asks for (not in the main SpotCheck form): question, unit, allowed range, default.
EXTRA_INPUTS = {
    "guests_per_day": {"question": "About how many guests do you expect on a typical day (dine-in + takeaway)?",
                       "unit": "guests", "range": (20, 350), "default": 120},
    "opening_hours": {"question": "How many hours a day will you be open?", "unit": "hours",
                      "range": (6, 18), "default": 12},
    "delivery_share": {"question": "Roughly what % of your orders will be delivery?", "unit": "%",
                       "range": (0, 90), "default": 40},
    "menu_items": {"question": "About how many items will be on your menu?", "unit": "items",
                   "range": (10, 150), "default": 45},
    "alcohol_share": {"question": "What % of your sales do you expect from alcohol?", "unit": "%",
                      "range": (5, 60), "default": 30},
    "takeover": {"question": "Are you taking over an existing restaurant site (Yes/No)? It cuts fit-out costs.",
                 "unit": "", "options": ("Yes", "No"), "default": "No"},
}

# The 5 targets: label, unit, model inputs (main form fields + extras). Mirrors generate_data.TRUE_RULES.
TARGETS = {
    "floor_area_sqft": {
        "label": "Floor area", "unit": "sq ft",
        "features": ["primary_type", "book_table", "has_bar", "n_cuisines", "cost_for_two",
                     "guests_per_day", "delivery_share"],
    },
    "staff_count": {
        "label": "Staff headcount", "unit": "people",
        "features": ["primary_type", "book_table", "has_bar", "n_cuisines", "cost_for_two",
                     "guests_per_day", "opening_hours", "menu_items", "delivery_share"],
    },
    "investment_lakh": {
        "label": "Initial investment", "unit": "₹ lakh",
        "features": ["location", "primary_type", "book_table", "has_bar", "n_cuisines", "cost_for_two",
                     "guests_per_day", "takeover"],
    },
    "food_cost_pct": {
        "label": "Food cost (COGS)", "unit": "% of sales",
        "features": [*CUISINES, "cost_for_two", "menu_items", "alcohol_share"],
    },
    "revenue_lakh": {
        "label": "Monthly revenue", "unit": "₹ lakh",
        "features": ["location", "primary_type", "has_bar", "cost_for_two", "guests_per_day",
                     "delivery_share", "opening_hours"],
    },
}
CATEGORICAL = {"location", "primary_type", "has_bar", "online_order", "book_table", "takeover", *CUISINES}

# Break-even calculator assumptions (illustrative; shown to the user with every break-even answer).
ASSUMPTIONS = {
    "salary_per_staff": 20_000,      # ₹ per person per month, incl. food/benefits
    "base_rent_per_sqft": 90,        # ₹ per sq ft per month in a typical area; scaled by the area's price level
    "other_costs_pct": 15,           # utilities, marketing, commissions, maintenance, % of sales
}
LAKH = 100_000


@lru_cache(maxsize=1)
def _models() -> dict:
    return joblib.load(MODEL_PATH)


@lru_cache(maxsize=1)
def metrics() -> dict:
    return json.loads(METRICS_PATH.read_text())


@lru_cache(maxsize=1)
def _location_index() -> dict[str, float]:
    return pd.read_csv(LOCATION_INDEX_PATH).set_index("location")["location_index"].to_dict()


def needed_inputs(target: str) -> list[str]:
    """Extra (chat-asked) inputs a target's model needs."""
    targets = list(TARGETS) if target == "break_even" else [target]
    return list(dict.fromkeys(f for t in targets for f in TARGETS[t]["features"] if f in EXTRA_INPUTS))


def missing_inputs(target: str, inputs: dict) -> list[str]:
    """Extra inputs still to ask for. Alcohol share is only asked when the place serves alcohol."""
    need = [f for f in needed_inputs(target) if not (f == "alcohol_share" and inputs.get("has_bar") != "Yes")]
    return [f for f in need if inputs.get(f) in (None, "")]


def _frame(target: str, inputs: dict) -> pd.DataFrame:
    row = dict(inputs)
    if row.get("has_bar") == "No":
        row["alcohol_share"] = 0  # same rule as the synthetic data
    return pd.DataFrame([{f: row[f] for f in TARGETS[target]["features"]}])


def predict(target: str, inputs: dict) -> dict:
    """Point estimate plus a typical range (± the model's 10-fold CV MAE)."""
    value = float(_models()[target].predict(_frame(target, inputs))[0])
    mae = metrics()[target]["cv_mae"]
    return {"target": target, "value": value, "low": value - mae, "high": value + mae, "mae": mae}


def predict_all(inputs: dict) -> dict[str, dict]:
    return {t: predict(t, inputs) for t in TARGETS}


def break_even(inputs: dict) -> dict:
    """Months to recover the initial investment, from the 5 predictions plus ASSUMPTIONS (a formula, not a model)."""
    p = {t: r["value"] for t, r in predict_all(inputs).items()}
    revenue = p["revenue_lakh"] * LAKH
    rent = p["floor_area_sqft"] * ASSUMPTIONS["base_rent_per_sqft"] * (1 + _location_index().get(inputs["location"], 0))
    costs = {
        "food": revenue * p["food_cost_pct"] / 100,
        "staff": round(p["staff_count"]) * ASSUMPTIONS["salary_per_staff"],
        "rent": rent,
        "other": revenue * ASSUMPTIONS["other_costs_pct"] / 100,
    }
    profit = revenue - sum(costs.values())
    months = p["investment_lakh"] * LAKH / profit if profit > 0 else None
    return {"predictions": p, "revenue": revenue, "costs": costs, "profit": profit, "months": months}
