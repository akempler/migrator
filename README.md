# Migrator

This app helps extract semi-structured data from an html table. 
It allows you to select the table and the columns you want to extract. 
Once selected, it will display the data in a table for you to review.
You can then save the data to a csv file.

NOTE: this is a work in progress and not all functionality is available yet. 


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
python app.py
```
