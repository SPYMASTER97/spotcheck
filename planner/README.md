# SpotCheck Planner – "Plan my restaurant" chat (built, not yet in the app)

After a user has checked a concept in SpotCheck (location, type, services, cuisines, price), the planner chat
answers follow-up questions about **opening** it. Status: built and tested in this folder only. `app.py`,
the price/rating models, the Orange workflow and its `.tab` inputs are untouched (team decision, 2026-10-27);
wiring it into the app is a later step.

> **All planner answers are estimates from SYNTHETIC data.** The 5 targets were generated from straight-line
> formulas with normal noise (`generate_data.py → TRUE_RULES`). They show how the planner would work; they are
> not facts about real Bangalore restaurants. Price and rating (the main app) still come from real Zomato data.

## The 5 targets (Linear Regression, plain OLS)

| Target | Unit | Extra inputs the chat asks for |
|---|---|---|
| Floor area | sq ft | guests per day, delivery share |
| Staff headcount | people | guests per day, opening hours, menu items, delivery share |
| Initial investment | ₹ lakh | guests per day, taking over an existing site |
| Food cost (COGS) | % of sales | menu items, alcohol share (bars only) |
| Monthly revenue | ₹ lakh | guests per day, delivery share, opening hours |

Each also uses the main SpotCheck inputs (type, location, services, cuisines, cost for two) where its formula does.
**Break-even months** is a formula on top of the 5 predictions (rent, salaries and other costs are stated
assumptions in `plan_predict.ASSUMPTIONS`), not a sixth model.

Evaluation (10-fold CV, GroupKFold by restaurant, hold-out T01–T10, assumption checks): see `EVALUATION.md`.

## How the chat works

1. The user asks in their own words ("How many staff do I need?").
2. **Reading the question:** the built-in rules read every message first (fast): keywords, numbers, time
   ranges ("5pm to 3am" = 10 hours), share words ("a quarter" = 25%), budgets ("1 Cr" = ₹100 lakh).
   Only when they find nothing is Google Gemini asked (if a key is set; default model `gemini-3.5-flash-lite`,
   15 s timeout). Gemini only picks the question type and pulls out values the user stated. Its output is
   checked; anything unexpected, a timeout or no key → the rules' reading is used. A worded answer is confirmed
   back ("Got it: 10 hours."). **No number shown to the user comes from Gemini** (CLAUDE.md rule 2).
3. Missing inputs are asked one at a time ("not sure" → a typical value, said out loud).
4. The answer comes from `plan_predict.py` (the saved models), with a typical range (± CV MAE) and the
   synthetic-data label. Follow-ups like "what about 250 guests?" redo the last answer.

## Files

| File | What |
|---|---|
| `generate_data.py` | Builds `data/planner_train.*` (9,234 real Zomato input rows + synthetic extras/targets) and `data/planner_holdout.*` (T01–T10). Seed 19. `.tab` copies for Orange: all 5 targets are meta; set one as target in the File widget. |
| `train_planner.py` | Trains/evaluates the 5 models → `models/planner_models.joblib`, `planner_metrics.json`, `planner_coefficients.csv`, `data/planner_reference.csv`, `EVALUATION.md` |
| `plan_predict.py` | `predict`, `predict_all`, `break_even`, `missing_inputs`; the questions and allowed ranges |
| `chat_engine.py` | Message reading (Gemini + rules), follow-up questions, answer wording |
| `chat_demo.py` | Standalone Streamlit test page (pick a reference restaurant, then chat) |
| `test_planner.py` | 7 checks: models reproduce `planner_reference.csv`, chat flow, ranges, Gemini fallback, demo page renders |

## Run (from the Session 19 folder)

```bash
../../.venv/bin/python planner/generate_data.py && ../../.venv/bin/python planner/train_planner.py
../../.venv/bin/python planner/test_planner.py
../../.venv/bin/streamlit run planner/chat_demo.py
```

**Gemini key (optional):** create `planner/.streamlit/secrets.toml` with `GEMINI_API_KEY = "…"` (and optionally
`GEMINI_MODEL = "…"`, default `gemini-3.5-flash-lite`), or set the `GEMINI_API_KEY` environment variable before
running. Never commit the key (`.gitignore` here excludes it). When deployed: Streamlit Cloud → Settings → Secrets.
No extra library is needed (it calls the Gemini REST API with `requests`).
