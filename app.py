from flask import Flask, render_template, request
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Headers specifically tuned for nycourts.gov
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Host': 'ww2.nycourts.gov',
    'Referer': 'https://ww2.nycourts.gov/',
    'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

app = Flask(__name__)
session = requests.Session()
session.headers.update(HEADERS)

@app.route('/')
def index():
    return render_template('scrape.html')

@app.route('/scrape', methods=['GET', 'POST'])
def scrape():
    if request.method == 'POST':
        url = request.form['url']
        try:
            # Disable SSL verification and add longer timeout
            response = session.get(url, verify=False, timeout=60)
            response.raise_for_status()
            
            # Parse HTML and find tables
            soup = BeautifulSoup(response.text, 'lxml')
            tables = pd.read_html(response.text)
            
            # Create preview of each table (first 5 rows)
            table_previews = {}
            for i, table in enumerate(tables):
                preview_df = table.head()
                table_previews[i] = preview_df.to_html(classes='table')
            
            return render_template('scrape.html', 
                                 tables=table_previews, 
                                 url=url)
                                 
        except Exception as e:
            return render_template('scrape.html', 
                                 error=f"Error scraping URL: {str(e)}")
    
    return render_template('scrape.html')

@app.route('/extract_table', methods=['POST'])
def extract_table():
    url = request.form['url']
    table_index = int(request.form['table_index'])
    
    try:
        # Disable SSL verification here as well
        response = session.get(url, verify=False, timeout=60)
        response.raise_for_status()
        tables = pd.read_html(response.text)
        selected_table = tables[table_index]
        
        # Convert to CSV and send as download
        return selected_table.to_csv(index=False), {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename=table_{table_index}.csv'
        }
    except Exception as e:
        return render_template('scrape.html', 
                             error=f"Error extracting table: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True) 