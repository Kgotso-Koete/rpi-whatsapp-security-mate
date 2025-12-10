# app/__init__.py
from flask import Flask
import logging

def create_app():
    """Application factory function"""
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = 'your-secret-key-change-this'
    
    # Register blueprints
    from app.blueprints.slack.routes import slack_bp
    from app.blueprints.web.routes import web_bp
    from app.blueprints.whatsapp.routes import whatsapp_bp
    
    app.register_blueprint(slack_bp, url_prefix='/rpi-security-cam/slack')
    app.register_blueprint(web_bp, url_prefix='/rpi-security-cam/web')
    app.register_blueprint(whatsapp_bp, url_prefix='/rpi-security-cam/whatsapp')
    
    # Root endpoint
    @app.route('/rpi-security-cam/')
    def index():
        return "Security System API - Use /slack, /web, or /whatsapp endpoints"
    
    return app
