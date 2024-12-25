from flask import render_template
from app.dashboard import bp

@bp.route('/dashboard')
def dashboard():
    return render_template('dashboard/dashboard.html')