from flask import Blueprint

bp = Blueprint('extract', __name__, template_folder='templates')

from app.extract import routes 