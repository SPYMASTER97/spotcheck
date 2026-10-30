"""Train the SpotCheck models and save them as .joblib files.

Price (FINAL): Random Forest regression on cost_for_two, settings mirrored from
SpotCheck_workflow.ows (100 trees, replicable training, Orange defaults:
min_samples_split=5, all features considered at each split, no depth limit).

Rating (FINAL): Logistic Regression (L2, C=1, lbfgs) on high_rating, mirroring the
Orange LR widget (Ridge, C=1). One-hot categoricals; n_cuisines and cost_for_two
standardised. Checked against the Orange GUI's P(4.0+) for T01-T10 (see PROJECT_LOG.md).

Run:  python train_models.py            (both models)
      python train_models.py price      (price only)
      python train_models.py rating     (rating only)
Retraining changes the reference outputs: afterwards run evaluate.py (updates
reference_tests.csv and the evidence workbook) and log it in PROJECT_LOG.md.
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from predict import (ALLOWED, CATEGORICAL, PRICE_FEATURES, PRICE_MODEL_PATH, RANGES,
                     RATING_FEATURES, RATING_MODEL_PATH)

HERE = Path(__file__).resolve().parent
N_TREES = 100
SEED = 0

# Orange GUI, "Predictions – RATING hold-out" (Logistic Regression, Ridge C=1), P(4.0+) for T01-T10, 2026-10-26.
ORANGE_GUI_P = [0.092, 0.061, 0.917, 0.141, 0.224, 0.229, 0.138, 0.211, 0.912, 0.785]
ORANGE_TOLERANCE = 0.02


def load_tab(name: str) -> pd.DataFrame:
    """Read an Orange .tab file (3 header rows: names, types, roles)."""
    return pd.read_csv(HERE / name, sep="\t", skiprows=[1, 2], keep_default_na=False)


def price_pipeline(seed: int = SEED) -> Pipeline:
    encode = ColumnTransformer(
        [("onehot", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)],
        remainder="passthrough",  # n_cuisines
    )
    forest = RandomForestRegressor(
        n_estimators=N_TREES,
        min_samples_split=5,
        max_features=1.0,
        random_state=seed,
        n_jobs=-1,
    )
    return Pipeline([("encode", encode), ("forest", forest)])


def rating_pipeline() -> Pipeline:
    encode = ColumnTransformer([
        ("onehot", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ("scale", StandardScaler(), ["n_cuisines", "cost_for_two"]),
    ])
    logit = LogisticRegression(C=1.0, solver="lbfgs", max_iter=5000)  # L2 is the default penalty
    return Pipeline([("encode", encode), ("logit", logit)])


def check_allowed_inputs(train: pd.DataFrame) -> None:
    """Fail loudly if predict.py's allowed lists/ranges drift from the training data."""
    for field, allowed in ALLOWED.items():
        found = sorted(train[field].unique())
        assert found == sorted(allowed), f"{field}: predict.py lists {allowed}, data has {found}"
    for field, (low, high) in RANGES.items():
        found = (train[field].min(), train[field].max())
        assert found == (low, high), f"{field}: predict.py range {(low, high)}, data has {found}"


def train_price() -> None:
    train = load_tab("zomato_price_train.tab")
    holdout = load_tab("reference_tests_price.tab")
    check_allowed_inputs(train)
    X, y = train[PRICE_FEATURES], train["cost_for_two"]

    model = price_pipeline(SEED).fit(X, y)
    joblib.dump(model, PRICE_MODEL_PATH, compress=3)
    size_mb = PRICE_MODEL_PATH.stat().st_size / 1e6
    print(f"Saved {PRICE_MODEL_PATH.name}: {size_mb:.1f} MB (seed {SEED}, {N_TREES} trees)")

    # Seed stability: same settings, seeds 0-4, scored on the 10 hold-out restaurants.
    preds, maes = {}, {}
    for seed in range(5):
        m = model if seed == SEED else price_pipeline(seed).fit(X, y)
        p = m.predict(holdout[PRICE_FEATURES])
        preds[seed] = p
        maes[seed] = np.mean(np.abs(p - holdout["cost_for_two"]))
    table = pd.DataFrame(preds, index=holdout["TestID"]).round(1)
    table["spread (max-min)"] = (table.max(axis=1) - table.min(axis=1)).round(1)
    print("\nSeed stability: predicted cost (₹) on T01-T10 per seed")
    print(table.to_string())
    print("\nHold-out MAE (₹) per seed: " + ", ".join(f"seed {s}: {v:.1f}" for s, v in maes.items()))
    print(f"Spread range: ₹{table['spread (max-min)'].min():.0f}-{table['spread (max-min)'].max():.0f};"
          f" MAE range: ₹{min(maes.values()):.0f}-{max(maes.values()):.0f}. Shipped: seed {SEED}.")


def train_rating() -> None:
    train = load_tab("zomato_rating_train.tab")
    holdout = load_tab("reference_tests_rating.tab")
    check_allowed_inputs(train)

    model = rating_pipeline().fit(train[RATING_FEATURES], train["high_rating"])
    joblib.dump(model, RATING_MODEL_PATH, compress=3)
    size_kb = RATING_MODEL_PATH.stat().st_size / 1e3
    print(f"Saved {RATING_MODEL_PATH.name}: {size_kb:.0f} KB (L2, C=1, lbfgs)")

    # Check against Orange's own output for the 10 hold-out restaurants.
    p = model.predict_proba(holdout[RATING_FEATURES])[:, list(model.classes_).index("Yes")]
    diff = p - np.array(ORANGE_GUI_P)
    table = pd.DataFrame({"Python P(4.0+)": p.round(3), "Orange GUI": ORANGE_GUI_P, "diff": diff.round(4)},
                         index=holdout["TestID"])
    print("\nRating check vs Orange GUI (P(4.0+), T01-T10)")
    print(table.to_string())
    correct = ((p >= 0.5) == (holdout["high_rating"] == "Yes")).sum()
    print(f"Max |diff| = {abs(diff).max():.4f} (tolerance {ORANGE_TOLERANCE}); hold-out correct at 0.5: {correct}/10")
    assert abs(diff).max() <= ORANGE_TOLERANCE, "Python rating model does not reproduce Orange within tolerance"


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("both", "price"):
        train_price()
    if which in ("both", "rating"):
        train_rating()


if __name__ == "__main__":
    main()
