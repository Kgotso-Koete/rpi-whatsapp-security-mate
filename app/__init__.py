# app/application.py
from flask import Flask
from flask_cors import CORS
import logging

def create_app():
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = 'your-secret-key'
    CORS(app)
    
    # Register blueprints with URL prefixes
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