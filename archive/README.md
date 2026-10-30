# SpotCheck – full project archive

Everything from the local project folder (`MLDL Capstone Group/`), archived on 2026-10-30 before the local copy
was deleted. The deployed app is at the **repo root** (unchanged); this folder is the full working project behind it.

## What's here

| Path | What |
|---|---|
| `ML Capstone/CLAUDE.md` | Project rules for Claude sessions |
| `ML Capstone/Session 19 - SpotCheck/` | The working folder: `PROJECT_LOG.md` (graded decision log), `HANDOFF.md`, `NEXT_SESSION.md`, app and model code, `train_models.py`, `evaluate.py`, the evidence workbook `SpotCheck_Session19_Pack.xlsx`, the Orange workflow `SpotCheck_workflow.ows`, the cleaned data (`zomato_clean.csv`, `zomato_*.tab`, `reference_tests_*.tab`), `planner/` (synthetic planning data, models, chat), `design/` (Stitch exports and prompts), `TASK_01_switch_price_to_RF.md` |
| `.claude/launch.json` | Local preview config used with Claude Code (port 8501) |

The `repo/` subfolder of the working folder is not copied here: it **is** this repository (the root files).

## Not included (on purpose)

| Item | Why | How to get it back |
|---|---|---|
| `ML Capstone/zomato.csv/zomato.csv` (574,072,999 bytes) | Over GitHub's 100 MB limit; Kaggle licence | Kaggle: https://www.kaggle.com/datasets/himanshupoddar/zomato-bangalore-restaurants → `zomato.csv`. Check: SHA-256 `4b0c91c37585310d509873dc399fdf739c7d222fcf7a693e4461b23d25a9d43d` |
| Course documents: `GCP.1 Instructions and Guidelines.pdf`, `MICA ML Capstone Hub.htm` (+ `_files`), `AMLDLBI_Peddi_Koushik_GCP_Proposal.docx` | Belong to MICA / the proposal's author; this repo is public | Course site / the author |
| `.streamlit/secrets.toml`, `planner/.streamlit/secrets.toml` (Gemini API key) | Never commit secrets | The live app keeps its key in Streamlit Cloud → app → Settings → Secrets. For local use, create a new key in Google AI Studio and save it as `GEMINI_API_KEY = "…"` in `.streamlit/secrets.toml` |
| `.venv/` (Python 3.14 environment) | Rebuildable | See below |

## Restore the working project on a new machine

```bash
git clone https://github.com/SPYMASTER97/spotcheck.git
mkdir -p "MLDL Capstone Group" && cp -R "spotcheck/archive/ML Capstone" "MLDL Capstone Group/"
cp -R spotcheck "MLDL Capstone Group/ML Capstone/Session 19 - SpotCheck/repo"   # the deployable copy (keeps .git)
cd "MLDL Capstone Group" && python3 -m venv .venv && .venv/bin/pip install -r "ML Capstone/Session 19 - SpotCheck/requirements.txt" statsmodels openpyxl
cd "ML Capstone/Session 19 - SpotCheck" && ../../.venv/bin/python test_reference.py && ../../.venv/bin/python test_app.py && ../../.venv/bin/python planner/test_planner.py
```

Optional: download `zomato.csv` from Kaggle into `ML Capstone/zomato.csv/` (only needed to redo the cleaning;
the cleaned files are already here). Then read `HANDOFF.md` and `NEXT_SESSION.md`.
