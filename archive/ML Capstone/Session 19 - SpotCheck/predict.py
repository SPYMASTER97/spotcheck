"""SpotCheck prediction functions used by the app and by test_reference.py.

Predictions come only from the trained .joblib models in this folder.
Each model is loaded once, the first time it is needed.
"""
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

HERE = Path(__file__).resolve().parent
PRICE_MODEL_PATH = HERE / "price_model.joblib"
RATING_MODEL_PATH = HERE / "rating_model.joblib"

CUISINE_FLAGS = [
    "c_North_Indian", "c_Chinese", "c_South_Indian", "c_Fast_Food",
    "c_Biryani", "c_Desserts", "c_Beverages", "c_Continental",
    "c_Cafe", "c_Street_Food", "c_Italian", "c_Bakery",
]
CATEGORICAL = ["location", "primary_type", "has_bar", "online_order", "book_table"] + CUISINE_FLAGS
PRICE_FEATURES = CATEGORICAL + ["n_cuisines"]
RATING_FEATURES = PRICE_FEATURES + ["cost_for_two"]

YES_NO = ["No", "Yes"]

# Exact levels in the training data (zomato_*_train.tab). train_models.py checks these against the data.
ALLOWED = {
    "location": [
        "BTM", "Banashankari", "Banaswadi", "Bannerghatta Road", "Basavanagudi",
        "Basaveshwara Nagar", "Bellandur", "Brigade Road", "Brookefield", "Domlur",
        "Electronic City", "Frazer Town", "HSR", "Indiranagar", "JP Nagar",
        "Jayanagar", "Jeevan Bhima Nagar", "Kalyan Nagar", "Kammanahalli",
        "Koramangala 1st Block", "Koramangala 4th Block", "Koramangala 5th Block",
        "Koramangala 6th Block", "Koramangala 7th Block", "Kumaraswamy Layout",
        "MG Road", "Majestic", "Malleshwaram", "Marathahalli", "Nagawara",
        "New BEL Road", "Old Airport Road", "Other", "Rajajinagar", "Residency Road",
        "Richmond Road", "Sarjapur Road", "Ulsoor", "Whitefield", "Yeshwantpur",
    ],
    "primary_type": [
        "Bakery", "Bar", "Beverage Shop", "Cafe", "Casual Dining", "Delivery",
        "Dessert Parlor", "Food Court", "Other", "Quick Bites", "Sweet Shop", "Takeaway",
    ],
    "has_bar": YES_NO,
    "online_order": YES_NO,
    "book_table": YES_NO,
    **{c: YES_NO for c in CUISINE_FLAGS},
}

# Min/max seen in the training data.
RANGES = {
    "n_cuisines": (1, 8),
    "cost_for_two": (40, 6000),
}

LABELS = {
    "location": "Location",
    "primary_type": "Restaurant type",
    "has_bar": "Serves alcohol",
    "online_order": "Online ordering",
    "book_table": "Table booking",
    "n_cuisines": "Number of cuisines",
    "cost_for_two": "Planned cost for two (₹)",
    **{c: c[2:].replace("_", " ") + " cuisine" for c in CUISINE_FLAGS},
}


def validate_inputs(inputs: dict, need_cost: bool = False) -> list[str]:
    """Return plain-English problems with the inputs; an empty list means they are fine.

    cost_for_two is only needed for the rating model (need_cost=True).
    """
    errors = []
    for field, allowed in ALLOWED.items():
        value = inputs.get(field)
        if value is None or value == "":
            errors.append(f"{LABELS[field]} is missing.")
        elif value not in allowed:
            if allowed is YES_NO:
                errors.append(f"{LABELS[field]} must be Yes or No (got '{value}').")
            else:
                errors.append(f"{LABELS[field]} '{value}' is not in the list of known options.")

    numeric = ["n_cuisines"] + (["cost_for_two"] if need_cost else [])
    for field in numeric:
        value = inputs.get(field)
        low, high = RANGES[field]
        if value is None or value == "":
            errors.append(f"{LABELS[field]} is missing.")
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            errors.append(f"{LABELS[field]} must be a number (got '{value}').")
            continue
        if not low <= number <= high:
            errors.append(f"{LABELS[field]} must be between {low} and {high} (got {value}).")

    if not errors:
        ticked = sum(inputs[c] == "Yes" for c in CUISINE_FLAGS)
        if ticked > float(inputs["n_cuisines"]):
            errors.append(
                f"You ticked {ticked} cuisines but entered {inputs['n_cuisines']} as the number of cuisines."
            )
    return errors


@lru_cache(maxsize=None)
def _load(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"{path.name} not found. Train it with train_models.py first.")
    return joblib.load(path)


def _frame(inputs: dict, features: list[str]) -> pd.DataFrame:
    row = {f: inputs[f] for f in features}
    for f in ("n_cuisines", "cost_for_two"):
        if f in row:
            row[f] = float(row[f])
    return pd.DataFrame([row], columns=features)


def predict_price(inputs: dict) -> float:
    """Predicted market cost for two (₹) from the Random Forest price model."""
    errors = validate_inputs(inputs)
    if errors:
        raise ValueError(" ".join(errors))
    model = _load(PRICE_MODEL_PATH)
    return float(model.predict(_frame(inputs, PRICE_FEATURES))[0])


def predict_rating(inputs: dict) -> float:
    """Probability that the restaurant is rated 4.0 or higher (Logistic Regression)."""
    errors = validate_inputs(inputs, need_cost=True)
    if errors:
        raise ValueError(" ".join(errors))
    model = _load(RATING_MODEL_PATH)
    proba = model.predict_proba(_frame(inputs, RATING_FEATURES))[0]
    return float(proba[list(model.classes_).index("Yes")])
