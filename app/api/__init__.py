"""
Shared API layer for the security system.
Provides common interfaces for Slack, Web UI, and future integrations (WhatsApp).
"""

from .camera_control import CameraController, SystemController

__all__ = ['CameraController', 'SystemController']