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
from typing import List, Optional, Dict, Any
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
df = df.sort_values('Arena Score', ascending=False, na_position='last')
df['Rank* (UB)'] = range(1, len(df) + 1)

def fetch_openrouter_pricing() -> Dict[str, Any]:
    """Fetch pricing data from OpenRouter API as fallback."""
    try:
        resp = requests.get("https://openrouter.ai/api/v1/models", timeout=30)
        resp.raise_for_status()
        openrouter_data = resp.json()

        # First pass: collect all models and identify free/paid pairs
        all_models = {}
        free_model_bases = set()
        
        for model in openrouter_data.get('data', []):
            model_id = model.get('id') or ''
            if not model_id:
                continue
            
            all_models[model_id] = model
            
            # Track models with :free suffix
            if ':free' in model_id:
                base_id = model_id.replace(':free', '')
                free_model_bases.add(base_id)

        # Convert OpenRouter format to match LiteLLM structure
        openrouter_models = {}
        for model_id, model in all_models.items():
            # Skip free models if a paid version exists
            if ':free' in model_id:
                base_id = model_id.replace(':free', '')
                if base_id in all_models:
                    print(f"   ⏭️  Skipping free model '{model_id}' because paid version exists")
                    continue
            
            # Safely handle None values
            canonical_slug = model.get('canonical_slug') or ''
            hugging_face_id = model.get('hugging_face_id') or ''

            # Convert to lowercase only if not empty
            model_id_lower = model_id.lower() if model_id else ''
            canonical_slug = canonical_slug.lower() if canonical_slug else ''
            hugging_face_id = hugging_face_id.lower() if hugging_face_id else ''

            pricing = model.get('pricing', {})

            # Convert pricing from per-token to per-million-tokens for consistency
            prompt_cost = float(pricing.get('prompt', 0)) if pricing.get('prompt') else None
            completion_cost = float(pricing.get('completion', 0)) if pricing.get('completion') else None

            # Debug specific models
            if 'gemma-3-27b' in model_id.lower():
                print(f"   🔍 DEBUG gemma: {model_id}")
                print(f"      Raw pricing: prompt={pricing.get('prompt')}, completion={pricing.get('completion')}")
                print(f"      Converted: prompt_cost={prompt_cost}, completion_cost={completion_cost}")

            if prompt_cost is not None or completion_cost is not None:
                model_data = {
                    'input_cost_per_token': prompt_cost,
                    'output_cost_per_token': completion_cost,
                    'max_input_tokens': model.get('context_length'),
                    'max_output_tokens': model.get('top_provider', {}).get('max_completion_tokens'),
                    'litellm_provider': 'openrouter',
                    'mode': 'chat',
                    'openrouter_id': model.get('id'),
                    'canonical_slug': canonical_slug,
                    'hugging_face_id': hugging_face_id
                }

                # Add under multiple identifiers for better matching
                openrouter_models[model_id_lower] = model_data

                # Also add without the provider prefix for better matching
                if '/' in model_id_lower:
                    model_without_prefix = model_id_lower.split('/', 1)[1]
                    openrouter_models[model_without_prefix] = model_data

                if canonical_slug and canonical_slug != model_id_lower:
                    openrouter_models[canonical_slug] = model_data
                    # Add canonical slug without prefix too
                    if '/' in canonical_slug:
                        canonical_without_prefix = canonical_slug.split('/', 1)[1]
                        openrouter_models[canonical_without_prefix] = model_data

                if hugging_face_id and hugging_face_id != model_id_lower and hugging_face_id != canonical_slug:
                    openrouter_models[hugging_face_id] = model_data

        print(f"✅ Fetched pricing for {len(openrouter_models):,} model entries from OpenRouter")

        # Log some examples of what we got from OpenRouter
        debug_models = ['claude', 'glm', 'qwen', 'gpt-5']
        for debug_name in debug_models:
            matching_or_models = [k for k in openrouter_models.keys() if debug_name in k.lower()]
            if matching_or_models:
                print(f"   OpenRouter models containing '{debug_name}': {matching_or_models[:3]}{'...' if len(matching_or_models) > 3 else ''}")

        # Check specifically for GPT-5 in OpenRouter
        if 'gpt-5' in openrouter_models:
            gpt5_data = openrouter_models['gpt-5']
            print(f"   🔍 GPT-5 found in OpenRouter with pricing: input=${gpt5_data.get('input_cost_per_token')}, output=${gpt5_data.get('output_cost_per_token')}")

        return openrouter_models
    except Exception as e:
        print(f"⚠️ Failed to fetch OpenRouter pricing: {e}")
        return {}

# 2. Fetch model-pricing JSON from LiteLLM
resp = requests.get(
    "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
    timeout=30,
)
resp.raise_for_status()
model_info = resp.json()

# 2b. Fetch OpenRouter pricing as fallback
openrouter_models = fetch_openrouter_pricing()

# Merge OpenRouter data into model_info for models not in LiteLLM
for model_id, model_data in openrouter_models.items():
    if model_id not in model_info:
        model_info[model_id] = model_data

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

def generate_model_variants(text: str) -> List[str]:
    """Generate multiple variants of a model name for better matching."""
    if not isinstance(text, str):
        return [text]

    variants = set()

    # Start with the cleaned base name
    base = clean(text)
    variants.add(base)

    # Remove common prefixes
    for prefix in ['openai/', 'anthropic/', 'google/', 'meta/', 'qwen/', 'z-ai/', 'zhipuai/']:
        if base.startswith(prefix):
            variants.add(base[len(prefix):])

    # Normalize separators
    normalized = re.sub(r'[-_\s]+', '-', base)
    variants.add(normalized)
    variants.add(re.sub(r'[-_\s]+', '', base))  # no separators
    variants.add(re.sub(r'[-_\s]+', '_', base))  # underscores

    # Remove version suffixes and dates
    for variant in list(variants):
        # Remove dates like -2507, -0709, -20250805
        no_date = re.sub(r'-\d{4}(-\d{2})?(-\d{2})?$', '', variant)
        variants.add(no_date)

        # Remove version numbers like -4.1, -235b
        no_version = re.sub(r'-\d+(\.\d+)?[a-z]*$', '', variant)
        variants.add(no_version)

        # Remove instruct/chat suffixes
        no_suffix = re.sub(r'-(instruct|chat|preview|turbo)$', '', variant)
        variants.add(no_suffix)

    # Handle specific model name patterns
    for variant in list(variants):
        # GLM-4.5 variants
        if 'glm' in variant:
            variants.add(re.sub(r'glm-?(\d+\.?\d*)', r'glm-\1', variant))
            variants.add(re.sub(r'glm-?(\d+\.?\d*)', r'glm\1', variant))

        # Claude variants
        if 'claude' in variant:
            # claude-opus-4.1 -> claude-4.1-opus, etc.
            claude_match = re.match(r'claude-?(.+)', variant)
            if claude_match:
                parts = claude_match.group(1).split('-')
                if len(parts) >= 2:
                    variants.add(f"claude-{'-'.join(reversed(parts))}")

        # Qwen variants
        if 'qwen' in variant:
            # Handle qwen3-235b-a22b-instruct-2507 patterns
            qwen_base = re.sub(r'qwen(\d+)', r'qwen\1', variant)
            variants.add(qwen_base)
            # Remove model size indicators
            variants.add(re.sub(r'-\d+b(-a\d+b)?', '', variant))

    return list(variants)

def create_matching_index(model_df: pd.DataFrame) -> Dict[str, str]:
    """Create a comprehensive matching index for model names."""
    matching_index = {}

    for _, row in model_df.iterrows():
        model_id = row['model']

        # Add all variants of the model name
        for variant in generate_model_variants(model_id):
            if variant and variant not in matching_index:
                matching_index[variant] = model_id

    return matching_index

# Enhance OpenRouter data processing to include multiple identifiers
openrouter_models = fetch_openrouter_pricing()

# Process OpenRouter models with multiple identifiers
enhanced_openrouter = {}
for model_data in openrouter_models.values():
    # Extract model info from the raw data if available
    pass

# Add OpenRouter models with their various identifiers
for model_id, model_data in openrouter_models.items():
    if model_id not in model_info:
        model_info[model_id] = model_data

    # Also add canonical slug and hugging face variants if we can extract them
    # This would require modifying fetch_openrouter_pricing to preserve this info

model_df = (
    pd.DataFrame(
        [
            dict(model=k, **v)
            for k, v in model_info.items()
        ]
    )
)

df["Model"] = df["Model"].map(clean)
model_df["model"] = model_df["model"].map(clean)

# Create comprehensive matching index
matching_index = create_matching_index(model_df)

print(f"📊 Created matching index with {len(matching_index):,} variants for {len(model_df):,} models")

# Show examples of what's in our matching index for debugging
debug_examples = {}
for key in matching_index.keys():
    for debug_name in ['claude', 'glm', 'qwen']:
        if debug_name in key.lower():
            if debug_name not in debug_examples:
                debug_examples[debug_name] = []
            if len(debug_examples[debug_name]) < 5:
                debug_examples[debug_name].append(key)

for debug_name, examples in debug_examples.items():
    print(f"   Matching index entries containing '{debug_name}': {examples}")

# 4. Advanced matching strategy
def find_best_match(leaderboard_name: str) -> Optional[str]:
    """Find the best match for a leaderboard model name."""
    variants = generate_model_variants(leaderboard_name)

    for variant in variants:
        if variant in matching_index:
            return matching_index[variant]

    return None

# Apply advanced matching with detailed logging
def find_best_match_with_logging(leaderboard_name: str) -> Optional[str]:
    """Find the best match for a leaderboard model name with detailed logging."""
    # Add logging for specific models we're interested in
    debug_models = ['claude opus 4.1', 'glm-4.5', 'qwen3-235b-a22b-instruct-2507']
    should_log = any(debug_name.lower() in leaderboard_name.lower() for debug_name in debug_models)

    if should_log:
        print(f"\n🔍 DEBUG: Matching '{leaderboard_name}'")

    variants = generate_model_variants(leaderboard_name)

    if should_log:
        print(f"   Generated {len(variants)} variants: {variants[:10]}{'...' if len(variants) > 10 else ''}")

    for i, variant in enumerate(variants):
        if variant in matching_index:
            matched_model = matching_index[variant]
            if should_log:
                print(f"   ✅ MATCH found at variant #{i}: '{variant}' -> '{matched_model}'")
            return matched_model

    if should_log:
        print(f"   ❌ NO MATCH found for any variant")
        # Show what's available that might be similar
        similar_keys = [k for k in matching_index.keys() if any(word in k for word in leaderboard_name.lower().split())][:5]
        if similar_keys:
            print(f"   Similar available keys: {similar_keys}")

    return None

df['matched_model'] = df['Model'].apply(find_best_match_with_logging)

# Debug: Check what we have for Claude models specifically
claude_models_in_df = df[df['Model'].str.contains('claude', case=False, na=False)]
if not claude_models_in_df.empty:
    print(f"\n🔍 CLAUDE DEBUG: Found {len(claude_models_in_df)} Claude models in leaderboard:")
    for _, row in claude_models_in_df.iterrows():
        print(f"   Leaderboard: '{row['Model']}' -> matched: '{row['matched_model']}'")

        # Check if this matched model exists in our pricing data
        if row['matched_model'] and row['matched_model'] in model_df['model'].values:
            pricing_row = model_df[model_df['model'] == row['matched_model']].iloc[0]
            input_cost = pricing_row.get('input_cost_per_token')
            output_cost = pricing_row.get('output_cost_per_token')
            print(f"      -> Found in pricing data: input=${input_cost}, output=${output_cost}")
        else:
            print(f"      -> ❌ NOT FOUND in pricing data")

# For models that match multiple pricing entries, prefer ones with actual cost data
def select_best_pricing_row(group):
    """Select the best pricing row from a group of matches."""
    # Prefer rows with both input and output cost data that are NOT zero
    has_both_costs_nonzero = group[
        (group['input_cost_per_token'].notna()) &
        (group['output_cost_per_token'].notna()) &
        (group['input_cost_per_token'] > 0) &
        (group['output_cost_per_token'] > 0)
    ]

    if not has_both_costs_nonzero.empty:
        # If multiple have both costs, prefer primary providers
        primary_providers = ['openai', 'anthropic', 'vertex_ai-language-models', 'gemini', 'openrouter']
        primary_matches = has_both_costs_nonzero[has_both_costs_nonzero['litellm_provider'].isin(primary_providers)]
        if not primary_matches.empty:
            return primary_matches.iloc[0]
        return has_both_costs_nonzero.iloc[0]

    # Fall back to rows with both costs (even if zero - for free models)
    has_both_costs = group[
        (group['input_cost_per_token'].notna()) &
        (group['output_cost_per_token'].notna())
    ]

    if not has_both_costs.empty:
        return has_both_costs.iloc[0]

    # If none have both costs, prefer ones with at least input cost
    has_input_cost = group[group['input_cost_per_token'].notna()]
    if not has_input_cost.empty:
        return has_input_cost.iloc[0]

    # Otherwise return the first row
    return group.iloc[0]

# Group pricing data by model and select best row for each
model_df_best = model_df.groupby('model').apply(select_best_pricing_row).reset_index(drop=True)

print(f"📊 Reduced pricing data from {len(model_df):,} to {len(model_df_best):,} rows by selecting best pricing per model")

# Merge using the matched model names with the deduplicated pricing data
merged = df.merge(
    model_df_best,
    left_on='matched_model',
    right_on='model',
    how='left',
    suffixes=('', '_pricing')
)

# Fill in the model column for successful matches
merged['model'] = merged['model'].fillna(merged['matched_model'])

print(f"✅ Matched pricing for {merged['input_cost_per_token'].notna().sum():,} out of {len(merged):,} models")

# Debug: Check Claude pricing after merge
claude_merged = merged[merged['Model'].str.contains('claude', case=False, na=False)]
if not claude_merged.empty:
    print(f"\n🔍 CLAUDE PRICING DEBUG after merge:")
    for _, row in claude_merged.iterrows():
        input_cost = row.get('input_cost_per_token')
        output_cost = row.get('output_cost_per_token')
        print(f"   '{row['Model']}': input=${input_cost}, output=${output_cost}")
        if pd.isna(input_cost) and pd.isna(output_cost):
            print(f"      ❌ NO PRICING DATA found for this model")

for old, new in {
    "input_cost_per_token": "input_cost_per_million_tokens ($)",
    "output_cost_per_token": "output_cost_per_million_tokens ($)",
    "output_cost_per_reasoning_token": "output_cost_per_reasoning_per_million_tokens ($)",
    "input_cost_per_token_batches": "input_cost_per_million_tokens_batches ($)",
    "output_cost_per_token_batches": "output_cost_per_million_tokens_batches ($)",
}.items():
    if old in merged.columns:
        print(f"\n🔍 Converting {old} to {new}")

        # Convert from per-token to per-million-tokens, preserving NaN for missing values
        numeric_values = pd.to_numeric(merged[old], errors="coerce")

        # Multiply by 1M first - this is critical to do before ANY formatting
        converted_values = numeric_values * 1_000_000
        
        # Store as numeric float64 (NOT string yet)
        merged[new] = converted_values.astype('float64')

        # Debug: Show values specifically for gemma-3-27b
        gemma_rows = merged[merged['Model'].str.contains('gemma-3-27b', case=False, na=False)]
        for _, row in gemma_rows.iterrows():
            original_val = row.get(old)
            converted_val = row.get(new)
            print(f"   '{row['Model']}' {old}: {original_val} -> {converted_val}")
            print(f"      Type: {type(converted_val)}, Value as float: {float(converted_val) if pd.notna(converted_val) else 'NaN'}")

        merged.drop(columns=old, inplace=True)

# Debug: Check final pricing values before writing CSV
claude_final = merged[merged['Model'].str.contains('claude', case=False, na=False)]
if not claude_final.empty:
    print(f"\n🔍 FINAL CSV DEBUG before writing:")
    for _, row in claude_final.head(3).iterrows():
        input_cost = row.get('input_cost_per_million_tokens ($)')
        output_cost = row.get('output_cost_per_million_tokens ($)')
        print(f"   '{row['Model']}': input=${input_cost}, output=${output_cost}")

# 5. Validate data types before writing CSV
cost_columns = [col for col in merged.columns if 'cost_per_million_tokens' in col]
print(f"\n🔍 FINAL VALIDATION before CSV write:")
print(f"   Cost columns: {cost_columns}")

for col in cost_columns[:2]:  # Check first 2 cost columns
    print(f"   {col} dtype: {merged[col].dtype}")
    sample_values = merged[col].dropna().head(3)
    print(f"   Sample non-null values: {list(sample_values)}")

# Ensure numeric columns are properly formatted and convert to strings to avoid pandas serialization issues
for col in cost_columns:
    if col in merged.columns:
        # Convert to numeric first
        numeric_col = pd.to_numeric(merged[col], errors='coerce')

        # Debug: Show what we have before string conversion
        gemma_debug = merged[merged['Model'].str.contains('gemma-3-27b', case=False, na=False)][col].head(1)
        if not gemma_debug.empty:
            print(f"   Final {col} numeric values for gemma-3-27b before CSV write: {list(gemma_debug)}")
            print(f"      Raw value: {gemma_debug.iloc[0]}")

        # Convert to strings - handle very small values properly
        def format_cost(x):
            if pd.isna(x):
                return ""
            # Force to float to avoid any type issues
            val = float(x)
            # Format with 2 decimal places (e.g., 0.04 not 0.00)
            return f"{val:.2f}"
        
        merged[col] = numeric_col.apply(format_cost)

        # Final debug: Show string values
        if not gemma_debug.empty:
            gemma_final = merged[merged['Model'].str.contains('gemma-3-27b', case=False, na=False)][col].head(1)
            print(f"   Final {col} string values for gemma-3-27b: {list(gemma_final)}")

# Reorder columns to put cost columns at the front for better CSV parsing
cost_cols = [col for col in merged.columns if 'cost_per_million_tokens' in col]
other_cols = [col for col in merged.columns if col not in cost_cols]

# Create new column order: essential columns first, then cost columns, then the rest
essential_cols = ['rank_icon', 'Model', 'Arena Score', 'Organization', 'License']
remaining_cols = [col for col in other_cols if col not in essential_cols]

new_column_order = essential_cols + cost_cols + remaining_cols
merged_reordered = merged[new_column_order]

# Write CSV with reordered columns
merged_reordered.to_csv("chatbot_arena_leaderboard_with_cost.csv", index=False)
print("💾 CSV written with cost columns moved to front")

top100_md = merged.head(100).to_markdown(index=False)
with open("markdown_preview.md", "w", encoding="utf-8") as f:
    f.write(top100_md)
print("💾 markdown_preview.md (top 100) written")
