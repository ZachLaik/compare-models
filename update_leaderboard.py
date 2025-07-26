#!/usr/bin/env python3
"""
Download Chatbot-Arena leaderboard data, enrich it with model pricing,
and write:
  • chatbot_arena_leaderboard_with_cost.csv  (full table)
  • markdown_preview.md                      (top-100 rows, GitHub-friendly)
Run daily via GitHub Actions.
"""

import pandas as pd
import requests
import re
from gradio_client import Client

# 1. Fetch data from Gradio API
client = Client("lmarena-ai/chatbot-arena-leaderboard")
table_data = client.predict(
    category="Overall",
    filters=[],
    api_name="/update_leaderboard_and_plots"
)[0]

headers = table_data["value"]["headers"]
data = table_data["value"]["data"]
if not (headers and data):
    raise RuntimeError("❌ No data returned from Gradio API")

df = pd.DataFrame(data, columns=headers)
print(f"✅ Fetched {len(df):,} leaderboard rows")

# 2. Fetch model-pricing JSON
resp = requests.get(
    "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
    timeout=30,
)
resp.raise_for_status()
model_info = resp.json()

model_df = (
    pd.DataFrame(
        [
            dict(model=k, **v)
            for k, v in model_info.items()
        ]
    )
)

# 3. Normalise model names
def clean(text: str) -> str:
    if not isinstance(text, str):
        return text
    text = re.sub(r"<.*?>", "", text)          # strip HTML
    text = re.sub(r"\s*\(.*?\)\s*", "", text)  # drop (…) hints
    text = text.split("/")[-1]                 # keep suffix after /
    return text.strip().lower()

df["Model"] = df["Model"].map(clean)
model_df["model"] = model_df["model"].map(clean)

# 4. Merge & transform prices → $/1M tokens
merged = df.merge(model_df, left_on="Model", right_on="model", how="left")

for old, new in {
    "input_cost_per_token": "input_cost_per_million_tokens ($)",
    "output_cost_per_token": "output_cost_per_million_tokens ($)",
    "output_cost_per_reasoning_token": "output_cost_per_reasoning_per_million_tokens ($)",
    "input_cost_per_token_batches": "input_cost_per_million_tokens_batches ($)",
    "output_cost_per_token_batches": "output_cost_per_million_tokens_batches ($)",
}.items():
    if old in merged.columns:
        merged[new] = pd.to_numeric(merged[old], errors="coerce") * 1_000_000
        merged.drop(columns=old, inplace=True)

# 5. Write artifacts
merged.to_csv("chatbot_arena_leaderboard_with_cost.csv", index=False)
print("💾 CSV written")

top100_md = merged.head(100).to_markdown(index=False)
with open("markdown_preview.md", "w", encoding="utf-8") as f:
    f.write(top100_md)
print("💾 markdown_preview.md (top 100) written")
