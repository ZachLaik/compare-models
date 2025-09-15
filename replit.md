# Overview

Compare Models is a daily-updated leaderboard system that aggregates LLM performance data from the Chatbot Arena with pricing information from multiple sources. The application automatically scrapes model rankings from OpenLM.ai's Chatbot Arena+ leaderboard, fetches pricing data from OpenRouter and LiteLLM, and produces a unified CSV dataset. It includes a web interface for searching models, calculating costs, and comparing quality-to-price ratios. The system runs automated daily updates via GitHub Actions to maintain current data.

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
- **CSS3**: Modern styling with gradients and responsive design
- **HTML5**: Static web interface structure