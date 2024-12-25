from flask import Flask
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    # from app.migration import bp as migration_bp
    # app.register_blueprint(migration_bp, url_prefix='/migration')

    return app 