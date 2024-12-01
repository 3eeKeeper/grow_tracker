from flask import Flask, send_from_directory
from config import Config
import os
from datetime import datetime
from app.webhook_routes import bp as webhook_bp, init_signal_service
from app.scheduler import init_scheduler
from app.extensions import db, login_manager, socketio
from flask_migrate import Migrate

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.debug = True
    
    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize scheduler
    init_scheduler(app)
    
    # Initialize Signal service
    init_signal_service(app)
    
    # Add route to serve uploaded files
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    # Register blueprints
    from app.auth import bp as auth_bp
    from app.main import bp as main_bp
    from app.plants import bp as plants_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(plants_bp)
    app.register_blueprint(webhook_bp)
    
    @app.context_processor
    def utility_processor():
        return {'now': datetime.utcnow()}
    
    return app

from app import models
