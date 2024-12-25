from flask import render_template
from app.scrape import bp

@bp.route('/scrape')
def scrape():
    return render_template('scrape/scrape.html')

@bp.route('/scrape_form', methods=['GET'])
def scrape_form():
    url = request.args.get('url', '')  # Get URL from query parameters
    return render_template('scrape/scrape.html', url=url)