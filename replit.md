# Overview

Compare Models is a daily-updated leaderboard system that aggregates LLM performance data from the Chatbot Arena with pricing information from multiple sources. The application automatically scrapes model rankings from OpenLM.ai's Chatbot Arena+ leaderboard, fetches pricing data from OpenRouter and LiteLLM, and produces a unified CSV dataset. It includes a web interface for searching models, calculating costs, and comparing quality-to-price ratios. The system runs automated daily updates via GitHub Actions to maintain current data.

# Recent Changes (November 2025)

- **Select All Button**: New button to quickly select or deselect all visible models in the table. Button toggles between "Select All" and "Deselect All" states.
- **Top 30 Button**: One-click button to select the top 30 models in the current table view for quick comparisons.
- **Chart Visualization**: New "Generate Chart" button creates an interactive scatter plot showing Arena Score vs Average API Cost for selected models. Each model appears as a uniquely colored dot with its name displayed directly next to it. Chart displays in a modal with tooltips showing model details.
- **Compact UI Design**: Reduced padding and font sizes across all cards and sections for more efficient space usage
- **Quick Scenarios Modal**: Clicking scenario buttons now opens a modal dialog asking users to choose between:
  - **Read**: Calculates input cost only (processing existing text)
  - **Write**: Calculates output cost only (generating new text)
  - **Summarize**: Calculates input cost + 30% output cost (reading and summarizing)
- **Currency Formatting**: Large numbers display with space separators (e.g., $30 000 000.00) for better readability
- **Hide N/A Models**: When costs are calculated, models without pricing are automatically hidden. Toggle "Show models without pricing" checkbox to view them
- **Fixed Scenario Values**: Corrected token amounts for NYT Archive (25B), U.S. Law (24B), Google Code (24B), and World Law (300B) scenarios
- **Referrer Tracking**: "Try in Blend" URLs include `ref=pricecomparisonlive` parameter for traffic attribution
- **Sortable Columns**: Click column headers to sort by Score, Max In/Out tokens, In/Out costs, and Total Cost
- **Persistent Selection**: Selected models remain visible even when filtered out by search
- **Cost Display**: Shows "N/A" instead of $0.00 for models without pricing data
- **Reduced Decimal Places**: Total costs display with 2 decimal places instead of 4

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Data Processing Pipeline
The core architecture centers around a Python-based ETL pipeline (`update_leaderboard.py`) that:
- **Data Extraction**: Scrapes HTML from OpenLM.ai using BeautifulSoup to parse the sortable leaderboard table
- **Data Enrichment**: Fetches pricing data from OpenRouter and LiteLLM APIs, then normalizes model names for matching
- **Data Output**: Generates both CSV files for programmatic use and markdown for human-readable previews

## Automation Strategy
Uses GitHub Actions for daily automated updates with a push-based deployment model:
- **Schedule**: Daily cron job triggers the update script
- **Persistence**: Commits generated CSV directly to the repository for easy consumption
- **Distribution**: Leverages GitHub's CDN for fast, reliable data access

## Frontend Architecture
Static HTML/CSS/JavaScript web interface that:
- **Data Source**: Fetches CSV directly from GitHub's raw content URL
- **Client-Side Processing**: All filtering, searching, and cost calculations happen in browser JavaScript
- **User Experience**: Provides search, filtering, model comparison, and cost calculation tools

## File Structure Design
- **Single Responsibility**: Each file has a clear, focused purpose
- **Minimal Dependencies**: Uses only essential Python packages (pandas, requests, beautifulsoup4, tabulate)
- **Output Separation**: Distinguishes between machine-readable (CSV) and human-readable (markdown) formats

# External Dependencies

## Data Sources
- **OpenLM.ai Chatbot Arena+**: Primary source for model rankings and benchmark scores via HTML scraping
- **OpenRouter API**: Model pricing data for cost calculations
- **LiteLLM**: Additional pricing and provider information

## Infrastructure Services
- **GitHub Actions**: Automated daily updates and CI/CD pipeline
- **GitHub Pages**: Static site hosting for the web interface
- **GitHub Raw Content**: CDN for serving CSV data to the web interface

## Python Libraries
- **pandas**: Data manipulation and CSV generation
- **requests**: HTTP client for API calls and web scraping
- **beautifulsoup4**: HTML parsing for leaderboard extraction
- **tabulate**: Formatted table output for markdown generation
- **gradio_client**: Additional model information retrieval

## Web Technologies
- **Vanilla JavaScript**: Client-side data processing and UI interactions
- **Chart.js**: Interactive data visualization library for scatter plot charts
- **CSS3**: Modern styling with gradients and responsive design
- **HTML5**: Static web interface structure