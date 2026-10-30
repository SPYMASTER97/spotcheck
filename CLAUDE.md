# CLAUDE.md — SpotCheck app repo (deployed to Streamlit Community Cloud)

The parent `../../CLAUDE.md` rules apply here too: Zomato/SpotCheck only, multiple-choice clarifying questions via AskUserQuestion, no LLM predictions, honest reporting, and the demo reminder.

## What belongs in this repo
This folder is a deployable copy of files maintained in the parent folder. Edit the parent originals first, then copy them here; never let the two drift apart.
- `predict.py`: loads the models once; `predict_price()`, `predict_rating()`, `validate_inputs()`.
- `price_model.joblib` (Random Forest, FINAL price) and `rating_model.joblib` (Logistic Regression, FINAL rating).
- `requirements.txt` with exact pinned versions (scikit-learn, pandas, numpy, joblib, streamlit).
- `reference_tests.csv` (copied from the parent folder, incl. the expected output columns) and `test_reference.py`: the integration check.
- `README.md` with Kaggle dataset attribution and retraining steps.
- `app.py` (Streamlit): later, once screens are designed in Google Stitch.
- NOT allowed: raw data (`zomato.csv`, `*.tab`), secrets, API keys — **except** under `archive/`, which holds the full project including the cleaned/derived data (team decision 2026-10-30). Never `zomato.csv`, secrets or API keys, anywhere.

## Before every push
1. Run `python test_reference.py`. It must pass. If it fails, do not push; report the failure.
2. If any `.joblib` file changed, update the expected output columns in `../reference_tests.csv` (in place), copy it here again, update the evidence workbook, and log it in `PROJECT_LOG.md`. Retraining changes the reference outputs.
3. Check `requirements.txt` matches the versions used to save the models.

## Deploy and demo (Streamlit Community Cloud, free tier)
- Deploy: share.streamlit.io → sign in with GitHub → choose this repo, branch `main`, file `app.py`. Pushing to `main` redeploys automatically.
- The repo must be public unless it is the account's single private app.
- Apps sleep after 12 hours without traffic. **Show the DEMO READINESS block from the parent CLAUDE.md** whenever deploy, demo, presentation, viva or a session is mentioned, and after every deploy.
- Record the live `*.streamlit.app` URL in `PROJECT_LOG.md` after the first deploy.
