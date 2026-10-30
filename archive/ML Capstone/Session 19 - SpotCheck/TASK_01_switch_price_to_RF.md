# TASK 01 — Switch the PRICE model to Random Forest and build the model package

Follow `../CLAUDE.md`: Zomato/SpotCheck only; multiple-choice questions via AskUserQuestion; **edit existing files in place (no `_v2` copies)**; no LLM predictions. Work in this folder. Do not build any UI. There is no login in this project.

## Step 0 — Clarify first (AskUserQuestion, one batch)
1. Backup: **Yes, I have the original ML_Capstone.zip stored outside this folder (Recommended)** | No, stop so I can make one.
2. Random Forest size: **100 trees (Recommended)**, matches the Orange workflow, ~9 MB | 100 trees with min_samples_leaf=5, ~2.6 MB, re-check accuracy | 300 trees, more stable, bigger file.
3. Orange RF settings: **mirror whatever the .ows says (Recommended)** | use sklearn defaults and document the difference.
4. Demo / session dates known? **Yes, I'll type them** | Not yet, ask me later.
If question 1 is "No", stop. Record the answers in PROJECT_LOG.md.

## Step 1 — Orange workflow: edit `SpotCheck_workflow.ows` in place
- Parse the XML. Report the current price RF settings from its node properties (trees, depth, min split, replicable training).
- Rename nodes only: Random Forest (price) → "Random Forest (FINAL – price)"; Linear Regression (price) → "Linear Regression (comparison – price)".
- Add links: PRICE TRAIN → price RF learner (Data); price RF Model → "Predictions – PRICE hold-out" (Predictors). Keep all existing Linear Regression links for comparison.
- Do NOT edit base64/pickled widget properties. List the manual Orange GUI steps for me: tick "Replicable training", confirm 100 trees, add Feature Importance if available, then save the workflow (File → Save, same file name).
- Verify the XML still parses. Tell me to open the file in Orange to confirm it loads.

## Step 2 — Python models (new files: no Python files exist yet) → `spotcheck_model/`
`train_models.py`:
- **Price:** Pipeline[ColumnTransformer(OneHotEncoder(handle_unknown="ignore") on categoricals; n_cuisines passthrough) → RandomForestRegressor(n_estimators per Step 0, random_state=0)]. Train on `zomato_price_train.tab`. Save `price_model.joblib` (compress=3); report its size.
- **Rating:** replicate Orange's Logistic Regression (L2, C=1, Orange default preprocessing: one-hot + normalisation of continuous inputs). Train on `zomato_rating_train.tab`. Save `rating_model.joblib`. Check P(4.0+) for T01–T10 is within ±0.02 of Orange's values: T01 0.143, T02 0.175, T03 0.899, T04 0.104, T05 0.303, T06 0.273, T07 0.179, T08 0.203, T09 0.874, T10 0.815. Report each difference. If they don't match, explain why and ask me (multiple choice) before continuing.
- **Seed stability check:** retrain the price RF with 5 seeds (0–4) and report the per-restaurant spread on T01–T10 and hold-out MAE per seed. Expected: about ₹14–92 spread, MAE ₹148–160 with 100 trees. Ship seed 0.

`predict.py`:
- `predict_price(inputs: dict) -> float`, `predict_rating(inputs: dict) -> float` (probability). Load each `.joblib` once.
- `validate_inputs(inputs) -> list[str]`: exact allowed category lists taken from the training data, and min/max for n_cuisines and cost_for_two. Plain-English error messages.

`requirements.txt`: exact pinned versions of scikit-learn, pandas, numpy, joblib and streamlit used here.

## Step 3 — Evaluation: `evaluate.py` writes results INTO the existing workbook (Step 5), no separate results file
- Full 9,244 rows. Two schemes: 10-fold KFold (shuffle, random_state=1) AND 10-fold GroupKFold grouped by restaurant_name (chains share a name; ~40% of rows are chain outlets).
- Models: mean baseline, Linear Regression, Random Forest. Metrics: MAE, RMSE, R².
- Permutation feature importance for the RF price model, on held-out folds (never on training data), grouped back to the original input fields.
- Linear-regression assumption diagnostics with statsmodels on `zomato_price_train.tab`: RESET, Breusch–Pagan, Jarque–Bera, residual SD by fitted-value decile, GVIF.

## Step 4 — Reference tests: update `reference_tests.csv` in place (KEEP the 10-sample format)
- Do not change, reorder or remove any existing column or row (T01–T10).
- **Append** these columns at the end: Predicted cost (₹), Error (₹), Abs error (₹), P(4.0+), Predicted 4.0+ (0.5), Correct?
- Predictions must come from loading the `.joblib` files **through `predict.py`**, the same path the app uses.
- Leave `reference_tests_price.tab` and `reference_tests_rating.tab` unchanged; Orange's hold-out test reads them.
- `test_reference.py`: asserts `predict.py` reproduces the appended columns of `reference_tests.csv` (price ±₹1, probability ±0.001). This is the Session 21 integration check.

## Step 5 — Evidence workbook: edit `SpotCheck_Session19_Pack.xlsx` in place (openpyxl, keep formatting)
- **Summary:** Model 1 final = Random Forest. Replace "Why Linear Regression for price?" with "Why Random Forest for price?" using the Step 3 numbers. Update the hold-out result. Integration = Python app on Streamlit Community Cloud, models loaded from joblib (facilitator confirmed).
- **Model Comparison (CV):** add the GroupKFold table beside the existing one.
- **Hold-out Test:** keep the exact row-by-row layout. Replace the price predictions with the RF values from Step 4 and recompute MAE. Update the rating columns to the Python LR values. Add a note: Orange and Python RF differ by ~₹14–92 per row; the app reproduces the Python values.
- Rename "Price Coefficients" to **"LR Coefficients (comparison)"**. Add a note: Orange lists both Yes and No levels; the Yes-vs-No effect is the difference (e.g. book_table +₹416, not +₹208).
- Add sheets **"RF Feature Importance"** and **"Assumption Checks"** (from Step 3), each with a one-line verdict per check.

## Step 6 — Repo package and log
- Fill `repo/` (keep its CLAUDE.md) with copies of: predict.py, both .joblib files, requirements.txt, test_reference.py, reference_tests.csv. Add README.md (file guide, retraining steps, Kaggle attribution) and a .gitignore excluding raw data and `*.tab`.
- Create `PROJECT_LOG.md` (no log exists yet) with a dated entry: LR → RF for price; the evidence (CV, GroupKFold, assumption checks); change from the proposal ("coded as formulas" → Python model on Streamlit, confirmed by facilitator); no login (team decision); seed-stability result; open items.

## Finish
Run `python test_reference.py` and show the result. Show the DEMO READINESS block from CLAUDE.md. Then reply in at most 5 bullets: files edited in place, files created (and why each was needed), key numbers, anything that didn't reproduce, manual Orange steps for me.
