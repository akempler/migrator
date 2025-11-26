# Migrator

## Overview

Migrator is a Flask-based web application designed to streamline the process of extracting semi-structured data from HTML tables on web pages and converting them into structured formats suitable for Drupal 11 content migration or CSV export.

### Key Features

- **Advanced Web Scraping**: Leverages Selenium with undetected ChromeDriver to scrape web pages, including those protected by Cloudflare and other anti-bot measures
- **Intelligent Table Detection**: Automatically discovers and parses all HTML tables on a scraped webpage
- **Interactive Table Preview**: Displays extracted tables with Bootstrap styling for easy review and selection
- **AI-Powered Schema Generation**: Uses OpenAI GPT-4 to automatically generate Drupal 11 content type schemas based on table structure and data patterns
- **Smart Data Extraction**: Employs OpenAI GPT-4o to extract and format table data as JSON according to the generated schema
- **CSV Export**: Enables quick download of extracted table data as CSV files
- **Flexible AI Backend**: Supports both OpenAI API and local Ollama installations for LLM processing

### Typical Workflow

1. **Scrape**: Enter a URL to scrape a webpage
2. **Detect**: Application automatically finds all tables on the page
3. **Select**: Choose the table you want to work with
4. **Generate Schema**: AI generates a Drupal 11 content type schema from the table structure
5. **Extract**: Convert the table data to JSON format or download as CSV

### Technology Stack

- **Backend**: Flask (Python web framework)
- **Parsing**: BeautifulSoup4, lxml
- **Web Scraping**: Selenium, undetected-chromedriver
- **Data Processing**: Pandas
- **AI/ML**: OpenAI API (GPT-4/GPT-4o) or Ollama (local LLM)

NOTE: This is a work in progress and not all functionality is fully implemented yet. 


## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up OpenAI API key in a `.env` file:

```bash
OPENAI_API_KEY=<your-openai-api-key>
```
Or to use ollama locally:
```bash
OLLAMA_API_KEY=<your-ollama-api-key>
OLLAMA_API_URL=<your-ollama-api-url>
```

3. Run the app:

```bash
python run.py
```
