from flask import Flask, render_template, request, jsonify, session, redirect, url_for
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

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Set your OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    raise ValueError("No OpenAI API key found. Please set OPENAI_API_KEY in your .env file.")

app.secret_key = 'your-secret-key-here'  # Replace with a secure secret key

def get_driver():
    try:
        options = uc.ChromeOptions()
        options.add_argument('--headless=new')  # Updated headless argument
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Create driver with version 131 to match your Chrome version
        driver = uc.Chrome(
            options=options,
            version_main=131,  # Updated to match your Chrome version
            driver_executable_path=None,
            browser_executable_path=None,
        )
        return driver
    except Exception as e:
        print(f"Error creating driver: {str(e)}")
        raise

def html_table_to_dataframe(table):
    # Extract headers
    headers = []
    
    # Try to find headers in thead first
    thead = table.find('thead')
    if thead:
        header_row = thead.find('tr')
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
    
    # If no headers found in thead, look in first row
    if not headers:
        first_row = table.find('tr')
        if first_row:
            headers = [cell.get_text(strip=True) for cell in first_row.find_all(['th', 'td'])]
    
    # If still no headers, generate column names
    if not headers:
        # Find the row with maximum columns to determine number of columns
        max_cols = 0
        for row in table.find_all('tr'):
            cols = len(row.find_all(['td', 'th']))
            max_cols = max(max_cols, cols)
        headers = [f'Column {i+1}' for i in range(max_cols)]
    
    # Extract rows from tbody if it exists, otherwise from table
    tbody = table.find('tbody')
    rows_container = tbody if tbody else table
    
    rows = []
    for tr in rows_container.find_all('tr'):
        # Skip header row if we're processing the whole table
        if not tbody and tr == table.find('tr') and headers == [cell.get_text(strip=True) for cell in tr.find_all(['th', 'td'])]:
            continue
            
        row = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
        if row and len(row) == len(headers):  # Only append rows that match header length
            rows.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(rows, columns=headers)
    return df

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

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/scrape', methods=['GET'])
def scrape_form():
    url = request.args.get('url', '')  # Get URL from query parameters
    return render_template('scrape.html', url=url)

@app.route('/scrape', methods=['POST'])
def scrape():
    # Clear previous session data when starting a new scrape
    session.clear()
    
    url = request.form['url']
    # Store URL in session for potential re-use
    session['last_url'] = url
    
    driver = None
    try:
        driver = get_driver()
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Get page source after JavaScript execution
        page_source = driver.execute_script("return document.documentElement.outerHTML")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(page_source, 'lxml')
        
        # Find all tables
        tables = soup.find_all('table')
        
        if not tables:
            return render_template('scrape.html', 
                                 error="No tables found on the page")
        
        # Store original table HTML and create previews
        original_tables = {}
        table_previews = {}
        
        for i, table in enumerate(tables):
            try:
                # Store original HTML
                original_tables[i] = str(table)
                
                # Create preview with Bootstrap table classes
                df = html_table_to_dataframe(table)
                if not df.empty:
                    table_previews[i] = df.to_html(
                        classes='table table-striped table-bordered',
                        index=False,
                        escape=False
                    )
            except Exception as table_error:
                print(f"Error processing table {i}: {str(table_error)}")
                continue
        
        if not table_previews:
            return render_template('scrape.html', 
                                 error="Found tables but couldn't process them properly.")
        
        if table_previews:
            session['current_table'] = True  # Changed from has_table
            session['current_schema'] = False  # Explicitly set schema to False
        
        return render_template('scrape.html', 
                             tables=table_previews,
                             original_tables=original_tables,
                             url=url)
                                 
    except Exception as e:
        return render_template('scrape.html', 
                             error=f"Error scraping URL: {str(e)}")
    finally:
        if driver:
            driver.quit()

@app.route('/extract_table', methods=['POST'])
def extract_table():
    url = request.form['url']
    table_index = int(request.form['table_index'])
    driver = None
    
    try:
        driver = get_driver()
        driver.get(url)
        time.sleep(3)
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        tables = soup.find_all('table')
        
        if not tables or table_index >= len(tables):
            raise ValueError("Table not found")
            
        selected_table = html_table_to_dataframe(tables[table_index])
        
        # Convert to CSV and send as download
        return selected_table.to_csv(index=False), {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename=table_{table_index}.csv'
        }
    except Exception as e:
        return render_template('scrape.html', 
                             error=f"Error extracting table: {str(e)}")
    finally:
        if driver:
            driver.quit()

@app.route('/generate_schema', methods=['GET', 'POST'])
def generate_schema():
    # Check if we have a table selected
    if not session.get('current_table'):
        return redirect(url_for('scrape_form'))
        
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
                return render_template('scrape.html', 
                                     error="Failed to generate schema. Please try again.")
            
            # Try to pretty print the JSON if possible
            try:
                parsed_schema = json.loads(schema)
                pretty_schema = json.dumps(parsed_schema, indent=2)
            except:
                pretty_schema = schema
            
            if schema:
                session['current_schema'] = True
                
            return render_template('schema.html', 
                                 schema=pretty_schema, 
                                 table_html=table_html)
        else:
            # GET request - only allow if we have a table
            return redirect(url_for('scrape_form'))
            
    except Exception as e:
        print(f"Error in generate_schema route: {str(e)}")
        return render_template('scrape.html', 
                             error=f"Error generating schema: {str(e)}")

@app.route('/extract_content', methods=['POST'])
def extract_content():
    try:
        schema = request.form.get('schema')
        table_html = request.form.get('table_html')
        
        if not schema or not table_html:
            return jsonify({"error": "Missing schema or table HTML"}), 400
            
        prompt = f"""Based on the following Schema and html table, 
extract ALL content from the table and convert it to json. 
Do not truncate or summarize the data - include every row from the table.
Return the complete dataset as valid JSON that matches the schema structure.

Schema:
{schema}

HTML Table:
{table_html}

Important: Return the complete JSON for all rows. Do not use ellipsis (...) or truncate the data."""
        
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=12000  # Increased max_tokens
        )
        
        content = response.choices[0].message.content
        
        # Try to parse and format the JSON
        try:
            # Remove any explanatory text before or after the JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', content)
            if json_match:
                content = json_match.group()
            
            parsed_content = json.loads(content)
            pretty_content = json.dumps(parsed_content, indent=2)
        except json.JSONDecodeError:
            pretty_content = content
            
        return render_template('content.html', content=pretty_content)
        
    except Exception as e:
        print(f"Error in extract_content route: {str(e)}")
        return jsonify({"error": f"Error extracting content: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True) 