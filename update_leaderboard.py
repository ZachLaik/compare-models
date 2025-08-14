
#!/usr/bin/env python3
"""
Download Chatbot-Arena+ leaderboard data from OpenLM.ai, enrich it with model pricing,
and write:
  • chatbot_arena_leaderboard_with_cost.csv  (full table)
  • markdown_preview.md                      (top-100 rows, GitHub-friendly)
Run daily via GitHub Actions.
"""

import pandas as pd
import requests
import re
from typing import List, Optional
from bs4 import BeautifulSoup

def parse_leaderboard_html(html: str) -> pd.DataFrame:
    """Parse Chatbot Arena+ leaderboard HTML into a pandas DataFrame.

    Args:
        html: Raw HTML of the Chatbot Arena+ page.

    Returns:
        A ``pandas.DataFrame`` with one row per model and columns:
        ``rank_icon``, ``model``, ``arena_elo``, ``coding``, ``vision``,
        ``aaii``, ``mmlu_pro``, ``arc_agi``, ``organisation``, ``license``.

    Raises:
        ValueError: If no table with class ``sortable`` is found in the HTML.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"class": "sortable"})
    if table is None:
        raise ValueError("Could not find leaderboard table in the provided HTML.")

    headers = [
        "rank_icon",
        "model",
        "arena_elo",
        "coding",
        "vision",
        "aaii",
        "mmlu_pro",
        "arc_agi",
        "organisation",
        "license",
    ]
    data: List[List[Optional[str]]] = []

    # Iterate over each table row in tbody
    tbody = table.find("tbody")
    for row in tbody.find_all("tr"):
        cols = row.find_all("td")
        if not cols:
            continue
        row_data: List[Optional[str]] = []
        # Column 0: rank icon (🏆, 🥇, 🥈, etc.)
        rank_icon = cols[0].get_text(strip=True) if cols[0] else None
        row_data.append(rank_icon)
        # Column 1: model name
        model = cols[1].get_text(strip=True) if cols[1] else None
        row_data.append(model)
        # Columns 2-8: numeric metrics (code inside <code> tags)
        for i in range(2, 8):
            cell = cols[i] if i < len(cols) else None
            if cell:
                # If the cell contains code tags, extract the numeric text
                code_tags = cell.find_all("code")
                if code_tags:
                    # Some cells highlight the highest value within <span class="mark"><strong><code>...</code></strong></span>
                    # We take the first <code> tag value
                    value = code_tags[0].get_text(strip=True)
                else:
                    value = cell.get_text(strip=True)
                row_data.append(value if value else None)
            else:
                row_data.append(None)
        # Column 8: organisation (contains text after an optional <img> or <svg> icon)
        organisation_cell = cols[8] if len(cols) > 8 else None
        organisation = None
        if organisation_cell:
            # Remove any <img> or <svg> tags then get remaining text
            for tag in organisation_cell.find_all(["img", "svg"]):
                tag.decompose()
            organisation = organisation_cell.get_text(strip=True) or None
        row_data.append(organisation)
        # Column 9: license
        license_cell = cols[9] if len(cols) > 9 else None
        license_value = license_cell.get_text(strip=True) if license_cell else None
        row_data.append(license_value)
        data.append(row_data)

    df = pd.DataFrame(data, columns=headers)
    return df

def scrape_openlm_chatbot_arena(url: str = "https://openlm.ai/chatbot-arena/",
                                 timeout: float = 15.0,
                                 user_agent: Optional[str] = None) -> pd.DataFrame:
    """Fetch and parse the Chatbot Arena+ leaderboard.

    Args:
        url: The URL of the leaderboard page (default: Chatbot Arena+).
        timeout: Timeout in seconds for the HTTP request.
        user_agent: Optional custom User‑Agent string to include in the request.

    Returns:
        A pandas DataFrame with the leaderboard data.

    Raises:
        requests.HTTPError: If the HTTP request fails.
        ValueError: If no table is found in the HTML.
    """
    headers = {}
    if user_agent:
        headers["User-Agent"] = user_agent
    else:
        headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0 Safari/537.36"
        )
    response = requests.get(url, headers=headers, timeout=timeout)
    # Raise an exception for HTTP errors (e.g., 403)
    response.raise_for_status()
    return parse_leaderboard_html(response.text)

# 1. Fetch data from OpenLM.ai
df = scrape_openlm_chatbot_arena()
print(f"✅ Fetched {len(df):,} leaderboard rows from OpenLM.ai")

# Map OpenLM.ai columns to expected columns for the frontend
df = df.rename(columns={
    'model': 'Model',
    'arena_elo': 'Arena Score',
    'organisation': 'Organization',
    'license': 'License'
})

# Add a numeric rank based on Arena Score (higher is better)
df['Arena Score'] = pd.to_numeric(df['Arena Score'], errors='coerce')
df = df.sort_values('Arena Score', ascending=False, na_last=True)
df['Rank* (UB)'] = range(1, len(df) + 1)

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
