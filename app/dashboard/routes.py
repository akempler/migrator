from flask import render_template
from app.dashboard import dashboard_bp

@dashboard_bp.route('/dashboard')
def dashboard():
    return render_template('dashboard/dashboard.html')