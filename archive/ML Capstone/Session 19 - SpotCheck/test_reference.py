"""Integration check (Session 21): predict.py must reproduce the expected outputs in reference_tests.csv.

Run:  python test_reference.py      (or: pytest test_reference.py)
Price within ±₹1, probability within ±0.001, and the 0.5 verdict must match.
"""
from pathlib import Path

import pandas as pd

from predict import predict_price, predict_rating

REFERENCE_CSV = Path(__file__).resolve().parent / "reference_tests.csv"
PRICE_TOL = 1.0
PROB_TOL = 0.001


def load_reference() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_CSV, dtype=str, keep_default_na=False)


def check_row(row) -> list[str]:
    """Return the problems for one reference restaurant (empty list = pass)."""
    problems = []
    price = predict_price(row.to_dict())
    if abs(price - float(row["Predicted cost (₹)"])) > PRICE_TOL:
        problems.append(f"price {price:.1f}, expected {row['Predicted cost (₹)']}")
    prob = predict_rating(row.to_dict())
    if abs(prob - float(row["P(4.0+)"])) > PROB_TOL:
        problems.append(f"P(4.0+) {prob:.4f}, expected {row['P(4.0+)']}")
    verdict = "Yes" if prob >= 0.5 else "No"
    if verdict != row["Predicted 4.0+ (0.5)"]:
        problems.append(f"verdict {verdict}, expected {row['Predicted 4.0+ (0.5)']}")
    return problems


def test_reference_outputs():
    for _, row in load_reference().iterrows():
        problems = check_row(row)
        assert not problems, f"{row['TestID']}: " + "; ".join(problems)


if __name__ == "__main__":
    ref = load_reference()
    print(f"{'Test':5s} {'Restaurant':28s} {'Expected ₹':>10s} {'predict.py ₹':>12s} {'Exp. P':>7s} {'P':>7s}  OK")
    failures = 0
    for _, row in ref.iterrows():
        problems = check_row(row)
        failures += bool(problems)
        print(f"{row['TestID']:5s} {row['restaurant_name'][:28]:28s} {float(row['Predicted cost (₹)']):10.1f} "
              f"{predict_price(row.to_dict()):12.1f} {float(row['P(4.0+)']):7.4f} {predict_rating(row.to_dict()):7.4f}  "
              f"{'✔' if not problems else '✘ ' + '; '.join(problems)}")
    print(f"\n{len(ref) - failures}/{len(ref)} restaurants match (price ±₹{PRICE_TOL:.0f}, P(4.0+) ±{PROB_TOL}, verdict at 0.5).")
    if failures:
        raise SystemExit("FAILED")
    print("PASSED")
