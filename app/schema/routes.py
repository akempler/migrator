from flask import render_template, request, jsonify, session, redirect, url_for
from app.schema import bp
import pandas as pd
from bs4 import BeautifulSoup
import time
import lxml
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import openai
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set your OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    raise ValueError("No OpenAI API key found. Please set OPENAI_API_KEY in your .env file.")


def generate_schema_from_table(table_html):
    try:
        # Parse the table HTML and extract text content
        soup = BeautifulSoup(table_html, 'lxml')
        
        # Debug print to see what we're working with
        #print(f"Raw table HTML received: {table_html[:500]}")
        
        # Extract headers and data from the table
        headers = []
        data = []
        
        # Try multiple methods to find headers
        # First try finding th elements
        header_cells = soup.find_all('th')
        if header_cells:
            headers = [th.get_text(strip=True) for th in header_cells]
        else:
            # If no th elements, try the first row
            first_row = soup.find('tr')
            if first_row:
                headers = [td.get_text(strip=True) for td in first_row.find_all('td')]
        
        # Get data rows
        rows = soup.find_all('tr')
        for row in rows[1:]:  # Skip the first row as it's headers
            cells = row.find_all('td')
            if cells:
                row_data = []
                for cell in cells:
                    # Get all text content, including from nested elements
                    text_content = ' '.join(cell.stripped_strings)
                    row_data.append(text_content)
                if row_data:
                    data.append(row_data)
        
        print(f"Extracted headers: {headers}")
        print(f"Sample data rows: {data[:2]}")
        
        # Create a structured representation of the table
        table_structure = {
            "content_type_name": "table_content",
            "fields": []
        }
        
        # Create field definitions based on headers and data
        for i, header in enumerate(headers):
            field = {
                "field_name": header.lower().replace(' ', '_'),
                "field_label": header,
                "field_type": "string",  # Default type
                "required": True,
                "sample_values": [row[i] for row in data[:3] if i < len(row)]
            }
            
            # Try to determine field type from sample data
            sample_values = field["sample_values"]
            if sample_values:
                if all(val.isdigit() for val in sample_values):
                    field["field_type"] = "integer"
                elif all(val.replace('.', '').isdigit() for val in sample_values):
                    field["field_type"] = "decimal"
                elif all(len(val) > 100 for val in sample_values):
                    field["field_type"] = "text_long"
                elif any('<a href' in val.lower() for val in sample_values):
                    field["field_type"] = "link"
            
            table_structure["fields"].append(field)
        
        # Convert to JSON for the prompt
        table_json = json.dumps(table_structure, indent=2)
        
        # Clean and escape the HTML table string
        cleaned_table_html = table_html.replace('\n', ' ').replace('\r', '').strip()
        
        prompt = f"""Generate a Drupal 11 content type schema based on this HTML table:

        ```html
        {cleaned_table_html}
        ```

        Create a complete Drupal content type configuration that includes:
        1. Machine names for fields (lowercase with underscores)
        2. Appropriate field types (text, long text, integer, decimal, link, etc.)
        3. Required field settings
        4. Field widget settings
        5. Display settings

        Return the schema as valid JSON that could be used for content type configuration.
        Include field descriptions based on the data patterns observed."""
        
        print(f"Sending prompt to OpenAI: {prompt[:500]}...")
        
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=2000
        )
        
        schema = response.choices[0].message.content
        print(f"Received response from OpenAI: {schema[:200]}...")
        
        # Validate and format JSON
        try:
            parsed_schema = json.loads(schema)
            return json.dumps(parsed_schema, indent=2)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', schema, re.DOTALL)
            if json_match:
                return json_match.group()
            raise ValueError("Response is not valid JSON")
        
    except Exception as e:
        print(f"Error in generate_schema_from_table: {str(e)}")
        return None


@bp.route('/generate_schema', methods=['GET', 'POST'])
def generate_schema():
    # Check if we have a table selected
    if not session.get('current_table'):
        return redirect(url_for('scrape.scrape_form'))
        
    try:
        if request.method == 'POST':
            table_html = request.form.get('table_html')
            if not table_html:
                return jsonify({"error": "No table HTML provided"}), 400
            
            # Debug the received HTML
            print("\n=== RECEIVED HTML ===")
            print(table_html)
            print("\n=== END RECEIVED HTML ===")
            
            # Clean and escape the HTML table string - use repr() to preserve all characters
            cleaned_table_html = repr(table_html)[1:-1]  # Remove the outer quotes from repr()
            
            prompt = f"""Generate a Drupal 11 content type schema based on this HTML table.
            Analyze this exact HTML table structure:

            {cleaned_table_html}

            Create a complete Drupal content type configuration that includes:
            1. Machine names for fields (lowercase with underscores)
            2. Appropriate field types (text, long text, integer, decimal, link, etc.)
            3. Required field settings
            4. Field widget settings
            5. Display settings

            Return the schema as valid JSON that could be used for content type configuration.
            Include field descriptions based on the data patterns observed."""
            
            # Debug the final prompt
            print("\n=== FINAL PROMPT ===")


            print(prompt)
            print("\n=== END FINAL PROMPT ===")
            
            schema = generate_schema_from_table(table_html)
            if not schema:
                print("Failed to generate schema")  # Debug print
                return render_template('schema/schema.html', 
                                     error="Failed to generate schema. Please try again.")
            
            # Try to pretty print the JSON if possible
            try:
                parsed_schema = json.loads(schema)
                pretty_schema = json.dumps(parsed_schema, indent=2)
            except:
                pretty_schema = schema
            
            if schema:
                session['current_schema'] = True
                
            return render_template('schema/schema.html', 
                                 schema=pretty_schema, 
                                 table_html=table_html)
        else:
            # GET request - only allow if we have a table
            return redirect(url_for('scrape.scrape_form'))
            
    except Exception as e:
        print(f"Error in generate_schema route: {str(e)}")
        return render_template('schema/schema.html', 
                             error=f"Error generating schema: {str(e)}")
