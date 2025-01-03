from flask import render_template, request, jsonify, session, redirect, url_for
from app.scrape import bp
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


@bp.route('/scrape_form', methods=['GET', 'POST'])
def scrape_form():
    return render_template('scrape/scrape_form.html')

@bp.route('/scrape', methods=['POST'])
def scrape():
    url = request.args.get('url', '')  # Get URL from query parameters
    return render_template('scrape/scrape.html', url=url)

@bp.route('/scrape_webpage', methods=['POST'])
def scrape_webpage():
    url = request.form['url']
    session['last_url'] = url

    load_dotenv()
    # # Set your OpenAI API key
    openai.api_key = os.getenv('OPENAI_API_KEY')
    if not openai.api_key:
        raise ValueError("No OpenAI API key found. Please set OPENAI_API_KEY in your .env file.")
    
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
            session['current_table'] = True
            session['current_schema'] = False  # Explicitly set schema to False
            session['original_tables'] = original_tables
        
        return render_template('scrape/scrape_webpage.html', 
                             tables=table_previews,
                             original_tables=original_tables,
                             url=url)
                                 
    except Exception as e:
        return render_template('scrape/scrape_webpage.html', 
                             error=f"Error scraping URL: {str(e)}")
    finally:
        if driver:
            driver.quit()

    # Scrape the webpage
    # return render_template('scrape/scrape_webpage.html', url=url)


@bp.route('/table_to_csv', methods=['POST'])
def table_to_csv():
    table_index = int(request.form['table_index'])
    table_html = request.form['table_html']
    
    try:
        # Parse the HTML string with BeautifulSoup first
        soup = BeautifulSoup(table_html, 'html.parser')
        selected_table = html_table_to_dataframe(soup)
        
        # Convert to CSV and send as download
        return selected_table.to_csv(index=False), {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename=table_{table_index}.csv'
        }
    except Exception as e:
        return render_template('scrape/scrape_webpage.html', 
                             error=f"Error extracting table: {str(e)}")


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
