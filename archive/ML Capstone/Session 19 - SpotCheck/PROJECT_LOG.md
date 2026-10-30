# SpotCheck – Project Log

Decisions, evidence and open items. Newest entries at the bottom.

## Project facts

- **Live app URL:** https://spotcheck-tbcb5npizuvfmpfgto7a2a.streamlit.app/ (first deployed 2026-10-27 from GitHub SPYMASTER97/spotcheck, branch `main`, `app.py`).
- **Demo / session dates:** no separate demo dates. The work is done and shown in the class sessions (team answer, 2026-10-26).

---

## 2026-10-26 – TASK 01: price model switched from Linear Regression to Random Forest

### Step 0 answers (team, via multiple-choice questions)
- Backup: the original `ML_Capstone.zip` is stored outside the project folder.
- Random Forest size: 100 trees (matches the Orange workflow).
- RF settings: mirror the Orange workflow (`SpotCheck_workflow.ows`).
- Dates: no separate demo dates; work is done in class sessions.

### Decision: final price model = Random Forest regression (was Linear Regression)
**Why:** Random Forest is clearly more accurate, and the integration route no longer needs a formula.

Evidence (`evaluate.py`, all 9,244 restaurants, pooled out-of-fold predictions):

| Model | KFold MAE | KFold RMSE | KFold R² | GroupKFold MAE | GroupKFold RMSE | GroupKFold R² |
|---|---|---|---|---|---|---|
| Mean baseline | ₹276 | ₹427 | 0.00 | ₹276 | ₹427 | 0.00 |
| Linear Regression | ₹164 | ₹267 | 0.61 | ₹165 | ₹268 | 0.61 |
| **Random Forest (100 trees)** | **₹136** | **₹222** | **0.73** | **₹144** | **₹227** | **0.72** |

- KFold: 10 folds, shuffled, random_state=1. Python's Linear Regression reproduces Orange's CV exactly (MAE ₹164.3, R² 0.608), which confirms the setup. Orange's RF CV was R² 0.714, MAE ₹139.
- GroupKFold (10 folds, grouped by `restaurant_name`): about 40% of rows are chain outlets sharing a name. Keeping each chain in one fold is the stricter test. RF loses a little (R² 0.73 → 0.72) but still clearly beats Linear Regression.
- Linear Regression assumption checks (statsmodels, OLS on `zomato_price_train.tab`, R² 0.616):
  - Linearity, RESET F = 446, p < 0.001: **violated**.
  - Equal spread, Breusch–Pagan LM = 1,981, p < 0.001: **violated**. Residual SD rises from ₹118 in the lowest fitted decile to ₹611 in the highest (5.2×).
  - Normal errors, Jarque–Bera = 266,298, p < 0.001; skew 2.6, kurtosis 28.8: **violated**.
  - Multicollinearity (GVIF): only `c_Cafe` is above the threshold (2.46 > 2.24, ≈ VIF 6) because it overlaps with primary_type = Cafe. All other fields are fine.
- RF permutation importance (MAE increase when the field is shuffled, held-out folds only): restaurant type ₹94, serves alcohol ₹50, table booking ₹37, number of cuisines ₹11, Cafe cuisine ₹10. Location is only ₹6 once type/bar/booking are known.

### Decision: Python Random Forest settings
- Mirrored from the `.ows` price RF node: 100 trees, replicable training (`random_state=0`). Its other settings are not stored, so Orange's widget defaults apply: `min_samples_split=5`, all features at each split, no depth limit.
- One-hot encoding of the 17 categorical inputs (`handle_unknown="ignore"`); `n_cuisines` passed through.
- `price_model.joblib` = 7.7 MB (compress=3), trained on 9,234 rows with seed 0.

### Seed-stability check (seeds 0–4, same settings, 10 hold-out restaurants)
- Spread of predicted cost per restaurant across seeds: **₹5–56** (T01 ₹5 … T10 ₹56).
- Hold-out MAE per seed: ₹151.6, 142.8, 142.0, 145.4, 149.4 (**₹142–152**).
- This is tighter than the ₹14–92 / ₹148–160 noted earlier in CLAUDE.md. Those figures were probably measured with different forest settings; the numbers above are as measured. **Seed 0 shipped.**
- Consequence: Orange's RF and the Python RF give different per-row numbers. The reference outputs therefore come from `price_model.joblib` via `predict.py` (hold-out MAE ₹151.5; Orange RF ₹158; former Linear Regression ₹184).

### Change from the proposal
- Proposal: models "coded as formulas" in the app. **Now:** Python app (Streamlit) → GitHub → Streamlit Community Cloud. The app loads the trained `.joblib` models through `predict.py` (confirmed by the facilitator). This is what makes a Random Forest usable for price.
- **No login** (team decision; matches the Capstone Hub P3 spec, "Version 1 excludes: login, user profiles…"). The app starts directly at the input form.

### Rating model: Python version PAUSED
- Orange's Logistic Regression could not be reproduced in Python within ±0.02. The workbook's Orange coefficients reproduce Orange's P(4.0+) exactly, using raw `cost_for_two` and both Yes/No levels, so Orange did not normalise continuous inputs. But every sklearn fit gives coefficients up to 5× less shrunk for rare locations. Variants tried: one-hot with/without normalisation, liblinear/lbfgs, C 0.02–1, full data, balanced classes. Gaps on T01–T10 were up to 0.09 at C=1 (T02: 0.08 vs 0.175).
- The sklearn LR itself performs as well: CV AUC 0.812 vs Orange 0.804; 9/10 correct on the hold-out, the same as Orange.
- **Team decision:** stop the Python rating model until Orange's LR widget/preprocessing has been inspected. Until then, `rating_model.joblib` does not exist and `predict_rating()` raises a clear error. The rating columns of `reference_tests.csv` are blank, `test_reference.py` skips rating, and the workbook keeps Orange's rating values.

### Files changed in place
- `SpotCheck_workflow.ows`: renamed "Random Forest 100 (price)" → "Random Forest (FINAL – price)" and "Linear Regression (FINAL – price)" → "Linear Regression (comparison – price)". Added links PRICE TRAIN → price RF (Data) and price RF Model → "Predictions – PRICE hold-out" (Predictors). LR links kept. No widget properties edited; the XML still parses.
- `reference_tests.csv`: appended Predicted cost (₹), Error (₹), Abs error (₹), P(4.0+), Predicted 4.0+ (0.5), Correct?. The original 23 columns are byte-identical; the rating columns are blank (paused).
- `SpotCheck_Session19_Pack.xlsx`:
  - Summary: final price model, "Why Random Forest for price?", hold-out result, new Integration row.
  - Model Comparison (CV): Python KFold vs GroupKFold table added beside the Orange table.
  - Hold-out Test: RF predictions plus notes.
  - Reference Tests: predicted price = RF; price band = RF CV MAE ₹136.
  - "Price Coefficients" renamed "LR Coefficients (comparison)", with a note on Yes-vs-No (book_table +₹416, not +₹208).
  - New sheets "RF Feature Importance" and "Assumption Checks".
- Not changed: `reference_tests_price.tab`, `reference_tests_rating.tab`, all `zomato_*` data files.

### Files created (no existing file could hold them)
- `train_models.py`, `predict.py`, `evaluate.py`, `test_reference.py`: no Python code existed.
- `price_model.joblib`: the trained model the app loads.
- `requirements.txt`: scikit-learn 1.9.1, pandas 3.1.0, numpy 2.5.4, scipy 1.18.1, joblib 1.6.0, streamlit 1.66.1 (trained under Python 3.14). `evaluate.py` also needs statsmodels 0.15.0 and openpyxl 3.1.5.
- `repo/`: copies of the files above plus `README.md` (Kaggle attribution, retraining) and `.gitignore` (raw data, `*.tab`, secrets).
- `PROJECT_LOG.md`: this log.

### Integration check
- `python test_reference.py` → PASSED: price 10/10 within ±₹1; rating skipped (paused).

### Open items
1. Inspect Orange's Logistic Regression widget/preprocessing, then decide how to build `rating_model.joblib`. Then fill the rating columns of `reference_tests.csv` and the Hold-out sheet.
2. Manual Orange steps (the `.ows` can't safely be edited for these): confirm "Replicable training" is ticked and 100 trees on the price RF, add Feature Importance, then save the workflow under the same name.
3. The `.ows` scheme description and the "PRICE coefficients (final model)" Data Table title still say Linear Regression is final. Rename them in Orange when saving (not edited, because the task allowed renaming only the two nodes).
4. Streamlit Community Cloud: choose a Python version for which the pinned versions install (the models were saved under Python 3.14 with scikit-learn 1.9.1). Check this at the first deploy.
5. `app.py` waits for the Google Stitch screen designs.

## 2026-10-26 – Orange check: Random Forest widgets opened with non-default settings
- **Finding:** the `.ows` stores only "100 trees" and "Replicable training" for both RF widgets. For every other setting, Orange uses the values last used on this computer. So both RFs opened with: attributes per split = 3, Balance class distribution on, depth limit 5, min split 10. That is not the RF behind the workbook's CV numbers or the Python model.
- **Also found:** both HOLD-OUT Test & Score widgets opened with no evaluation option selected. The saved settings have no version number, so Orange 3.39 shifts "Test on test data" (5) to an option that doesn't exist (6), and the widget crashes.
- **Action (manual, in Orange):** price RF set to: no attribute limit, no class balancing, no depth limit, min split 5. This mirrors Orange's defaults and `train_models.py`. "Test on test data" re-selected in both hold-out widgets. The saved `.ows` (14:19) confirms both. Orange's save now writes all settings with version numbers.
- **Not yet done:** the rating RF (comparison only) is still saved with attributes per split = 3, depth limit 5, min split 10 and class balancing on.
- **Result, Orange GUI price hold-out (Test on test data) after the fix:**
  - Random Forest: MAE ₹151.7, RMSE ₹207.0, R² 0.853. Python RF seed 0: MAE ₹151.5, so the two agree within ₹0.2 on average.
  - Before the fix (depth 5, 3 attributes): MAE ₹250.2, R² 0.488.
  - Constant ₹432.6 and Tree depth 5 ₹196.6 match the workbook exactly.
- **Still open:** Orange GUI Linear Regression hold-out MAE is ₹185.1 (R² 0.754), but the workbook says ₹183.9 (R² 0.760). LR has no randomness, so these should be identical. Also, the workbook's Orange RF hold-out (₹158) differs from the GUI's ₹151.7. The workbook's Orange numbers may not come from this GUI workflow. The same could explain the rating LR mismatch.

## 2026-10-26 – Workbook hold-out rows updated to the Orange GUI results (team request)
- `SpotCheck_Session19_Pack.xlsx` → Hold-out Test, rows 5 and 7:
  - Linear Regression: RMSE 268.125, MAE ₹185.075, R² 0.754 (was 264.9 / 183.9 / 0.760).
  - Random Forest: RMSE 206.970, MAE ₹151.730, R² 0.853 (was 227.6 / 157.9 / 0.823).
- Constant and Tree rows unchanged (they already matched). Notes A33/A35 and Summary B18 updated: Orange RF ₹152, Python RF ₹151.5, LR ₹185.
- The numbers are stored as `ORANGE_HOLDOUT` in `evaluate.py`, so a re-run keeps them. `test_reference.py` still PASSES.
- **Orange GUI price 10-fold CV after the RF fix** (all 9,244 rows; Orange's own fold split):

| Model | RMSE | MAE | R² |
|---|---|---|---|
| Constant | ₹426.9 | ₹276.1 | 0.000 |
| Linear Regression | ₹267.2 | ₹164.4 | 0.608 |
| Tree depth 5 | ₹247.7 | ₹153.8 | 0.663 |
| Random Forest | ₹223.7 | ₹136.8 | 0.725 |

  This agrees with the Python KFold RF (MAE ₹136.4, R² 0.730). Orange's model-comparison table gives a 0.999 probability that RF has lower MSE than Linear Regression. The workbook's 'Model Comparison (CV)' Orange table (RF R² 0.714, MAE ₹138.5) is from an earlier run and is not yet replaced.

## 2026-10-26 – Workbook CV table updated to the Orange GUI results (team request)
- `SpotCheck_Session19_Pack.xlsx` → Model Comparison (CV), price rows 4–7, replaced with the Orange GUI 10-fold CV above:
  - Constant: was ₹276.1, R² 0.000. Now ₹276.1, R² 0.000.
  - Linear Regression: was ₹164.3, R² 0.608. Now ₹164.4, R² 0.608.
  - Tree depth 5: was ₹155.4, R² 0.670. Now ₹153.8, R² 0.663.
  - Random Forest: was ₹138.5, R² 0.714. Now ₹136.8, R² 0.725.
- Note A22 rewritten to say where the numbers come from. The rating table is unchanged (earlier Orange run).
- Summary "Why Random Forest for price?" now also cites Orange: RF R² 0.725, MAE ₹137 vs LR R² 0.608, MAE ₹164.
- Stored as `ORANGE_CV` in `evaluate.py`, so re-runs keep them. `test_reference.py` still PASSES.

## 2026-10-26 – Linear Regression hold-out: ₹183.9 vs ₹185.1 investigated
- The Orange LR widget settings are correct (Fit intercept on, No regularization; 84 coefficients = intercept + 83 inputs).
- Plain OLS in Python (sklearn LinearRegression, one-hot, trained on `zomato_price_train.tab`) gives hold-out RMSE 264.888, MAE ₹183.912, R² 0.760. The per-row predictions are 294.9, 628.3, 919.6, … This matches the ORIGINAL workbook exactly. So the original ₹183.9 was the correct OLS result.
- The Orange 3.39 GUI LR gives ₹185.075 on the same data and settings. Constant and Tree match exactly, so the data is identical, and the gap must come from inside Orange's LR learner. Cause not identified. LR is comparison-only, so this does not affect the app.
- Also seen: the "Test & Score – PRICE (10-fold CV)" widget had been switched to "Test on test data" (no test input → empty table). It must be set back to Cross validation, 10 folds, before saving.

## 2026-10-26 – Decision: keep Orange's LR hold-out figure, with an OLS note (team decision)
- Hold-out Test row 5 keeps the Orange GUI values (RMSE 268.125, MAE ₹185.075, R² 0.754).
- New note A36: plain OLS in Python gives MAE ₹183.9, RMSE ₹264.9, R² 0.760 (the original value); the gap comes from inside Orange; LR is comparison-only. The note is written by `evaluate.py`. `test_reference.py` still PASSES.
- Orange check: the workflow was saved with the price CV widget on "Cross validation by feature" (high_rating) instead of "Cross validation". That option splits the data by rating group, not into 10 random folds (RF R² 0.632, LR 0.321). It must be switched to "Cross validation" (10 folds) and the workflow saved again. The workbook CV numbers (RF R² 0.725) come from the correct run and are unaffected.
- After switching back to Cross validation (10 folds), the GUI reproduces the logged CV exactly: RF RMSE 223.657, MAE ₹136.778, R² 0.725. The `.ows` saved at 14:19 still holds the price CV widget on "Test on test data", so it must be saved once more.

## 2026-10-26 – Price branch of SpotCheck_workflow.ows verified (saved 14:34)
- XML parses; 25 nodes, 35 links.
- Random Forest (FINAL – price): 100 trees, replicable, no attribute limit, no depth limit, min split 5, no class weighting. Matches `train_models.py`.
- Linear Regression (comparison – price): no regularization, fit intercept.
- Test & Score – PRICE (10-fold CV): Cross validation, 10 folds. Test & Score – PRICE (HOLD-OUT test): Test on test data.
- File widgets point to this folder's `zomato_price.tab`, `zomato_price_train.tab` and `reference_tests_price.tab`; Orange also stores the relative name, so the file works on other computers.
- Links: PRICE TRAIN → RF (Data); RF → both Test & Score (Learner); RF Model → Predictions – PRICE hold-out.
- All settings are now saved with version numbers, so the earlier crash and the remembered-default problem can't recur.
- Still open (cosmetic): the scheme description and the "PRICE coefficients (final model)" Data Table title still describe Linear Regression as final.

## 2026-10-26 – Cosmetic labels in SpotCheck_workflow.ows fixed (team request)
- Scheme description now reads "Price: Random Forest (FINAL; Linear Regression, Tree and mean baseline kept for comparison) and 4.0+ rating (Logistic Regression)…".
- Data Table node 9 renamed "PRICE coefficients (final model)" → "PRICE coefficients (LR comparison)".
- Text edits only, no widget settings touched; the XML still parses (25 nodes, 35 links). Orange was open at the time, so the workflow must be reopened in Orange without saving, or the old labels would be written back.

## 2026-10-26 – Orange check: rating branch
- Logistic Regression (FINAL – rating) widget: Ridge (L2), C=1, no class balancing. Correct.
- **Orange GUI rating LR 10-fold CV: AUC 0.811.** The Python sklearn LR (C=1, liblinear, one-hot, raw numerics) gets 0.812; the workbook says 0.804. So the GUI agrees with Python, not with the workbook. This supports the view that the workbook's Orange rating numbers (AUC 0.804, P(4.0+) 0.143, 0.175, …) were not produced by this GUI workflow. To confirm: compare the GUI's P(4.0+) for T01–T10 with Python's (≈ 0.08, 0.08, 0.92, 0.14, 0.22, 0.24, 0.13, 0.22, 0.91, 0.78).
- Hold-out (Test on test data), averaged over classes: LR AUC 0.917, CA 0.900. This matches the workbook (0.917, 9/10).
- Rating Random Forest still has the remembered settings (3 attributes per split, depth 5, min split 10, class balancing). GUI CV AUC is 0.787 vs 0.818 in the workbook. To be set the same way as the price RF.
- Both rating Test & Score widgets show "(None, show average over classes)". The workbook figures use Target class = Yes; set it before reading F1/Precision/Recall.

## 2026-10-26 – Rating LR: Python DOES reproduce the Orange GUI (the workbook values don't)
- Orange GUI "Predictions – RATING hold-out", P(4.0+) for T01–T10: 0.092, 0.061, 0.917, 0.141, 0.224, 0.229, 0.138, 0.211, 0.912, 0.785.
- Python LogisticRegression (L2, C=1, lbfgs, one-hot of all levels, trained on `zomato_rating_train.tab`) reproduces them within **0.002**. That holds both with raw numerics and with standardised n_cuisines/cost_for_two. liblinear is off by up to 0.021.
- The workbook's values (0.143, 0.175, 0.899, …; from its 'Rating Coefficients' sheet) differ from the Orange GUI by up to 0.11. So they were not produced by this workflow and are not a valid target. The ±0.02 check passes against the real Orange output.
- Classification at 0.5 is unchanged: 9/10 correct (T08 Mojo Pizza missed), hold-out AUC 0.917.
- Consequence: the reason for pausing the Python rating model no longer holds. Building it waits for the team's go-ahead.

## 2026-10-26 – Rating branch fixed in Orange and verified (saved 14:43)
- Rating RF set to the same recipe as the price RF: 100 trees, replicable, no attribute limit, no depth limit, min split 5, no class balancing. Both rating Test & Score widgets use Target class = Yes; CV = 10 folds, hold-out = Test on test data. Logistic Regression: L2, C=1 (C_index 61), no class weight. The saved `.ows` confirms all of these.
- **Orange GUI rating 10-fold CV, target Yes** (workbook in brackets):

| Model | AUC | CA | F1 | Prec | Recall |
|---|---|---|---|---|---|
| Logistic Regression | 0.811 (0.804) | 0.833 (0.833) | 0.528 (0.523) | 0.744 (0.751) | 0.409 (0.401) |
| Tree depth 4 | 0.729 (0.729) | 0.811 (0.812) | 0.476 (0.480) | 0.647 (0.647) | 0.377 (0.382) |
| Random Forest | 0.825 (0.818) | 0.841 (0.835) | 0.586 (0.586) | 0.722 (0.685) | 0.493 (0.513) |

- Orange's model comparison gives 0.985 probability that RF has higher AUC than LR. The gap is 0.014. Logistic Regression stays the FINAL rating model, as recorded in CLAUDE.md; a change would need a team decision.
- **Hold-out (Test on test data, target Yes):** LR AUC 0.917, CA 0.900, F1 0.857, Prec 1.000, Recall 0.750; Tree 0.771 / 0.800; RF 1.000 on all metrics (10 rows only). This matches the workbook.
- The workbook's rating CV table is not yet updated with these GUI numbers.
- The 14:43 save restored the old scheme description and "PRICE coefficients (final model)" title, because Orange still had the pre-edit version open. They are to be renamed inside Orange instead.

## 2026-10-26 – FINAL rating model built in Python (team go-ahead)
- **Model:** Logistic Regression, L2, C=1, lbfgs (`train_models.py rating`). One-hot encoding of the 17 categorical inputs; n_cuisines and cost_for_two standardised. Trained on `zomato_rating_train.tab` (9,234 rows). Converged in 50 iterations. `rating_model.joblib` = 3 KB. The price model was not retrained (file unchanged).
- **Check vs Orange GUI (P(4.0+), T01–T10):** Python 0.091, 0.060, 0.917, 0.142, 0.224, 0.231, 0.139, 0.211, 0.912, 0.784. Orange 0.092, 0.061, 0.917, 0.141, 0.224, 0.229, 0.138, 0.211, 0.912, 0.785. Max |diff| 0.0018, within the ±0.02 tolerance (`train_models.py` asserts it).
- **Hold-out:** 9/10 correct at 0.5 (T08 Mojo Pizza missed, P = 0.211); AUC 0.917. Same as Orange.
- **reference_tests.csv:** P(4.0+) (4 decimals), Predicted 4.0+ (0.5) and Correct? filled in through `predict.py`. The original 23 columns are still byte-identical.
- **test_reference.py:** now checks every restaurant for price ±₹1, P(4.0+) ±0.001 and the 0.5 verdict. **PASSED 10/10** in the project folder and in `repo/`.
- **Workbook:**
  - Hold-out Test I17:I26 = Python P(4.0+), plus note A34.
  - Reference Tests X5:X14 = Python P(4.0+); note A17 updated.
  - Model Comparison (CV) rating rows 11–14 = Orange GUI 10-fold CV with target Yes: LR AUC 0.811, RF 0.825, Tree 0.729, Constant 0.500. Notes A22/A23; the confusion matrix is still from the earlier run.
  - Summary B17 "Why Logistic Regression for rating?" and B18 hold-out result updated.
  - Rating Coefficients notes A93/A94: the old coefficients don't reproduce Orange; the app uses the joblib.
  - Orange numbers are stored as `ORANGE_RATING_CV` in `evaluate.py`.
- **repo/:** copied `predict.py`, `rating_model.joblib`, `reference_tests.csv`, `test_reference.py`, `requirements.txt`; README updated.
- **SpotCheck_workflow.ows** (Orange closed, so safe to edit): scheme description and the "PRICE coefficients (LR comparison)" title re-applied. All settings checked: both RFs on the same recipe, rating Test & Scores with target Yes, all 6 File widgets on the right files. The XML parses (25 nodes, 35 links).

### Open items
1. ~~Confusion Matrix (CV) in the workbook is from the earlier Orange run.~~ Done, see below.
2. Rating: Random Forest's CV AUC (0.825) is slightly above Logistic Regression's (0.811). LR stays FINAL, as recorded in CLAUDE.md; revisit only by team decision.
3. Streamlit Cloud Python version for the pinned scikit-learn 1.9.1 (check at first deploy).
4. `app.py` waits for the Google Stitch screen designs.

## 2026-10-26 – Rating confusion matrices read from the Orange GUI
- **Confusion Matrix (CV)**, Logistic Regression, 10-fold, number of instances:
  - Actual No: 6,840 predicted No, 297 predicted Yes.
  - Actual Yes: 1,245 predicted No, 862 predicted Yes.
  - Total 9,244.
  - Consistent with the CV table: precision 862/1,159 = 0.744, recall 862/2,107 = 0.409, accuracy 7,702/9,244 = 0.833.
  - Earlier run: 6,857 / 280 / 1,262 / 845.
- Workbook 'Model Comparison (CV)' B18:C19 updated; note A23 rewritten. Stored as `ORANGE_RATING_CM` in `evaluate.py`.
- **Confusion Matrix (HOLD-OUT)**, Logistic Regression: 6 / 0 / 1 / 3 (T08 Mojo Pizza is the miss). Same as the workbook and the Python model; no change needed.
- `test_reference.py` still PASSES 10/10.

## 2026-10-26 – Assumption checks re-run for both models (statsmodels, training files)
**Price, Linear Regression (OLS, n = 9,234, R² 0.616):**
1. Linearity: RESET F = 446, p < 0.001. **Violated.**
2. Independence: chains are 40% of rows. Restaurant name explains 73% of their residual variance; with names shuffled it explains 26%. **Violated** (new finding).
3. Equal spread: Breusch–Pagan LM = 1,981, p < 0.001; residual SD ₹118 → ₹611 from the lowest to the highest fitted decile. **Violated.**
4. Normality: Jarque–Bera = 266,298, p < 0.001; skew 2.6, kurtosis 28.8. **Violated.**
5. Multicollinearity: only c_Cafe is above the 2.24 threshold (GVIF^(1/2df) 2.46, overlaps type = Cafe); all others ≤ 1.61. **Mostly OK.**
- A log(price) model fixes normality (skew −0.2) but not linearity (RESET p < 0.001) or spread (BP p < 0.001).
- Verdict: 4 of 5 fail. Linear Regression is comparison only; Random Forest is FINAL.

**Rating, Logistic Regression (unpenalised fit for diagnostics, n = 9,234, 2,103 events):**
1. Binary outcome: **OK.**
2. Independence: name explains 51% of chain residual variance vs 25% shuffled. **Violated.** Impact: GroupKFold AUC 0.806 vs KFold 0.812 (−0.006).
3. Linearity of the logit (Box–Tidwell): n_cuisines p = 0.95 **OK**; cost_for_two p < 0.001 **violated** (4.0+ rate flat at 0.11–0.14 up to mid prices, then rising to 0.72). Impact: a spline on cost gives the same CV AUC (0.812 → 0.812).
4. Multicollinearity: c_Cafe 2.46, all others ≤ 1.61. **Mostly OK.**
5. Influential points: max Cook's D 0.005 (problem only near 1). **OK.**
6. Sample size: 31 events per parameter (rule of thumb ≥ 10). **OK.**
- Calibration (10-fold CV): Hosmer–Lemeshow χ² = 11.6, p = 0.17; predicted vs observed per decile agree within 0.02. **Probabilities are well calibrated.**
- Verdict: 2 of 6 violated, but neither measurably hurts predictions. Logistic Regression stays FINAL.

## 2026-10-26 – App plan and user journey (team decisions)
- **Build route:** build and test `app.py` locally (`streamlit run app.py`), then push `repo/` to a public GitHub repo (GitHub CLI signed in as SPYMASTER97; push only after team OK), then deploy on Streamlit Community Cloud (the team signs in at share.streamlit.io). The Python version for Cloud must support scikit-learn 1.9.1; check at deploy.
- **Users:** primary = first-time restaurant founder in Bangalore before opening; also existing owners planning a new outlet or format. Justification: the models use only pre-opening inputs (post-opening fields were dropped in cleaning).
- **Journey (6 stages):** trigger → arrive (lands straight on the form, no login) → describe the concept (Where → Format → Menu → Price) → verdict (price check first, then the rating outlook) → what-if comparison → take-away summary. Side path: About/Method.
- **v1 screens (all chosen by the team):** S1 Concept form, S1-error state, S2 Results, S3 Compare scenarios, S4 Take-away summary, S5 About/Method. **Device: responsive web app** (desktop layout that stacks cleanly on phones; the team changed this from "desktop first").
- **Design update (team decisions, same day):**
  - **Mobile web app first** (about 390 px wide).
  - **Zomato-style red palette** (#E23744 primary, green rating-style badges). The SpotCheck name stays as the brand; no Zomato logo or wordmark; "Not affiliated with Zomato" shown.
  - **Step-by-step wizard:** Where → Format → Menu → Price, with a progress bar.
  - **Interactive widgets:** live price slider (results update as you drag), tappable chips and tiles (cuisine chips, type tiles with emoji, popular-area chips), swipeable what-if cards. Gauges were not chosen.
  - Navigation via the menu (Streamlit's sidebar becomes a slide-in drawer on phones).
- **Verdict rules (from the workbook settings):** price band ± ₹136 (RF 10-fold CV MAE): Above / In line / Below market. Rating: Strong ≥ 60%, Moderate ≥ 30%, otherwise Weak.
- **Mock-up numbers computed with `predict.py`:** cafe in Koramangala 5th Block, ₹800 → market ₹718 (₹582–₹854), in line, 92% Strong. Without table booking → ₹628, above market, 68%. At ₹1,200 → above market, 95%.
- **UI caveat needed:** a higher planned price raises P(4.0+) because pricier places tend to be rated higher (correlation, not cause). The comparison screen must say so.

## 2026-10-26 – App v1 built and tested locally (Streamlit, mobile-first)
- **Design input:** the Stitch export (`design/stitch_DESIGN.md`, `design/stitch_results_screen.png`) contained only the Results screen and the design system. The team chose: build all screens from this style, and keep the bottom tab bar.
- **Removed from the Stitch screen** because it broke our rules or stated untrue things:
  - profile/avatar icon (no-login rule);
  - café photo with made-up "42 comparable cafes · 98% confidence";
  - Min/Median/Max labels (the numbers are estimate ± ₹136, not a min/max);
  - invented "specialty beans / valet" explanation;
  - false "2019–2023 micro-market registries" data claim;
  - "success probability / viability" wording (the model predicts a 4.0+ rating only).
- **`app.py`** (new file; no existing file could hold the app):
  - 4-step wizard: popular-area chips plus a searchable list of all 40 areas → type tiles and 3 service toggles → cuisine chips and a total stepper → price slider plus an exact-amount field.
  - Results: price card with range bar, rating card, live "play with your price" slider, Keep in mind, details for experienced owners.
  - Compare: swipeable cards, up to 3 (base + 2 what-ifs); blocks duplicates and no-change what-ifs; shows the price↔rating correlation note.
  - Summary: downloadable HTML. About: data, accuracy, limitations. Bottom tab bar: Predictor / Compare / About.
  - Every number comes from `predict.py`. Verdict rules: price band ± ₹136 (RF CV MAE), Strong ≥ 60%, Moderate ≥ 30%. No login, nothing stored; "Not affiliated with Zomato" shown.
- **`.streamlit/config.toml`:** red theme (#E23744).
- **`test_app.py`:** 5 checks: the app's results match `reference_tests.csv` for all 10 restaurants (price ±₹1, P ±0.001); verdict rules; wizard errors; all 5 pages render (T03 shows ₹718 and 92%; Compare shows ₹628 / 68% / 95%); step 1 can't advance without a location. **PASSED**, as does `test_reference.py`.
- **Manual walk-through** in a 375 px phone viewport with T03 (Roundup Cafe): ₹718, range ₹582–₹854, in line, 92% Strong. What-ifs: ₹1,200 → above market, 95%; no table booking → ₹628, above market, 68%.
  - Fixed during the walk-through: broken expander icon (font rule), "No serves alcohol" chip wording, truncated tab labels, words running together in notes, duplicate what-ifs, oversized rating badge.
- **Open:**
  - Service toggles flipped with a scripted click but not with the automated mouse click in the preview browser. Real taps need checking by the team.
  - Fixed bottom bar and swipe to be checked on a real phone.
- **repo/:** `app.py`, `test_app.py`, `.streamlit/config.toml` copied; README updated (file guide, run and check commands). Nothing pushed yet.

## 2026-10-26 – App feedback 1: cuisine total follows the chips (team request)
- Before: the "Total number of cuisines" stayed at 1 when chips were tapped, so the user had to raise it by hand.
- Now: the total updates as chips are tapped. The user presses + only for cuisines outside the 12 listed, and those extras are kept when chips change (4 chips + 1 extra = 5; remove a chip → 4). The total is capped at 8 (the highest in the training data); picking more than 8 chips shows "Pick at most 8 main cuisines…".
- New test `test_cuisine_total_follows_chips` in `test_app.py`; all 6 app checks PASS. Copied to `repo/`.

## 2026-10-27 – App feedback 2: what-ifs can change several settings; up to 3 what-ifs (team request)
- Before: each what-if changed exactly one setting, and only 2 what-ifs fitted beside the base concept.
- Now: "Add what-if card" is a form that starts from the concept and shows every setting (area, type, the 3 services, cuisines, total, price). Change any number of them, then add the card.
  - The card lists every change. Its title is the change itself if there's only one (e.g. "Higher price"), otherwise "What-if B/C/D".
  - "All settings" opens the card's full setup.
  - Up to 3 what-ifs plus the base concept.
  - Blocked: no change, duplicates, or cuisine/price problems (same rules as the wizard). The cuisine total is raised automatically to at least the number ticked.
- The summary's what-if table lists each card's changes.
- New test `test_whatif_form_multiple_changes`. All 7 app checks PASS. Browser check in a separate session: one card with 3 changes (table booking, 2 cuisines, total 1 → 2) computed correctly. Copied to `repo/`.

## 2026-10-27 – App feedback 3: change list removed from what-if cards (team request)
- The red "what changed" box (e.g. "📍 Koramangala 5th Block → Bellandur …") is no longer shown on the compare cards; each card shows its title, the results and an "All settings" fold-out with its full setup.
- The take-away summary still lists each card's changes. All 7 app checks PASS; copied to `repo/`.

## 2026-10-27 – Repo prepared for GitHub (push pending)
- Pre-push checks in `repo/`: `test_reference.py` PASSED, `test_app.py` PASSED; no raw data, `*.tab`, `*.xlsx` or secrets; all files identical to the parent originals.
- `requirements.txt`: every pinned package has Linux wheels for Python 3.12 and 3.13 (checked with pip download), so Streamlit Cloud can install the versions that saved the models. Use Python 3.12 or 3.13 when deploying.
- `repo/` initialised as a git repo (branch `main`); first commit 066ceaa with 12 files (app, models, predict.py, tests, reference rows, README, .gitignore, theme, repo CLAUDE.md). Author: Saswat Pani with the GitHub no-reply address (SPYMASTER97).
- Creating the **public** repo SPYMASTER97/spotcheck was blocked by Claude Code's permission check (publishing needs the user). The team runs the create-and-push command themselves.

## 2026-10-27 – Pushed to GitHub
- Public repo **https://github.com/SPYMASTER97/spotcheck**, branch `main`, commit 066ceaa (pushed by the team with `gh repo create … --push`).
- Verified: GitHub `main` = local `main`; all 12 files present; both `.joblib` files are byte-identical to the local ones (git blob hashes match).
- Next: deploy on Streamlit Community Cloud (repo SPYMASTER97/spotcheck, branch main, file app.py, Python 3.12). Record the live URL here after deploy.

## 2026-10-27 – Deployed on Streamlit Community Cloud
- **Live URL:** https://spotcheck-tbcb5npizuvfmpfgto7a2a.streamlit.app/ (deployed by the team from SPYMASTER97/spotcheck, branch `main`, `app.py`).
- **Live check, T03 Roundup Cafe** (Koramangala 5th Block · Cafe · online ordering · table booking · Beverages, Continental, Cafe · 3 cuisines · ₹800): **₹718, typical range ₹582–₹854, In line with market; 92% Strong.** Identical to `reference_tests.csv` (price 718.2, P(4.0+) 0.9166), so the cloud loads the same models and library versions.
- Also seen live: the cuisine total follows the chips (3 chips → 3). The exact-amount field and slider stay in sync.
- Reminder: free tier apps sleep after 12 hours without traffic. Open the link 10–15 minutes before any demo.

## 2026-10-27 – Handoff files created (team request)
- `HANDOFF.md` (new; no existing file held a current-state snapshot): live and GitHub links, final models and evidence, app rules, file map with edit rules, ship-a-change steps, known quirks.
- `NEXT_SESSION.md` (new): start-up checklist and prioritised to-do list:
  - stale CLAUDE.md facts (needs team OK);
  - workbook guide text;
  - README live link;
  - real-phone test;
  - report visuals;
  - course deliverables for Sessions 20–24.
  - Plus open decisions.
- Both are for the next Claude session and the team. They are not in `repo/` (not part of the app).

## 2026-10-27 – Planner chat built in a new folder (faculty request; not yet in the app)
- **Why:** the faculty asked for repeat use after the go/no-go check: help the owner plan the opening (size, staff, money, costs, sales).
- **Team decisions (multiple-choice, 2026-10-27):**
  - 5 targets: floor area, staff headcount, initial investment, food cost %, monthly revenue. Break-even months is a formula on top, not a model.
  - Synthetic data: the real Zomato inputs are kept, and the extra inputs and the targets are synthetic. The targets are linear formulas plus normal noise, so Linear Regression fits them by construction.
  - Model: Linear Regression only.
  - Chat: Gemini reads the question, with a rule-based fallback.
  - Everything goes in a **new folder `planner/`**. No existing file, model, Orange workflow or `.tab` input is changed; integration into `app.py` comes later.
- **Why new files:** the team asked for a separate folder, and no existing file holds synthetic planning data or a chat.
- **Data** (`planner/generate_data.py`, seed 19):
  - 9,234 training rows from `zomato_rating_train.tab` (read-only) and T01–T10 as the hold-out.
  - 6 synthetic inputs: guests/day, opening hours, delivery %, menu items, alcohol % and takeover. They are clipped normals or a coin flip.
  - Targets were raised to a physical minimum in at most 47 of 9,234 rows each (0.5%).
  - Formulas were calibrated so break-even comes out at about 7–38 months on T01–T10 (illustrative).
- **Results** (`planner/EVALUATION.md`):
  - 10-fold CV R²: area 0.944, staff 0.909, investment 0.945, food cost 0.581, revenue 0.910. GroupKFold gives the same.
  - Residual skew ≈ 0 and kurtosis ≈ 3. Four of 15 assumption tests are slightly below p = 0.05 (n = 9,234; about 1 is expected by chance).
  - **The high R² reflects how the data was built; it is not evidence about real restaurants.** Every chat answer carries the "synthetic data" label.
- **Rule 2 kept:** Gemini only classifies the question and pulls out stated values. Its output is validated, any failure falls back to the rules, and every number comes from `planner/plan_predict.py`.
  - The Gemini model name (`gemini-2.5-flash` by default) is **not yet tested with a real key**. The fallback was tested.
- **Tests:** `planner/test_planner.py` 7/7 PASSED (models reproduce `planner/data/planner_reference.csv`, chat flow, ranges, Gemini fallback, demo page).
- **Next:** the team tests `planner/chat_demo.py` with their Gemini key. Then decide integration: a Plan tab in `app.py`, copying `planner/` into `repo/`, and the key in Streamlit Cloud secrets.

## 2026-10-27 – Planner: Gemini key added, default model changed
- The team saved their Gemini key in `planner/.streamlit/secrets.toml`. It is git-ignored by `planner/.gitignore` and was never shown or logged.
- `gemini-2.5-flash` (the old default) returns 404 for new users. `gemini-3.8-flash` timed out or returned 503 ("high demand") on every try.
- **New default: `gemini-3.5-flash-lite`** (listed for this key; about 2 s per message). It can be changed with `GEMINI_MODEL` in the secrets file.
- Live test on T03, with Gemini as the reader for all 6 messages:
  - "11 in the morning till 11 at night" → 12 opening hours;
  - "roughly half" → 50% delivery;
  - "when do I get my money back?" → break-even;
  - "nope, brand new fit-out" → takeover No.
  - The numbers came from the models: staff 13, break-even about 19 months.
  - Earlier, a timeout fell back to the rules as designed.
- `planner/test_planner.py` 7/7 PASSED.

## 2026-10-27 – Planner chat feedback: objective required; stated facts kept apart
- **Team request:** if a message is not a clear question, the chat must ask "What is your objective?" and not move on until one is chosen. The user can tap a button or type it (7 objectives: size, staff, money to open, food cost, revenue, break-even, full plan).
- **Bug found by the team:** "I have an investment of 1 Cr, and a staff of 20 members with me" was treated as a request for an investment estimate, because it mentions "investment".
- **Fixes:**
  - **Objectives only from real requests:** a message counts as an objective only if it asks for an estimate (a question or request words), or names one while the chat is waiting for an objective.
    - The Gemini prompt now says the same.
    - Gemini's "no objective" reading is trusted, instead of being overridden by keywords.
  - **Stated facts are kept:** budget and staff on hand are noted (1 Cr = ₹100 lakh) and compared with the estimates, e.g. "Your budget of ₹100 lakh covers this, with about ₹47 lakh to spare." They are not model inputs.
  - **Follow-ups no longer re-run the last answer:** "What about 250 guests?" after an answer is noted, and the objective question is asked.
- Tested with rules and with Gemini (`gemini-3.5-flash-lite`) on the team's exact message: both now note the facts and ask for the objective.
- `planner/test_planner.py` 8/8 PASSED. A new test covers the objective question and the team's case. Tests force the rule-based reader (`PLANNER_NO_LLM`), so they make no Gemini calls.

## 2026-10-27 – Plan feature: user flow approved, Stitch prompts written
- **Flow approved by the team:**
  1. Compare: tap a card to select it.
  2. Sticky "Plan this concept →" button, disabled until a card is selected.
  3. Plan chat screen: concept strip, synthetic-data notice, objective question when unclear, follow-ups with quick-reply chips, answer cards, "Ask next" chips.
  4. Summary gains a "My opening plan" section, included in the download.
- **Bottom bar:** Predictor · Compare · Plan · About, with an empty state on Plan until a concept is chosen.
- `design/stitch_plan_prompts.md` (new; no existing file holds Stitch prompts for this feature) has a shared style prompt plus 11 screen prompts.
  - Example numbers are real model outputs for T03 (base concept; 150 guests, 12 h, 45 items, 50% delivery, new fit-out; budget ₹100 lakh, 20 staff): area ≈ 1,240 sq ft, staff ≈ 13, investment ≈ ₹50.3 lakh, food cost ≈ 26.2%, revenue ≈ ₹11.4 lakh/month, break-even ≈ 19 months.
- **Next:** the team generates the screens in Stitch and sends the export. App integration is not started.

## 2026-10-27 – Stitch export for the Plan feature reviewed
- The export was unzipped to `design/plan_export/` (15 screens + DESIGN.md). The zip in Downloads is untouched.
- **Matches the approved flow and real outputs:**
  - Compare: unselected state and selected state (red border ✓, "Plan this concept →"); disabled "Select a card to continue".
  - Plan empty state; chat start; objective question with 7 chips and fact pills (budget ₹100 lakh, staff 20); follow-up with quick replies ("Question 1 of 2", "Not sure (use 120)", typing dots).
  - Investment card (₹50.3 lakh, ₹46.3–54.2, "₹49.7 lakh to spare"); break-even card (≈ 19 months, cost table) and its amber not-reached variant; switch-concept sheet.
  - Summary with "My opening plan" (all 6 numbers match the model outputs).
- **Invented by Stitch; not to be built** (untrue, unsupported by our models, or against the no-login rule):
  - Profile/user icon; "BLR v1.2"; "AI Feasibility Studio"; "Live Mode"; "Report #SC-9244"; "High confidence"; "Strong viability"; "Viable"; the hamburger side menu; the map image.
  - Invented details: "Artisanal Café", "12th Main, Indiranagar" micro-market, "Estimated 38–42 covers".
  - On the chat start: the "Koramangala 5th Block Baseline" panel (₹32–38L, 3.4 turns/day, 11–14 months).
  - The whole `plan/` screen ("Pre-Launch Plan & Feasibility": footfall, rent, checklist, "Founder advice", all invented); the "Unlocks after concept selection" modules; "Popular Bangalore concepts".
  - The Compare tip text claiming pricier places "invest more in decor, craft coffee"; it will be replaced with the neutral wording the app already uses (association, not cause).
  - `predictor/` and `about/` are redesigns that were not requested; the current screens stay.

## 2026-10-27 – Plan feature built into the app (committed locally, not pushed)
- **Compare:** each card is now tappable. Both the circle and "Choose this one" select it.
  - The selected card gets a red border, a "Selected" badge and ✓; the others fade.
  - A pinned "Select a card to continue" button becomes "Plan this concept →" once a card is selected.
  - The first version used chips below the cards. The team couldn't select the card itself, so it was changed the same day.
- **Plan tab** (bottom bar: Predictor · Compare · Plan · About):
  - Empty state until a concept is picked.
  - Concept strip, synthetic-data banner with "Why synthetic?".
  - Chat bubbles, with fact pills under the user's message.
  - Objective chips when no objective is clear; "Question N of M" follow-ups with quick-reply chips and "Not sure".
  - Answer cards: estimate, range and inputs used; budget/staff comparison; break-even table with assumptions; full-plan tiles.
  - "Ask next" chips and "View my plan in the Summary".
  - Picking a different concept with a plan in progress asks "Start a new plan?" first.
- **Summary:** a "My opening plan" section (each answered estimate with its range, the stated facts, the data note). It is included in the HTML download.
- **Left out (invented in the Stitch export):** see the 2026-10-27 review entry. The Compare tip keeps the app's neutral wording.
- **Engine:** chat messages now carry structured data (question number, answer numbers, stated facts) for the cards. The wording and numbers are unchanged.
- **Gemini in the app:** reads `GEMINI_API_KEY` / `GEMINI_MODEL` from Streamlit secrets. Tests force the rules (`PLANNER_NO_LLM`).
- **Tests:**
  - `test_app.py` 11/11 PASSED (4 new: card selection, empty state, chat → investment card → summary, switch confirmation);
  - `planner/test_planner.py` 8/8 PASSED;
  - `test_reference.py` PASSED.
  - Checked in the browser at phone size: the T03 chat from facts to investment card gave ≈ ₹50.3 lakh, with ₹49.7 lakh to spare.
- **requirements.txt:** `requests==2.34.2` (pure-Python wheel; works on Python 3.12).
- **repo/:** app, tests, requirements and the `planner/` runtime files and models were copied (identical; synthetic training data excluded); README updated (Plan section, live link, third test). Local commit only. **The team pushes.**
  - After the push, add `GEMINI_API_KEY` in Streamlit Cloud → Settings → Secrets (optional; without it the chat uses rules). Then check T03 live (₹718, 92%) and one Plan question.

## 2026-10-27 – Wizard defaults changed (team request)
- **Menu step:** the cuisine chip "Cafe" is now shown as **"Coffee"**, so it doesn't clash with the "Cafe" restaurant type. Only the display name changed: the model input is still `c_Cafe`, so predictions are unchanged.
- **Menu step:** "Total number of cuisines" now **starts at 0** until a cuisine is picked. Pressing Next with 0 shows "Pick at least one cuisine, or press + if yours isn't in the list." The models need 1–8.
- **Format step:** **Online ordering is off by default** (was on).
- Checked in the browser: online ordering off, "Coffee" chip, "0 selected", total 0, and Next blocked with the message.
- Tests: `test_app.py` 11/11 (step-errors test extended), `test_reference.py` and `planner/test_planner.py` PASSED. Copied to `repo/` and committed locally. Not pushed.

## 2026-10-27 – Plan chat: worded answers and ranges (team feedback)
- **Problem reported by the team:** "From 5pm to 3am" for opening hours was rejected ("between 6 and 18"), and the question was asked twice.
  - **Cause:** locally the app wasn't using Gemini. The key was in `planner/.streamlit/`, but `app.py` reads `Session 19 - SpotCheck/.streamlit/secrets.toml`. The team's key file was copied there without being shown; that folder is outside `repo/`, and secrets are git-ignored.
  - The fallback rules then read only the "5".
- **Fixes:**
  - **Time ranges become hours, wrapping past midnight:** "5pm to 3am" = 10, "11 in the morning till 11 at night" = 12, "9 to 5" = 8, "18:00 to 02:00" = 8.
  - **Share words** for % questions: "a quarter delivery" = 25%, "half" = 50%.
  - **Worded answers are confirmed** ("Got it: 10 hours."). Details given for a later question are acknowledged ("Noted: …"). An out-of-range answer is asked about once, not twice.
  - **Rules first, Gemini when needed:** the fast rules read each message first, and Gemini is asked only when they find nothing (timeout 8 → 15 s).
    - Why: Gemini was taking about 14–23 s per call today (503 "high demand" and timeouts on Google's side); earlier it took about 2 s.
- **Ranges (team request):** an input given as a range ("100-200 guests", "10 to 14 hours", "30-40% delivery", or a bare "40-60" answering the question) is computed at both ends.
  - Each answer shows a band, e.g. investment "≈ ₹47.4–₹53.1 lakh", with "With 100 guests/day → ≈ ₹47.4 lakh" and "With 200 guests/day → ≈ ₹53.1 lakh".
  - This applies to the answer, break-even and full-plan cards and the Summary. The middle of the range feeds the main estimate. Both ends must be within the allowed range.
  - Gemini is told to return ranges as [low, high]; its output is validated like single values.
- **Tests:**
  - `planner/test_planner.py` 10/10 (new: worded answers, ranges);
  - `test_app.py` 12/12 (new: range answer card);
  - `test_reference.py` PASSED.
  - Checked in the browser: T03 → "100-200 guests" → "≈ ₹47.4–₹53.1 lakh".
- `repo/`: 4 local commits ahead of GitHub (Plan feature, wizard defaults, worded answers, ranges). **Not pushed.**

## 2026-10-27 – Compare cards: equal size (team feedback)
- **Problem:** the cards were squeezed side by side at a third of the width each, so text wrapped ("Your / concept") and badges spilled over the edge.
  - **Cause:** Streamlit wraps each card in a layout wrapper, so the width rule never reached it.
- **Fix:**
  - Every card is now 86% of the row, so the next card peeks in to show you can swipe.
  - All cards are the same height.
  - Row labels stay on one line, and the "Choose this one" / "✓ Selected" button lines up at the bottom of every card.
- Checked at phone size with 3 cards: all 292 × 373 px, and the selected what-if is shown correctly.
- Tests PASSED. Committed in `repo/`; 5 commits ahead of GitHub, not pushed.

## 2026-10-27 – What-if cuisine total, Plan button position, text-only tab bar (team feedback)
- **What-if card:** 7 cuisine chips showed a total of 4. The card was a Streamlit form, which only updates on submit.
  - It now uses normal fields, so the total follows the chips as you tap, as in the wizard. Extras added with + are kept.
  - The total can be 0. "Add what-if card" then asks for at least one cuisine.
- **"Plan this concept →"** now sits directly under the cards. As a pinned button it covered the "Add what-if card" button.
- **Bottom tab bar:** names only (no icons). The active tab is red with a red top line; the others are grey, with no button borders.
- Tests: `test_app.py` 13/13 (new: what-if cuisine total), `test_reference.py` and `planner/test_planner.py` PASSED.
- Checked at phone size: 7 chips → total 7; the tab bar shows plain names.
- `repo/`: 6 commits ahead of GitHub, not pushed.

## 2026-10-27 – Plan feature deployed and checked live
- The team pushed `repo/` (066ceaa..96088b6, 6 commits). GitHub `main` = local (commit and file hashes match for app.py, chat_engine.py, planner_models.joblib, requirements.txt).
- Streamlit Cloud redeployed automatically. **Live checks** (https://spotcheck-tbcb5npizuvfmpfgto7a2a.streamlit.app/):
  - **Wizard defaults:** online ordering off; cuisine total starts at 0; "Coffee" chip.
  - **T03 Roundup Cafe:** ₹718 (₹582–₹854), In line with market, 92% Strong. Matches `reference_tests.csv`.
  - **What-if:** 4 more cuisines tapped → "7 selected", total 7. The card was added; both cards are 382 × 373 px; "Select a card to continue" stays disabled until a card is chosen; card B selected → "Plan this concept →" opened Plan.
  - **Plan with a range:** "How many staff do I need?" → "100-200 guests" → "From 5pm to 3am" (10 h) → "not sure" → "half" (50%) gave **Staff ≈ 13–16 people** (13 at 100 guests, 16 at 200).
  - Gemini key on Cloud: not checked. The live chat read these messages with the built-in rules.
- **Found live:** a what-if card titled "What-if B" was labelled "What-if B (What-if B)" on Plan. Fixed and tested, committed locally (`1fa573b`). **Not pushed yet.**

## 2026-10-27 – Label fix pushed; Gemini live on Streamlit Cloud
- The team pushed `1fa573b`. GitHub `main` = local `repo/` (nothing left to push).
- The team added `GEMINI_API_KEY` in Streamlit Cloud → app → Settings → Secrets. The key is not in GitHub.
- **Live checks after the redeploy:**
  - T03: ₹718 / 92%.
  - A two-change what-if is labelled "What-if B" on Plan (no longer "What-if B (What-if B)").
  - "Why synthetic?" says messages are read by Google Gemini.
  - "roughly two hundred folks a day", which the rules can't read, was read by Gemini as "Got it: 200 guests."

## 2026-10-27 – Handoff files updated (team request)
- **`HANDOFF.md`** now covers the Plan feature:
  - synthetic plan models with CV metrics, and break-even as a formula;
  - the full app flow, including card selection, the objective rule, ranges and worded answers;
  - where the Gemini key lives (Cloud secrets plus two local git-ignored files);
  - the new `planner/` files; three test suites (13 app + 10 planner + reference);
  - new quirks: Gemini speed, Streamlit's CSS and module caching, and the layout wrapper.
- **`NEXT_SESSION.md`:**
  - updated start-up checks (three tests, a live Plan check);
  - new to-dos: CLAUDE.md project facts for the planner, workbook rating coefficients, an optional planner sheet in the workbook and in Orange, Plan screenshots for the report, real-phone tests of the Plan chat;
  - open decisions (planner data source, Gemini model).
- Not in `repo/` (not part of the app).

## 2026-10-28 – About page: Plan chat and model inputs (team request)
- **New "The Plan chat" section:**
  - **Understanding the question:** Google Gemini (an LLM) reads a message only when the built-in rules can't, and only to work out what is asked and which details were given. It never produces a number.
  - **The estimates:** five Linear Regression models trained on synthetic planning data. Break-even is a formula on those estimates.
- **New "What each model uses" section** (generated from the code, so it can't drift):
  - **Price** (Random Forest, real data): 18 inputs (location, type, alcohol, online ordering, table booking, number of cuisines, 12 cuisine flags).
  - **Rating** (Logistic Regression, real data): the same plus planned cost for two (19).
  - **Plan chat:** a matrix of every input × the 5 estimates. Inputs asked in the chat are marked *. The break-even assumptions are listed; budget and staff the user mentions are noted as comparisons only, not model inputs.
- **Limitations:** added that plan estimates come from synthetic data.
- **"How SpotCheck works":** added a 4th step, "Pick the version you'll open and plan it in a chat".
- Tests: `test_app.py` 14/14 (new: About content), `test_reference.py` and `planner/test_planner.py` PASSED. Checked at phone size.
- Committed in `repo/`; not pushed.

## 2026-10-28 – About update pushed and live
- The team pushed `620c0a3`; GitHub `main` = local `repo/`.
- Live About page checked: "The Plan chat" (Google Gemini + Linear Regression on synthetic data), "What each model uses" (price 18 inputs, rating 19, plan matrix) are present.

## 2026-10-30 – Whole project archived to GitHub (team request, before deleting the local copy)
- **Request:** move everything from the local folder to GitHub, because the local project will be deleted.
- **Team decisions (multiple-choice, 2026-10-30):**
  - **Destination:** the existing **public** repo SPYMASTER97/spotcheck, under `archive/`.
  - **Raw data:** `zomato.csv` (574,072,999 bytes) is **left out** (over GitHub's 100 MB limit; Kaggle licence). Its source and SHA-256 are recorded in `archive/README.md`.
  - **Cleaned/derived data published:** `zomato_clean.csv`, the 6 `.tab` files and `planner/data/planner_train.*` are uploaded. This **overrides CLAUDE.md rule 5 / repo CLAUDE.md**; both now record the exception.
  - **Course documents NOT uploaded:** MICA guidelines PDF, Hub page and the proposal .docx belong to MICA and the proposal's author.
  - **Gemini key NOT uploaded:** it stays in Streamlit Cloud secrets; the team doesn't need a local copy.
  - **`.venv` NOT uploaded:** it is rebuilt from `requirements.txt`.
- **Layout:**
  - `archive/ML Capstone/` mirrors the local folder: `CLAUDE.md` and `Session 19 - SpotCheck/` with everything (code, workbook, Orange workflow, logs, handoff files, design exports, planner, data).
  - The `repo/` subfolder is not duplicated, because it *is* the repo.
  - `archive/.claude/launch.json` holds the local preview config.
- The live app is unchanged: Streamlit Cloud still runs the root `app.py`.
