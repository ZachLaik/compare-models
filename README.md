Of course! Here’s the full README.md in clean markdown format, ready to drop into your repo:

# Compare Models — Daily Leaderboard + Pricing Merge

**Compare Models** keeps a daily, machine-readable snapshot of top chatbot models by **arena ranking** and **inference pricing**.  
It fetches fresh rankings from the **Open LLM/Chatbot Arena** and merges them with public pricing from **OpenRouter** and **LiteLLM**, producing a single CSV you can use in notebooks, dashboards, or apps.

> Primary artifact: **`chatbot_arena_leaderboard_with_cost.csv`** (updated daily)
> A hosted Webview with cost calculator is also available [here](https://zachlaik.github.io/compare-models)

---

## What this repo contains

- `update_leaderboard.py` — main script that:
  - pulls the latest arena ranking
  - fetches model pricing from OpenRouter & LightLLM
  - normalizes model names
  - merges everything into a single table
  - writes **`chatbot_arena_leaderboard_with_cost.csv`**
- `chatbot_arena_leaderboard_with_cost.csv` — the daily output (committed so it’s easy to consume)
- `.github/workflows/` — CI that runs the update daily and pushes changes
- `docs/` & `markdown_preview.md` — optional static preview material (for GitHub Pages or a simple hosted view)
- `requirements.txt` — minimal Python deps

---

## Why this exists

Comparing models is hard when quality and price live in different places. This repo gives you a **single source of truth** that answers:
- Which models rank highly today?
- What do they cost per input/output token?
- What’s the best **quality-per-€** tradeoff right now?

---

## Quick start

### 1) Clone and install
```bash
git clone https://github.com/ZachLaik/compare-models.git
cd compare-models
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
### 2) Run the updater locally

python update_leaderboard.py

This will regenerate chatbot_arena_leaderboard_with_cost.csv in the repo root.

No API keys are required for the default sources. If you point the script to authenticated endpoints in the future, document the required env vars here.

⸻

Using the CSV

In Python (pandas)
```
import pandas as pd

df = pd.read_csv("chatbot_arena_leaderboard_with_cost.csv")
```
# Examples:
# Top 10 by arena score
```
print(df.sort_values("arena_score", ascending=False).head(10))

# Best value: score per 1€ of output tokens (example columns)
df["value_score"] = df["arena_score"] / (df["output_usd_per_1k_tokens"])
print(df.sort_values("value_score", ascending=False).head(10))
```
In JavaScript (browser/Node)
```
// Browser (with a raw link to the CSV in your GitHub or CDN)
const res = await fetch('chatbot_arena_leaderboard_with_cost.csv');
const text = await res.text();
// Parse with PapaParse or your favorite CSV lib
```

⸻

Data sources & update cadence
	•	Ranking: Open LLM / Chatbot Arena (daily pull)
	•	Pricing: OpenRouter & LightLLM public pricing pages/APIs (daily pull)
	•	Schedule: GitHub Actions runs once per day and commits the refreshed CSV

⸻

GitHub Actions (CI)

The workflow in .github/workflows/:
	•	creates a Python environment
	•	runs update_leaderboard.py
	•	commits the new CSV if anything changed

If you ever need to modify the cadence, update the schedule: block in the workflow file.

⸻

File schema (CSV)

Columns may evolve, but the table generally includes:
	•	model — normalized model name
	•	provider — e.g., OpenRouter/LightLLM
	•	arena_rank / arena_score — model standing in the arena
	•	input_usd_per_1k_tokens — input pricing
	•	output_usd_per_1k_tokens — output pricing
	•	source_rank_url / source_price_url — provenance (when available)
	•	Additional helper columns used for joins and normalization

Check the current header row of chatbot_arena_leaderboard_with_cost.csv for the exact set.

⸻

Reproducibility & notes
	•	The script applies simple name normalization so “model aliases” map together before merging.
	•	If a model appears in rankings but not in pricing (or vice versa), it’s included with NaN for missing fields.
	•	No historical backfill: This repo is a daily snapshot. If you need history, keep the CSVs per date (/snapshots/2025-08-19.csv, etc.) or log to a datastore.

⸻

Roadmap ideas
	•	Publish a small JSON API (Cloudflare Workers / GitHub Pages + JS) for easy consumption.
	•	Add value metrics (e.g., score per $), latency, context window size.
	•	Expand pricing sources (vendor pages) and add validation checks.
	•	Keep a /snapshots/ folder for historical trend charts.

⸻

Contributing

PRs welcome!
Please keep the output CSV stable and documented, and avoid breaking column names without a migration note.

⸻

License

MIT

⸻

Acknowledgements
	•	[Open LLM/Chatbot Arena](https://openlm.ai/chatbot-arena) for community rankings.
	•	[OpenRouter](https://openrouter.ai/) and [LiteLLM](https://github.com/BerriAI/litellm) for public model pricing.
