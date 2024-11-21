from flask import Flask, render_template, request
import pandas as pd
from bs4 import BeautifulSoup
import time
import lxml
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

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

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/scrape', methods=['GET'])
def scrape_form():
    return render_template('scrape.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form['url']
    driver = None
    try:
        driver = get_driver()
        
        # Set page load timeout
        driver.set_page_load_timeout(30)
        
        # Navigate to URL
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
        
        # Convert tables to DataFrames
        table_previews = {}
        for i, table in enumerate(tables):
            try:
                df = html_table_to_dataframe(table)
                if not df.empty:
                    preview_df = df.head()
                    table_previews[i] = preview_df.to_html(classes='table')
            except Exception as table_error:
                print(f"Error processing table {i}: {str(table_error)}")
                continue
        
        if not table_previews:
        # Wait for the actual page title to appear (indicating Cloudflare check is complete)
          max_attempts = 3
          current_attempt = 0
        
        while "Just a moment" in driver.title and current_attempt < max_attempts:
            time.sleep(5)
            current_attempt += 1
        
        # Get page source and verify content
        page_source = driver.page_source
        
        # Debug the raw page source
        source_preview = page_source[:1000]  # First 1000 characters
        content_length = len(page_source)
        
        # Create soup with both parsers to compare
        soup_lxml = BeautifulSoup(page_source, 'lxml')
        soup_html = BeautifulSoup(page_source, 'html.parser')
        
        # Debug information
        debug_info = [
            f"Content length: {content_length} characters",
            f"Source preview: {source_preview}",
            f"URL being accessed: {url}",
            f"Current page title: {driver.title}",
        ]
        
        # Try different methods to find tables
        direct_tables_lxml = soup_lxml.find_all('table')
        direct_tables_html = soup_html.find_all('table')
        
        debug_info.extend([
            f"Tables found with lxml: {len(direct_tables_lxml)}",
            f"Tables found with html.parser: {len(direct_tables_html)}",
        ])
        
        # Try to find any element to verify parsing is working
        all_elements_lxml = soup_lxml.find_all()
        all_elements_html = soup_html.find_all()
        
        debug_info.extend([
            f"Total elements found with lxml: {len(all_elements_lxml)}",
            f"Total elements found with html.parser: {len(all_elements_html)}",
        ])
        
        # Try explicit XPath with Selenium
        try:
            table_elements = driver.find_elements("xpath", "//table")
            debug_info.append(f"Tables found with Selenium XPath: {len(table_elements)}")
        except Exception as xpath_error:
            debug_info.append(f"XPath search error: {str(xpath_error)}")
        
        # Check if page is fully loaded
        ready_state = driver.execute_script("return document.readyState")
        debug_info.append(f"Page ready state: {ready_state}")
        
        # Try to get table directly with JavaScript
        table_count_js = driver.execute_script("return document.getElementsByTagName('table').length")
        debug_info.append(f"Tables found with JavaScript: {table_count_js}")
        
        # If we still haven't found any tables, return debug info
        if not direct_tables_lxml and not direct_tables_html:
            debug_str = "\n".join(debug_info)
            return render_template('scrape.html', 
                                     error=f"No tables found. Debug info:\n{debug_str}")
        
        # Use whichever parser found tables
        tables = direct_tables_lxml if direct_tables_lxml else direct_tables_html
        
        # Convert tables to DataFrames
        table_previews = {}
        for i, table in enumerate(tables):
            try:
                df = html_table_to_dataframe(table)
                if not df.empty:
                    preview_df = df.head()
                    table_previews[i] = preview_df.to_html(classes='table')
                    debug_info.append(f"Successfully processed table {i}")
            except Exception as table_error:
                debug_info.append(f"Error processing table {i}: {str(table_error)}")
                continue
        
        if not table_previews:
            debug_str = "\n".join(debug_info)
            return render_template('scrape.html', 
                                     error=f"Found tables but couldn't process them properly.\nDebug info:\n{debug_str}")
        
        return render_template('scrape.html', 
                                 tables=table_previews, 
                                 url=url)
                                 
    except Exception as e:
        return render_template('scrape.html', 
                                 error=f"Error scraping URL: {str(e)}")
    finally:
        if driver:
            driver.quit()
    
    return render_template('scrape.html')

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

if __name__ == '__main__':
    app.run(debug=True) 