import os
import openai
from dotenv import load_dotenv
from flask import render_template, request, jsonify

# Load environment variables from .env file
load_dotenv()

# Check for Ollama configuration first
OLLAMA_API_KEY = os.getenv('OLLAMA_API_KEY')
OLLAMA_API_URL = os.getenv('OLLAMA_API_URL')

if OLLAMA_API_KEY and OLLAMA_API_URL:
    # Use Ollama configuration
    USE_OLLAMA = True
    openai.api_key = os.getenv('OLLAMA_API_KEY')
    openai.api_base = os.getenv('OLLAMA_API_URL')
else:
    # Fall back to OpenAI
    USE_OLLAMA = False
    openai.api_key = os.getenv('OPENAI_API_KEY')
    if not openai.api_key:
        raise ValueError("No OpenAI API key found. Please set OPENAI_API_KEY in your .env file.")
