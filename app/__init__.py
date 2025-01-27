from flask import Flask
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

    from app.scrape import bp as scrape_bp
    app.register_blueprint(scrape_bp, url_prefix='/scrape')
    
    from app.schema import bp as schema_bp
    app.register_blueprint(schema_bp, url_prefix='/schema')
    
    from app.extract import bp as extract_bp
    app.register_blueprint(extract_bp, url_prefix='/extract')

    return app 