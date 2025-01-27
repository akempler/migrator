from flask import Flask
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # List of blueprint modules to register
    blueprint_modules = [
        ('app.main', 'main_bp', None),
        ('app.dashboard', 'dashboard_bp', '/dashboard'),
        ('app.scrape', 'scrape_bp', '/scrape'),
        ('app.schema', 'schema_bp', '/schema'),
        ('app.extract', 'extract_bp', '/extract')
    ]

    # Dynamically register blueprints
    for module_name, bp_name, url_prefix in blueprint_modules:
        module = __import__(module_name, fromlist=[bp_name])
        bp = getattr(module, bp_name)
        app.register_blueprint(bp, url_prefix=url_prefix)

    return app
