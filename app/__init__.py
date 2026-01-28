"""
Flask application initialization with blueprints
"""
from flask import Flask
import logging
import os

# 1. Define the Flask object at the top level
application = Flask(__name__)

# Configure logging
from app import config
config.init_logging()

# Load configuration into Flask application context
application.config.update(config.load_config())
try:
    application.config.update(config.load_private_config())
except Exception as e:
    logging.warning(f"Could not load private.yml: {e}")

from app.slack import slack_bp
from app.web import web_bp
from app.whatsapp import whatsapp_bp

application.register_blueprint(slack_bp, url_prefix='/rpi-security-cam/slack')
application.register_blueprint(web_bp, url_prefix='/rpi-security-cam/web')
application.register_blueprint(whatsapp_bp, url_prefix='/rpi-security-cam/whatsapp')

# Import legacy routes 
from app import views_legacy

# Root endpoint
@application.route('/rpi-security-cam/')
def index():
    return "Security System API - Use /slack, /web, or /whatsapp endpoints"