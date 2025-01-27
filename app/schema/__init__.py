from flask import Blueprint

schema_bp = Blueprint('schema', __name__, template_folder='templates')

from app.schema import routes 
