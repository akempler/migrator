from flask import Blueprint

bp = Blueprint('scrape', __name__, template_folder='templates')

from app.scrape import routes 