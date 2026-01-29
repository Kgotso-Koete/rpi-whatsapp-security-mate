"""
Flask application initialization with blueprints

This module initializes the Flask app, loads configuration from YAML files,
and registers the blueprints for Slack, Web, and WhatsApp integrations.
"""
import logging
import logging.config
import os
from flask import Flask

# Create Flask application
application = Flask(__name__)

# Initialize logging first
from app import config as app_config

try:
    app_config.init_logging()
except Exception as e:
    # Fallback to basic logging if logging.yml has issues
    logging.basicConfig(level=logging.INFO)
    logging.warning(f"Could not initialize logging from config: {e}")

LOGGER = logging.getLogger(__name__)

# Load main configuration (config.yml)
try:
    main_config = app_config.load_config()
    application.config.update(main_config)
    LOGGER.info(f"Loaded main config keys: {list(main_config.keys())}")
except Exception as e:
    LOGGER.error(f"Failed to load config.yml: {e}")

# Load private configuration (private.yml)
try:
    private_config = app_config.load_private_config()
    application.config.update(private_config)
    LOGGER.info(f"Loaded private config keys: {list(private_config.keys())}")
    
    # Validate WhatsApp config is present
    if 'whatsapp' in private_config:
        wa_keys = list(private_config['whatsapp'].keys())
        LOGGER.info(f"WhatsApp config loaded with keys: {wa_keys}")
    else:
        LOGGER.warning("No 'whatsapp' section found in private.yml")
        
except FileNotFoundError:
    LOGGER.error(
        "private.yml not found! Copy app/config/private-example.yml to "
        "app/config/private.yml and fill in your credentials."
    )
except Exception as e:
    LOGGER.error(f"Failed to load private.yml: {e}")

# Import and register blueprints
from app.slack import slack_bp
from app.web import web_bp
from app.whatsapp import whatsapp_bp

application.register_blueprint(slack_bp, url_prefix='/rpi-security-cam/slack')
application.register_blueprint(web_bp, url_prefix='/rpi-security-cam/web')
application.register_blueprint(whatsapp_bp, url_prefix='/rpi-security-cam/whatsapp')

LOGGER.info("Registered blueprints: slack, web, whatsapp")

# Import legacy routes
try:
    from app import views_legacy
except ImportError as e:
    LOGGER.warning(f"Could not import views_legacy: {e}")


# Root endpoint
@application.route('/rpi-security-cam/')
def index():
    """Health check endpoint"""
    return "Security System API - Use /slack, /web, or /whatsapp endpoints"


@application.route('/rpi-security-cam/debug/config')
def debug_config():
    """Debug endpoint to check config loading (remove in production)"""
    whatsapp_config = application.config.get('whatsapp', {})
    return {
        "whatsapp_config_loaded": bool(whatsapp_config),
        "whatsapp_keys": list(whatsapp_config.keys()) if whatsapp_config else [],
        "verify_token_set": bool(whatsapp_config.get('verify_token')),
        "phone_number_id_set": bool(whatsapp_config.get('phone_number_id')),
        "access_token_set": bool(whatsapp_config.get('access_token')),
    }