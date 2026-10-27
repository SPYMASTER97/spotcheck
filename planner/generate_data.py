"""Generate the SYNTHETIC planning dataset for the SpotCheck "Plan" chat.

Inputs that already exist in the real Zomato data are kept as they are (read-only):
location, primary_type, has_bar, online_order, book_table, the 12 cuisine flags,
n_cuisines and cost_for_two (from ../zomato_rating_train.tab and ../reference_tests.csv).

Everything else is SYNTHETIC:
- Six extra inputs the chat asks for (guests per day, opening hours, delivery share,
  menu size, alcohol share, taking over an existing restaurant), drawn from normal
  distributions (clipped to sensible ranges) or a coin flip.
- Five targets, each a straight-line (linear) formula of the inputs plus normally
  distributed noise, so Linear Regression is the correct model by construction.
  The formulas are in TRUE_RULES below. They are illustrative industry-style
  assumptions, NOT measured Bangalore facts, and every answer built on them must
  be labelled "estimate from synthetic data".

Run:  python planner/generate_data.py
Writes planner/data/planner_train.csv / .tab (9,234 rows) and planner_holdout.csv / .tab (T01-T10).
Fixed seed, so re-running reproduces the same files.
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
DATA = HERE / "data"
SEED = 19

CUISINES = ["c_North_Indian", "c_Chinese", "c_South_Indian", "c_Fast_Food", "c_Biryani", "c_Desserts",
            "c_Beverages", "c_Continental", "c_Cafe", "c_Street_Food", "c_Italian", "c_Bakery"]
REAL_INPUTS = ["location", "primary_type", "has_bar", "online_order", "book_table", *CUISINES,
               "n_cuisines", "cost_for_two"]

# Synthetic extra inputs: (mean, sd, low, high) of a clipped normal, rounded to `decimals`.
EXTRA_NORMAL = {
    "guests_per_day": (120, 40, 20, 350, 0),    # dine-in + takeaway guests on a typical day
    "opening_hours": (12, 2, 6, 18, 1),          # hours open per day
    "menu_items": (None, 12, 10, 150, 0),        # mean = 25 + 8 x n_cuisines
    "delivery_share": (None, 12, 0, 90, 0),      # % of orders delivered; mean 40 if online ordering else 5
    "alcohol_share": (None, 8, 5, 60, 0),        # % of sales from alcohol; 0 when has_bar = No
}
TAKEOVER_P = 0.35  # chance the owner takes over an existing restaurant site (cheaper fit-out)

# Location effect: each area's median real cost for two relative to the city median (from the real data).
TRUE_RULES = {
    "floor_area_sqft": {
        "intercept": 350, "noise_sd": 100,
        "numeric": {"guests_per_day": 3.0, "delivery_share": -2.5, "cost_for_two": 0.25, "n_cuisines": 40},
        "yes": {"book_table": 250, "has_bar": 300},
        "type": {"Bar": 400, "Casual Dining": 300, "Other": 100, "Cafe": 0, "Quick Bites": -150,
                 "Dessert Parlor": -200, "Bakery": -200, "Sweet Shop": -200, "Beverage Shop": -250,
                 "Food Court": -200, "Takeaway": -200, "Delivery": -250},
        "location_index": 0,
    },
    "staff_count": {
        "intercept": -1, "noise_sd": 1.2,
        "numeric": {"guests_per_day": 0.03, "opening_hours": 0.2, "n_cuisines": 0.5, "cost_for_two": 0.003,
                    "menu_items": 0.02, "delivery_share": 0.02},
        "yes": {"has_bar": 2.0, "book_table": 1.0},
        "type": {"Bar": 4, "Casual Dining": 3, "Other": 1, "Cafe": 0, "Quick Bites": -1, "Dessert Parlor": -2,
                 "Bakery": -2, "Sweet Shop": -2, "Beverage Shop": -2, "Food Court": -2, "Takeaway": -2,
                 "Delivery": -2},
        "location_index": 0,
    },
    "investment_lakh": {  # initial investment, ₹ lakh (1 lakh = ₹100,000)
        "intercept": 6, "noise_sd": 5,
        "numeric": {"guests_per_day": 0.06, "cost_for_two": 0.015, "n_cuisines": 1.5},
        "yes": {"has_bar": 20, "book_table": 5, "takeover": -6},
        "type": {"Bar": 35, "Casual Dining": 25, "Other": 10, "Cafe": 10, "Quick Bites": 0, "Dessert Parlor": 0,
                 "Bakery": 3, "Sweet Shop": 0, "Beverage Shop": -3, "Food Court": -4, "Takeaway": -4,
                 "Delivery": -5},
        "location_index": 15,  # premium areas: higher deposits and fit-out
    },
    "food_cost_pct": {  # ingredients as % of sales
        "intercept": 31, "noise_sd": 2.0,
        "numeric": {"menu_items": 0.04, "cost_for_two": -0.002, "alcohol_share": -0.15},
        "yes": {"c_Continental": 2, "c_Italian": 2, "c_Biryani": 2, "c_North_Indian": 1, "c_Fast_Food": 0,
                "c_Chinese": -1, "c_Desserts": -1, "c_Street_Food": -1, "c_South_Indian": -2, "c_Bakery": -2,
                "c_Cafe": -3, "c_Beverages": -4},
        "type": {},
        "location_index": 0,
    },
    "revenue_lakh": {  # monthly sales, ₹ lakh
        "intercept": -3, "noise_sd": 1.2,
        "numeric": {"guests_per_day": 0.03, "cost_for_two": 0.006, "delivery_share": 0.03, "opening_hours": 0.25},
        "yes": {"has_bar": 2},
        "type": {"Bar": 2, "Casual Dining": 1, "Other": 1, "Cafe": 0, "Quick Bites": -1, "Dessert Parlor": -1,
                 "Bakery": -1, "Sweet Shop": -1, "Beverage Shop": -1, "Food Court": -1, "Takeaway": -1,
                 "Delivery": -1},
        "location_index": 2,
    },
}
TARGETS = list(TRUE_RULES)
# Physical floor for each target. Values below it are raised to it; generate_data.py prints how many (a handful).
MINIMUM = {"floor_area_sqft": 100, "staff_count": 2, "investment_lakh": 2, "food_cost_pct": 15, "revenue_lakh": 0.5}


def load_tab(path: Path) -> pd.DataFrame:
    """Read an Orange .tab file (3 header rows: names, types, roles)."""
    return pd.read_csv(path, sep="\t", skiprows=[1, 2], keep_default_na=False)


def location_index(train: pd.DataFrame) -> dict[str, float]:
    """Each area's median real cost for two divided by the city median, minus 1 (0 = typical area)."""
    city = train["cost_for_two"].median()
    return (train.groupby("location")["cost_for_two"].median() / city - 1).round(3).to_dict()


def add_extras(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    out = df.copy()
    n = len(out)
    means = {
        "guests_per_day": np.full(n, 120.0),
        "opening_hours": np.full(n, 12.0),
        "menu_items": 25 + 8 * out["n_cuisines"].to_numpy(float),
        "delivery_share": np.where(out["online_order"] == "Yes", 40.0, 5.0),
        "alcohol_share": np.full(n, 30.0),
    }
    for col, (_, sd, low, high, decimals) in EXTRA_NORMAL.items():
        out[col] = np.clip(rng.normal(means[col], sd), low, high).round(decimals)
    out.loc[out["has_bar"] == "No", "alcohol_share"] = 0
    out["takeover"] = np.where(rng.random(n) < TAKEOVER_P, "Yes", "No")
    return out


def true_value(df: pd.DataFrame, rule: dict, loc_idx: dict[str, float]) -> np.ndarray:
    """The noiseless straight-line formula for one target."""
    value = np.full(len(df), float(rule["intercept"]))
    for col, coef in rule["numeric"].items():
        value += coef * df[col].to_numpy(float)
    for col, coef in rule["yes"].items():
        value += coef * (df[col] == "Yes").to_numpy(float)
    value += df["primary_type"].map(rule["type"]).fillna(0).to_numpy(float)
    value += rule["location_index"] * df["location"].map(loc_idx).fillna(0).to_numpy(float)
    return value


def add_targets(df: pd.DataFrame, rng: np.random.Generator, loc_idx: dict[str, float]) -> pd.DataFrame:
    out = df.copy()
    for target, rule in TRUE_RULES.items():
        value = true_value(out, rule, loc_idx) + rng.normal(0, rule["noise_sd"], len(out))
        out[target] = np.maximum(value, MINIMUM[target]).round(1)
        raised = int((value < MINIMUM[target]).sum())
        if raised:
            print(f"{target}: {raised} of {len(out)} rows raised to the minimum {MINIMUM[target]}")
    return out


def write_tab(df: pd.DataFrame, path: Path) -> None:
    """Orange .tab: all 5 targets are meta; pick one as target in Orange (File widget → role)."""
    types, roles = [], []
    for col in df.columns:
        numeric = pd.api.types.is_numeric_dtype(df[col])
        types.append("string" if col in ("TestID", "restaurant_name") else "continuous" if numeric else "discrete")
        roles.append("meta" if col in ("TestID", "restaurant_name", *TARGETS) else "")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\t".join(df.columns) + "\n" + "\t".join(types) + "\n" + "\t".join(roles) + "\n")
        df.to_csv(f, sep="\t", index=False, header=False)


def main() -> None:
    DATA.mkdir(exist_ok=True)
    real_train = load_tab(PROJECT / "zomato_rating_train.tab")
    real_holdout = pd.read_csv(PROJECT / "reference_tests.csv", dtype=str, keep_default_na=False)
    for col in ("n_cuisines", "cost_for_two"):
        real_holdout[col] = real_holdout[col].astype(float).astype(int)
    loc_idx = location_index(real_train)

    rng = np.random.default_rng(SEED)
    train = add_targets(add_extras(real_train[["restaurant_name", *REAL_INPUTS]], rng), rng, loc_idx)
    holdout = add_targets(add_extras(real_holdout[["TestID", "restaurant_name", *REAL_INPUTS]], rng), rng, loc_idx)

    for name, df in (("planner_train", train), ("planner_holdout", holdout)):
        df.to_csv(DATA / f"{name}.csv", index=False)
        write_tab(df, DATA / f"{name}.tab")
    pd.Series(loc_idx, name="location_index").rename_axis("location").to_csv(DATA / "location_index.csv")
    print(f"train {train.shape}, holdout {holdout.shape}")
    print(train[TARGETS].describe().round(1).T[["mean", "std", "min", "50%", "max"]])
    print(train.groupby("primary_type")[TARGETS].median().round(1))


if __name__ == "__main__":
    main()
