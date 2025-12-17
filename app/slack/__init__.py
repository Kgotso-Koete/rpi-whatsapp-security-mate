"""
Slack integration blueprint
Handles all Slack slash commands and interactive components
"""

from .routes import slack_bp

__all__ = ['slack_bp']