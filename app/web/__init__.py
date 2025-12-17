"""
Web UI blueprint
Provides web interface for camera control and monitoring
"""

from .routes import web_bp
from .api import register_api_routes

# Register API routes on the blueprint
register_api_routes(web_bp)

__all__ = ['web_bp']