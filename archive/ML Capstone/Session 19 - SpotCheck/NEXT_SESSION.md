# SpotCheck – Next session (updated 2026-10-27, evening)

Pick up from here. Current state: `HANDOFF.md`. Rules: `../CLAUDE.md`. Full history: `PROJECT_LOG.md`.

## Start-up checklist (5 minutes)

1. **Claude:** read `../CLAUDE.md` → `HANDOFF.md` → the last 5 entries of `PROJECT_LOG.md`.
2. Make sure the workbook and Orange are **closed** (no `~$SpotCheck_Session19_Pack.xlsx`; Orange not running) before editing them.
3. Confirm nothing has drifted:
   ```bash
   cd "/Users/DELL/MLDL Capstone Group/ML Capstone/Session 19 - SpotCheck" && ../../.venv/bin/python test_reference.py && ../../.venv/bin/python test_app.py && ../../.venv/bin/python planner/test_planner.py && git -C repo status -sb
   ```
   All three should print PASSED, and `repo` should show `## main...origin/main` with no changes (last commit `620c0a3`).
4. **Wake the live app** (it sleeps after 12 h): https://spotcheck-tbcb5npizuvfmpfgto7a2a.streamlit.app/.
   - Run T03 Roundup Cafe → expect ₹718 and 92%.
   - Then Compare → "Choose this one" → "Plan this concept" → ask "How many staff do I need?" → "100-200 guests" → expect a band (≈ 13–16 with the defaults).
5. Ask the team which session or deliverable is next, and its date. Record dates in `PROJECT_LOG.md` → Project facts.

## To-do, in priority order

### 1. Accuracy and housekeeping (small, do first)

- [ ] **Update stale facts in `../CLAUDE.md`** (needs team OK; CLAUDE.md says "do not change without asking"):
  - Seed stability: replace "₹14–92 … MAE ₹148–160" with the measured **₹5–56 per restaurant, hold-out MAE ₹142–152**.
  - CV: Orange GUI RF R² **0.725** vs LR **0.608**; GroupKFold 0.716 vs 0.606.
  - **Add the Plan feature to the project facts:**
    - the 5 synthetic-data Linear Regression targets and break-even as a formula;
    - Gemini only reads messages (it never produces a number);
    - `planner/` is the new folder.
  - **Clarify scope:** the planner's *synthetic* data was requested by the faculty and team, so it's not a new real dataset.
- [ ] **Workbook:**
  - 'Orange Workflow Guide' B10 still says the coefficient tables are "the final-model coefficients the app needs". Change to: the app loads `.joblib` models.
  - The 'Rating Coefficients' sheet holds old values; replace them with the `rating_model.joblib` coefficients (offered before, not done).
  - Do both via openpyxl in `evaluate.py`.
- [ ] *(Optional)* Add a "Plan models (synthetic)" sheet to the workbook from `planner/models/planner_metrics.json` and `planner_coefficients.csv`, clearly labelled synthetic.

### 2. App quality (needs the team's phones)

- [ ] **Real-phone test** on iOS Safari and Android Chrome:
  - Swiping the Compare cards, the circle/"Choose this one" buttons, the tab bar.
  - Plan chips and the chat input with the keyboard open.
  - Summary download.

  Note any issues in `PROJECT_LOG.md`.
- [ ] **Gemini behaviour:**
  - Watch for slow replies (it took 14–23 s at busy times).
  - If it stays slow, try `GEMINI_MODEL` in secrets, e.g. another model listed for the key (check the list first).
  - The chat always falls back to the rules.
- [ ] *(Optional)* **Plan answers in the Summary download:** consider adding the break-even assumptions and the stated facts.
- [ ] *(Optional)* **Shorter URL:** Streamlit Cloud → app → ⋮ → Settings → General → custom subdomain. Then update `PROJECT_LOG.md`, `HANDOFF.md` and `repo/README.md`.

### 3. Evidence for the report and presentation

- [ ] **Assumption-check visuals in Orange** (price residual funnel/skew; rating calibration plot). See PROJECT_LOG 2026-10-26.
- [ ] *(Optional)* **Plan models in Orange:** the `planner/data/planner_train.tab` and `planner_holdout.tab` files are ready.
  - All 5 targets are **meta**; set one as target in the File widget.
  - Show Linear Regression CV, plus residual plots that look normal (by construction).
- [ ] **Screenshots of the live app** for the report: wizard, results, Compare with a selected card, Plan chat (objective buttons, a follow-up with chips, a range answer card, break-even card), Summary with "My opening plan".
- [ ] **Professor-facing explanations already written in the conversation** (summarise into the report):
  - how the app works and how numbers are calculated;
  - the Orange workflow and its settings;
  - coefficients and confusion matrices in plain words;
  - why LR assumptions matter for inference but not our CV-measured predictions;
  - **for the planner:** the data is synthetic by design, Linear Regression fits by construction, the high R² is not evidence about real restaurants, Gemini only reads messages, and break-even is a stated formula.

### 4. Course deliverables (check what's next)

- [ ] Read `../GCP.1 Instructions and Guidelines.pdf` and `../MICA ML Capstone Hub.htm` (Zomato/SpotCheck parts only; ignore SmartNudge) and list what Sessions 20–24 require. Turn that into tasks here.
- [ ] **Demo rehearsal:** follow the DEMO READINESS block in `../CLAUDE.md` (open the link 10–15 min early, run T03, keep the tab open).
  - Add one Plan question with a range to the demo script.
  - **Backups:** local `streamlit run app.py`, or the three test scripts.

## Open decisions for the team

| Question | Current choice | Evidence |
|---|---|---|
| Rating: keep Logistic Regression or switch to Random Forest? | **LR (FINAL)** | RF AUC 0.825 vs LR 0.811; LR is calibrated and explainable |
| Planner: stay on synthetic data, or look for real cost/staff data later? | **Synthetic, labelled** | No real source in the Zomato data; CLAUDE.md says new real datasets need team OK |
| Gemini model if it stays slow | `gemini-3.5-flash-lite` | 2 s → 14–23 s depending on Google's load; rules fallback always works |
| Custom app subdomain? | Not set | Optional; cosmetic |
| Upcoming session dates and requirements? | Unknown ("class sessions") | Ask at the start of the next session |

## Don'ts (from `../CLAUDE.md` and this project)

- No login or accounts.
- No LLM-generated predictions: Gemini only reads messages.
- Never edit or commit raw data, `.tab` files or `planner/data/planner_train.*`.
- Never commit secrets: `.streamlit/secrets.toml` and `planner/.streamlit/secrets.toml` stay local.
- Never retrain silently: retraining changes `reference_tests.csv` / `planner_reference.csv`.
- Ask clarifying questions as multiple choice.
- Log every decision.
