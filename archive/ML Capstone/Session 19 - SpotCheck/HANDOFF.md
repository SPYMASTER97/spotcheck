# SpotCheck – Handoff (state as of 2026-10-27, evening)

For the next Claude session **and** the team. Read `../CLAUDE.md` first (rules), then this file (where things stand), then `NEXT_SESSION.md` (what to do next). The full decision history with evidence is in `PROJECT_LOG.md`, the graded log; this file is a snapshot.

---

## 1. In one paragraph

SpotCheck is **live**. It's a mobile-first Streamlit app that checks a planned Bangalore restaurant concept:

- **Price for two:** the typical market price (Random Forest).
- **Rating:** the chance of a 4.0+ rating (Logistic Regression).
- **Plan chat (new):** after the user picks the version they'll open in Compare, a **Plan** chat estimates floor area, staff, initial investment, food cost and monthly revenue, plus break-even.

Price and rating are trained on 9,244 real restaurants from the Kaggle Zomato Bangalore dataset. The **five plan estimates come from Linear Regression models trained on SYNTHETIC data**, and the app labels them that way everywhere. Google Gemini (optional) only *reads* chat messages; every number comes from the models.

The code is public on GitHub and deployed on Streamlit Community Cloud. There is no login and nothing is stored.

| | |
|---|---|
| **Live app** | https://spotcheck-tbcb5npizuvfmpfgto7a2a.streamlit.app/ (free tier, sleeps after 12 h idle) |
| **GitHub** | https://github.com/SPYMASTER97/spotcheck (public, branch `main`, last commit `620c0a3`; local `repo/` = GitHub) |
| **Archive (2026-10-30)** | The whole local project is in the repo under `archive/` (incl. cleaned data, workbook, Orange workflow, logs). Not uploaded: `zomato.csv` (Kaggle; SHA-256 in `archive/README.md`), course documents, secrets, `.venv`. Restore steps: `archive/README.md`. |
| **Gemini** | Key set in Streamlit Cloud → app → ⋮ → Settings → Secrets (`GEMINI_API_KEY`). Locally in `.streamlit/secrets.toml` (app) and `planner/.streamlit/secrets.toml` (test page). Both are git-ignored and **never in `repo/`**. |
| **Live check (2026-10-27)** | T03 Roundup Cafe → ₹718 (₹582–₹854), In line with market, 92% Strong. Plan: "100-200 guests" → staff ≈ 13–16; "roughly two hundred folks a day" → Gemini read 200 guests. |

## 2. Models

### Price and rating (real data, FINAL)

| | Price (FINAL) | Rating (FINAL) |
|---|---|---|
| Model | Random Forest regression: 100 trees, `min_samples_split=5`, all features per split, no depth limit, `random_state=0` | Logistic Regression: L2, C=1, lbfgs |
| Inputs | location (40), primary_type (12), has_bar, online_order, book_table, 12 cuisine flags, n_cuisines | same + cost_for_two (n_cuisines and cost standardised) |
| File | `price_model.joblib` (7.7 MB) | `rating_model.joblib` (3 KB) |
| 10-fold CV (Orange GUI) | MAE ₹136.8, R² 0.725 (LR: ₹164.4 / 0.608) | AUC 0.811, CA 0.833, F1 0.528 |
| Chain-aware CV (GroupKFold) | R² 0.716 | AUC 0.806 |
| Hold-out (10 rows) | MAE ₹151.5 (Orange ₹151.7) | 9/10 correct (T08 missed) |

**Why these models:**
- **Price:** Linear Regression fails 4 of 5 assumptions, and Random Forest is more accurate.
- **Rating:** Logistic Regression is well calibrated (Hosmer–Lemeshow p = 0.17). Random Forest is only slightly better (AUC 0.825), so LR stays FINAL by team decision.

### Plan models (SYNTHETIC data, `planner/`)

**How the data was built** (`planner/generate_data.py`, seed 19):
- **Inputs:** the real Zomato inputs of the 9,234 training restaurants, plus six synthetic inputs drawn from clipped normal distributions or a coin flip: guests/day, opening hours, delivery %, menu items, alcohol %, takeover.
- **Targets:** each is a straight-line formula of the inputs (`TRUE_RULES`) plus normal noise, so Linear Regression is correct **by construction**.
- **Hold-out:** T01–T10.

| Target | Unit | 10-fold CV MAE | CV R² | Hold-out MAE |
|---|---|---|---|---|
| Floor area | sq ft | 79.1 | 0.944 | 83.2 |
| Staff headcount | people | 0.95 | 0.909 | 1.09 |
| Initial investment | ₹ lakh | 3.97 | 0.945 | 3.80 |
| Food cost | % of sales | 1.62 | 0.581 | 1.88 |
| Monthly revenue | ₹ lakh | 0.95 | 0.910 | 0.48 |

- **Break-even months** is a **formula, not a model:** investment ÷ (revenue − food − staff × ₹20,000 − rent at ₹90/sq ft × area price level − 15% other costs). The assumptions are in `plan_predict.ASSUMPTIONS` and shown in the app.
- **The high R² reflects how the data was built**, not real restaurants. The app and report must keep the "synthetic" label. Details are in `planner/EVALUATION.md` (CV, GroupKFold, assumption checks).

## 3. App (`app.py`)

**Every number comes from `predict.py` or `planner/plan_predict.py`.**

**Verdict rules:**
- **Price:** ± ₹136 band → Above / In line / Below market.
- **Rating:** Strong ≥ 60%, Moderate ≥ 30%, otherwise Weak.

**Flow:**
1. **Wizard:** Where → Format → Menu → Price.
   - Online ordering is off by default.
   - The cuisine total starts at 0; at least 1 is needed.
   - The c_Cafe cuisine chip is shown as "Coffee"; the model column is still `c_Cafe`.
2. **Results:** price card, rating card, live price slider.
3. **Compare:**
   - Up to 3 what-if cards plus the base, all the same size in a swipeable row.
   - The what-if card's cuisine total follows the chips live.
   - **Select a card:** tap the circle or "Choose this one". "Select a card to continue" becomes **"Plan this concept →"** under the cards.
4. **Plan** (tab):
   - Empty state until a card is picked; then a concept strip and a "synthetic data" banner with "Why synthetic?".
   - **Objective rule:** an unclear message, or facts only (e.g. "I have 1 Cr and 20 staff"), → "What is your objective?" with 7 buttons (tap or type). Nothing moves on until one is chosen.
   - **Follow-ups:** "Question N of M" with quick-reply chips and "Not sure".
   - **Answer cards:** estimate, range and inputs used; budget/staff comparison; break-even table; full-plan tiles; "Ask next".
   - **Ranges** ("100-200 guests") → each answer is given for the low and the high end.
   - **Worded answers** are confirmed: "5pm to 3am" = 10 h, "a quarter delivery" = 25%.
   - Choosing a different card with a plan in progress → "Start a new plan?".
5. **Summary:** concept, results, what-ifs and **"My opening plan"**, as a downloadable HTML file.
6. **About** page.

**Other app rules:**
- **Bottom tab bar:** Predictor · Compare · Plan · About (names only; active tab red).
- **Chat reading:** the fast rules read every message first. **Gemini** (`gemini-3.5-flash-lite`, 15 s timeout) is asked only when the rules find nothing. Its output is validated, and any failure falls back to the rules.
- **Design:** Zomato-style red #E23744, from the Stitch exports in `design/` (`stitch_DESIGN.md`, `plan_export/`). Content Stitch invented was left out (see PROJECT_LOG). "Not affiliated with Zomato".

## 4. Files (in `ML Capstone/Session 19 - SpotCheck/`)

| File | What | Edit rules |
|---|---|---|
| `PROJECT_LOG.md` | **Graded** decision log | Append an entry for every decision |
| `HANDOFF.md` / `NEXT_SESSION.md` | This snapshot / the to-do list | Update at the end of each session |
| `app.py`, `.streamlit/config.toml` | Streamlit app and theme | Edit here, then copy to `repo/` |
| `predict.py` | Price/rating predictions, `validate_inputs` | Edit here, then copy |
| `train_models.py`, `evaluate.py` | Train / evaluate price and rating; `evaluate.py` writes `reference_tests.csv` and the workbook | **Never retrain silently** |
| `planner/plan_predict.py` | 5 plan models, `break_even`, the chat's questions/ranges/assumptions | Edit here, then copy to `repo/planner/` |
| `planner/chat_engine.py` | Message reading (rules + Gemini), ranges, follow-ups, answer data | Edit here, then copy |
| `planner/generate_data.py`, `train_planner.py` | Synthetic data + training → `planner/models/`, `planner/data/planner_reference.csv`, `planner/EVALUATION.md` | Re-running changes the plan reference outputs |
| `planner/chat_demo.py` | Standalone test page for the chat | Optional |
| `test_reference.py` | `predict.py` vs `reference_tests.csv` | Must PASS before every push |
| `test_app.py` | 13 app checks (results, wizard, what-ifs, card selection, Plan chat, range card, summary) | Must PASS before every push |
| `planner/test_planner.py` | 10 checks (models vs `planner_reference.csv`, chat flow, objective rule, worded answers, ranges, Gemini fallback) | Must PASS before every push |
| `reference_tests.csv` | T01–T10 inputs + 6 appended output columns | Only the appended columns change |
| `SpotCheck_Session19_Pack.xlsx` | Evidence workbook (price/rating only) | openpyxl only; close Excel first |
| `SpotCheck_workflow.ows` | Orange workflow (price/rating) | Close Orange before editing |
| `design/` | Stitch exports + `stitch_plan_prompts.md` | Reference only |
| `repo/` | **The deployable copy** = GitHub (includes `planner/` runtime files and models; **not** the synthetic training data) | Never edit only here, except `repo/README.md`, which lives only there |
| `*.tab`, `zomato_clean.csv`, `../zomato.csv/zomato.csv`, `planner/data/planner_train.*` | Data | **Never edit; never commit** |

**Environment:**
- **Local:** Python 3.14 venv at `MLDL Capstone Group/.venv` (scikit-learn 1.9.1, pandas 3.1.0, numpy 2.5.4, scipy 1.18.1, joblib 1.6.0, streamlit 1.66.1, requests 2.34.2, plus statsmodels and openpyxl for evaluation).
- **Streamlit Cloud:** Python 3.12.
- **Local preview:** `MLDL Capstone Group/.claude/launch.json` (name `spotcheck`, port 8501).

## 5. How to ship a change

1. Edit in the Session 19 folder (never only in `repo/`).
2. Run all three checks; each must print PASSED:
   ```bash
   cd "ML Capstone/Session 19 - SpotCheck" && ../../.venv/bin/python test_reference.py && ../../.venv/bin/python test_app.py && ../../.venv/bin/python planner/test_planner.py
   ```
   Tests set `PLANNER_NO_LLM=1`, so they never call Gemini.
3. Copy the changed files into `repo/` (same paths) and run the three checks there.
4. In `repo/`: `git add` + `git commit` (author Saswat Pani / GitHub no-reply).
5. **The team runs `git push`.**
6. Check the live app: T03 ₹718 / 92%, and one Plan question. Log it in `PROJECT_LOG.md`.

## 6. Known quirks and lessons

- **Gemini speed varies a lot:** about 2 s in the morning, 14–23 s with 503 "high demand" errors in the afternoon of 2026-10-27. Hence rules first, Gemini only when needed.
  - `gemini-2.5-flash` is not available to new users.
  - `gemini-3.8-flash` timed out.
  - Change the model with `GEMINI_MODEL` in secrets.
- **Streamlit caches the page CSS:** after editing CSS in `app.py`, **reload the browser page** (a rerun keeps the old style). After editing `planner/*.py`, **restart the server** (imported modules are cached).
- **Streamlit wraps widgets:** card width rules must target `.st-key-cardrow > [data-testid="stLayoutWrapper"]`. Streamlit pulls a leading emoji in a button label out as an icon. A `st.form` blocks live updates, which is why the what-if card is no longer a form.
- **Orange remembers widget settings** across workflows. They're now saved in the `.ows` with versions.
- **The workbook's original rating coefficients** (0.143, 0.175, …) were not from this workflow; Python matches the Orange GUI. The workbook's "Rating Coefficients" sheet is stale.
- **Streamlit Cloud iframe:** for automated checks, open `<live URL>/~/+/`. Scripted checks must click in short steps; each browser call times out after 45 s.
- **Claude can't create public repos** (permission check); the team pushes.
- **Disk space** on this Mac is low (about 3.7 GB free).
