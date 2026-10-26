# SpotCheck

Restaurant concept, price and rating validator for Bangalore (MICA ML Capstone).
A restaurant owner describes a planned restaurant; SpotCheck predicts the market
cost for two (Random Forest) and the chance of a 4.0+ Zomato rating (Logistic Regression).

Mobile-first Streamlit app: a 4-step wizard (Where → Format → Menu → Price), results with a live
price slider, swipeable what-if comparison, a downloadable summary and an About page.
There is no login: the app opens directly at the form, and nothing is stored on a server.
Not affiliated with Zomato.

## Files

| File | What it is |
|---|---|
| `app.py` | The Streamlit app. Gets every number from `predict.py`; adds only the verdict rules (price band ± ₹136, Strong ≥ 60%, Moderate ≥ 30%). |
| `.streamlit/config.toml` | Theme (red #E23744, light background). |
| `predict.py` | Loads each model once; `predict_price()`, `predict_rating()`, `validate_inputs()`. The app calls only these. |
| `price_model.joblib` | FINAL price model: Random Forest regression, 100 trees, `random_state=0`, trained on 9,234 restaurants. |
| `rating_model.joblib` | FINAL rating model: Logistic Regression (L2, C=1), trained on 9,234 restaurants. Matches Orange's predictions within 0.002. |
| `requirements.txt` | Exact library versions. The models must be loaded with the scikit-learn version that saved them. |
| `reference_tests.csv` | The 10 hold-out restaurants (T01–T10) with the expected model outputs in the last columns. |
| `test_reference.py` | Integration check: `predict.py` must reproduce `reference_tests.csv` (price ±₹1, probability ±0.001). |
| `test_app.py` | App check: the app shows the reference outputs for all 10 restaurants and every page renders. |

## Run the app and the checks

```bash
pip install -r requirements.txt
streamlit run app.py
python test_reference.py
python test_app.py
```

Both checks must print `PASSED` before every push.

## Retraining

Training and evaluation run in the parent project folder, which holds the data (the data is not in this repo):

1. `python train_models.py` (or `price` / `rating` for one model): trains and saves the `.joblib` files (fixed `random_state=0`).
2. `python evaluate.py`: cross-validation, feature importance and assumption checks; appends the new
   expected outputs to `reference_tests.csv` and updates the evidence workbook.
3. Copy `app.py`, `test_app.py`, `.streamlit/config.toml`, `predict.py`, the `.joblib` files, `requirements.txt`, `test_reference.py` and `reference_tests.csv` here.
4. `python test_reference.py` and `python test_app.py` must pass. Log the change in `PROJECT_LOG.md`.

Retraining changes the expected outputs, so never retrain without updating `reference_tests.csv`.

## Data and attribution

Built on the **Zomato Bangalore Restaurants** dataset by Himanshu Poddar, Kaggle:
https://www.kaggle.com/datasets/himanshupoddar/zomato-bangalore-restaurants
(scraped from Zomato, about 2019). The raw data is not included in this repository;
download it from Kaggle under its licence. Only the 10 reference restaurants are included, as test inputs.
