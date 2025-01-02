from flask import render_template, request, jsonify, session, redirect, url_for
from app.scrape import bp

@bp.route('/scrape_form', methods=['GET'])
def scrape_form():
    return render_template('scrape/scrape_form.html')

@bp.route('/scrape', methods=['POST'])
def scrape():
    url = request.args.get('url', '')  # Get URL from query parameters
    return render_template('scrape/scrape.html', url=url)