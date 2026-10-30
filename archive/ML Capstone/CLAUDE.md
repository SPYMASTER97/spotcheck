# CLAUDE.md — SpotCheck (MICA ML Capstone)

Read this file fully before doing anything. These rules apply to every task in this folder and all subfolders.

## 1. Scope: Zomato use case ONLY

- This project is **SpotCheck**: a restaurant concept, price and rating validator for Bangalore, built on the Kaggle Zomato Bangalore Restaurants dataset (himanshupoddar/zomato-bangalore-restaurants).
- Work ONLY on the Zomato / SpotCheck use case.
- Ignore everything about **SmartNudge** (Proposal 1 in `AMLDLBI_Peddi_Koushik_GCP_Proposal.docx`, the UCI Online Shoppers data). Do not read, use, or suggest it.
- Do not bring in other datasets, other cities, or other use cases. If a request seems to go outside Zomato/SpotCheck, stop and ask (see section 3).

## 2. Project facts (do not change without asking)

- Working folder: `Session 19 - SpotCheck/`.
- Data: `zomato_price.tab` / `zomato_rating.tab` (9,244 rows, full, used for CV); `*_train.tab` (9,234 rows, training); `reference_tests_*.tab` / `reference_tests.csv` (10 hold-out restaurants T01–T10). Orange `.tab` files have 3 header rows (names, types, roles).
- Inputs: location (40 levels incl. "Other"), primary_type (12), has_bar, online_order, book_table, n_cuisines, 12 cuisine flags `c_*`. The rating model also uses cost_for_two.
- **Price model (FINAL): Random Forest regression** on cost_for_two (₹). Linear Regression is kept only for comparison: it violated linearity, homoscedasticity and normality, and its CV R² was ~0.61 vs ~0.71 for RF.
- **Rating model (FINAL): Logistic Regression** (Ridge/L2, C=1) on high_rating (Yes = rating ≥ 4.0).
- **Integration route (confirmed by facilitator):** Python app (Streamlit) → code on GitHub → deployed on Streamlit Community Cloud. The app loads the trained `.joblib` models; the models are not coded as formulas.
- Orange vs Python Random Forest: these never produce identical forests. With 100 trees, predictions on T01–T10 shift by about ₹14–92 per restaurant between random seeds (hold-out MAE ₹148–160). So:
  - Orange is the comparison/evaluation evidence.
  - The **10 reference outputs must come from the exact `.joblib` files the app loads**, via `predict.py`.
  - Always use a fixed `random_state` and never retrain silently. Retraining changes the reference outputs.

## 3. Clarifying questions: ALWAYS multiple choice

- When anything is ambiguous, **ask before acting. Never guess.**
- Ask with the **AskUserQuestion tool** so the user can click options. Do not ask clarifying questions as free text in chat.
  - 1–4 questions per call, each with 2–4 short, mutually exclusive options.
  - Put your recommended option first and add "(Recommended)" to its label.
  - Add a one-line description to each option explaining its consequence.
  - Use multi-select only when several answers can genuinely apply.
- Ask in batches at the start of a task rather than interrupting repeatedly.
- If the AskUserQuestion tool is unavailable, use the same format as a numbered list (Q1: options A/B/C) and wait for the answer.

## 4. Hard rules

1. **Edit existing files in place. No `_v2` copies.** All Orange, workbook and data-related changes go into the files that already exist: `SpotCheck_workflow.ows`, `SpotCheck_Session19_Pack.xlsx`, `reference_tests.csv`, etc. Create a new file ONLY when no existing file can hold the content (e.g. Python scripts, `.joblib` model files, `requirements.txt`, `PROJECT_LOG.md`, the `repo/` folder); before creating one, say why no existing file fits.
   - The user's original `ML_Capstone.zip` is the backup. Before the first in-place edit of a task, confirm with AskUserQuestion that the user still has it stored outside this folder. Do not create backup copies inside the project.
   - Never edit the raw source data (`zomato.csv`, `zomato_clean.csv`) or the Orange input `.tab` files unless the user explicitly asks.
2. **Never use any LLM/AI service to produce a prediction.** Predictions come only from the trained models.
3. **Report numbers honestly.** If something doesn't reproduce, say so. Never tune numbers to match.
4. **Keep the 10-sample reference test format:** the same restaurants T01–T10, the existing columns of `reference_tests.csv` unchanged and in the same order (new output columns may only be appended at the end), and the same row-by-row layout as the "Hold-out Test" sheet.
5. **Never commit raw data** (`zomato.csv` is 574 MB, over GitHub's 100 MB limit, and the Kaggle licence names the original authors). Model files, code and the 10 reference rows only. Attribute the dataset in the README.
   - **Exception (team decision 2026-10-30):** before deleting the local copy, the whole project was archived in the public repo under `archive/`, **including the cleaned/derived data** (`zomato_clean.csv`, the `.tab` files, `planner/data/planner_train.*`). `zomato.csv` itself, secrets, `.venv` and the course documents (MICA guidelines PDF, Hub page, proposal .docx) are still NOT uploaded; `archive/README.md` records where to get them. The app at the repo root still uses only code, models and the 10 reference rows.
6. **Pin library versions** (scikit-learn especially) in `requirements.txt`. A model must be loaded with the version that saved it.
7. If `~$SpotCheck_Session19_Pack.xlsx` exists, the workbook is open in Excel. Stop and ask the user to close it.
8. **Log every decision** in `Session 19 - SpotCheck/PROJECT_LOG.md`: date, what changed, why, evidence. The course grades this log.
9. **No login, ever.** The app has no login, sign-up, user accounts or user profiles (decided by the team; matches the Capstone Hub P3 spec, "Version 1 excludes: login, user profiles…"). Do not build or suggest them. The UI is out of scope until the user says otherwise; screens and the user flow will be designed later in Google Stitch, starting directly at the input form.
10. Finish every task with at most 5 bullets: files changed, key numbers, what didn't work, manual steps for the user, what to check.

## 5. Demo / live-app reminder (Streamlit Community Cloud free tier)

Free tier facts (check docs.streamlit.io if unsure; limits can change):
- Free, with a `<name>.streamlit.app` subdomain. **No custom domain.**
- Unlimited **public** apps, but only **one private** app. The GitHub repo is normally public.
- About 1 GB memory, shared resources.
- **The app goes to sleep after 12 hours without traffic.** A visitor sees a "This app has gone to sleep" page with a button to wake it. Waking takes from under a minute to a few minutes.

**RULE: whenever the user mentions any of these:** demo, presentation, viva, session 20/21/22/23/24, sharing the link, another team testing the app, faculty review, or deploying, **print this block before anything else:**

> ⏰ **DEMO READINESS: SpotCheck live app**
> 1. Open the live link **at least 10–15 minutes before** the demo. If it shows "gone to sleep", click the wake button and wait until the form loads.
> 2. Run one reference restaurant (e.g. T03 Roundup Cafe) and check the output matches its Predicted cost / P(4.0+) in `reference_tests.csv`.
> 3. Keep the tab open. The app stays awake for 12 hours after the last visit.
> 4. Backup: run locally with `streamlit run app.py`, or show the `test_reference.py` result if the cloud is down.
> 5. Live URL: <read from PROJECT_LOG.md; if missing, ask the user for it>

- If the live URL or upcoming session dates are not in `PROJECT_LOG.md`, ask for them (AskUserQuestion) and record them.
- After any deploy or redeploy, record the live URL and date in `PROJECT_LOG.md` and show the reminder block.
