from flask import Blueprint

extract_bp = Blueprint('extract', __name__, template_folder='templates')

from app.extract import routes 
