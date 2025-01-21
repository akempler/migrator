from flask import Blueprint

bp = Blueprint('schema', __name__, template_folder='templates')

from app.schema import routes 