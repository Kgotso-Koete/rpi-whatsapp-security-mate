"""
WhatsApp Cloud API Service for Raspberry Pi Security System

This module provides a WhatsAppService class that:
- Handles incoming messages (text commands, button clicks, list selections)
- Sends alerts with image tagging buttons
- Provides a control menu mirroring Slack/Web functionality

Works both inside Flask context (webhooks) and standalone (security_system.py).
"""
import logging
import json
import os
import requests
import time

try:
    from flask import current_app, has_app_context
except ImportError:
    # Flask not available (running standalone)
    current_app = None
    has_app_context = lambda: False

try:
    from app.api import CameraController, SystemController
    from app import config
except ImportError:
    # Handle direct script execution
    import sys
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    from app.api import CameraController, SystemController
    from app import config

LOGGER = logging.getLogger(__name__)


class WhatsAppService:
    """
    Service to handle WhatsApp communication via the Cloud API.
    
    Provides:
    - Command processing (text, buttons, lists)
    - Alert sending with image tagging
    - System control (camera, notifications, rotation)
    
    Can be used:
    - Inside Flask (webhooks) - uses current_app.config
    - Standalone (security_system.py) - loads config from private.yml directly
    """
    
    def __init__(self, body=None):
        """
        Initialize WhatsApp service with config.
        
        Args:
            body: Optional incoming webhook body to initialize conversation
        """
        # Get config - try Flask first, fall back to loading directly
        whatsapp_config = self._load_config()
        
        self.access_token = whatsapp_config.get('access_token')
        self.phone_number_id = whatsapp_config.get('phone_number_id')
        self.version = whatsapp_config.get('version', 'v20.0')
        self.recipient_wa_id = whatsapp_config.get('recipient_wa_id')
        self.verify_token = whatsapp_config.get('verify_token')
        self.public_url = whatsapp_config.get('public_url', '')
        
        # Validate essential config
        if not self.access_token:
            LOGGER.warning("WhatsApp access_token not configured")
        if not self.phone_number_id:
            LOGGER.warning("WhatsApp phone_number_id not configured")
        if not self.recipient_wa_id:
            LOGGER.warning("WhatsApp recipient_wa_id not configured")
        
        # Build API URL
        self.base_url = f"https://graph.facebook.com/{self.version}/{self.phone_number_id}/messages"
        self.auth_header = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Conversation state
        self.body = body
        self.wa_id = None
        self.sender_name = None
        self.message_queue = []
        
        if body:
            self._init_conversation(body)
    
    def _load_config(self):
        """
        Load WhatsApp config from Flask or directly from private.yml
        
        Returns:
            dict: WhatsApp configuration
        """
        # Try Flask context first (when running inside webhook handlers)
        try:
            if has_app_context() and current_app:
                whatsapp_config = current_app.config.get('whatsapp', {})
                if whatsapp_config:
                    LOGGER.debug("Loaded WhatsApp config from Flask context")
                    return whatsapp_config
        except Exception as e:
            LOGGER.debug(f"Flask context not available: {e}")
        
        # Fall back to loading directly from private.yml
        try:
            private_config = config.load_private_config()
            whatsapp_config = private_config.get('whatsapp', {})
            LOGGER.debug("Loaded WhatsApp config from private.yml")
            return whatsapp_config
        except FileNotFoundError:
            LOGGER.error("private.yml not found - WhatsApp will not work")
            return {}
        except Exception as e:
            LOGGER.error(f"Failed to load WhatsApp config: {e}")
            return {}
    
    def _init_conversation(self, body):
        """Extract sender information from webhook body"""
        try:
            entry = body.get("entry", [{}])[0]
            change = entry.get("changes", [{}])[0]
            value = change.get("value", {})
            contacts = value.get("contacts", [])
            
            if contacts:
                self.wa_id = contacts[0].get("wa_id")
                self.sender_name = contacts[0].get("profile", {}).get("name", "there")
                LOGGER.info(f"Initialized conversation with {self.wa_id}")
        except Exception as e:
            LOGGER.error(f"Error initializing conversation: {e}")

    # ==========================================================================
    # MESSAGE PROCESSING
    # ==========================================================================
    
    def process_inbound_message(self, message):
        """Route incoming message to appropriate handler based on type"""
        msg_type = message.get("type")
        LOGGER.info(f"Processing message type: {msg_type}")
        
        if msg_type == "text":
            text = message.get("text", {}).get("body", "").strip().lower()
            self._handle_text(text)
        elif msg_type == "interactive":
            interactive = message.get("interactive", {})
            interactive_type = interactive.get("type")
            
            if interactive_type == "button_reply":
                button_id = interactive.get("button_reply", {}).get("id", "")
                self._handle_button(button_id)
            elif interactive_type == "list_reply":
                list_id = interactive.get("list_reply", {}).get("id", "")
                self._handle_list(list_id)
        else:
            LOGGER.debug(f"Unhandled message type: {msg_type}")
    
    def _handle_text(self, text):
        """Process text commands"""
        if text in ["menu", "hi", "hello", "help", "start"]:
            self.send_main_menu()
        elif text == "status":
            self._send_status()
        elif text == "image" or text == "img":
            self._send_latest_image()
        else:
            self.send_text("🤖 Type 'menu' to see available commands.")
    
    def _handle_button(self, button_id):
        """Process button clicks (image tagging)"""
        LOGGER.info(f"Button clicked: {button_id}")
        
        # Format: tag_occupied:timestamp_slug or tag_unoccupied:timestamp_slug
        if ":" in button_id:
            action, ts_slug = button_id.split(":", 1)
            if action == "tag_occupied":
                self._log_occupancy(True, ts_slug)
                self.send_text(f"✅ Marked *{ts_slug}* as *Occupied*")
            elif action == "tag_unoccupied":
                self._log_occupancy(False, ts_slug)
                self.send_text(f"🔲 Marked *{ts_slug}* as *Unoccupied*")
        else:
            # Legacy format without timestamp
            if button_id == "tag_occupied":
                self._log_occupancy(True)
                self.send_text("✅ Marked as *Occupied*")
            elif button_id == "tag_unoccupied":
                self._log_occupancy(False)
                self.send_text("🔲 Marked as *Unoccupied*")
    
    def _handle_list(self, list_id):
        """Process menu list selections"""
        LOGGER.info(f"List selected: {list_id}")
        
        handlers = {
            "cmd_status": self._send_status,
            "cmd_image": self._send_latest_image,
            "cmd_camera_toggle": self._toggle_camera,
            "cmd_notify_toggle": self._toggle_notifications,
            "cmd_rotate": self._send_rotation_menu,
            "main_menu": self.send_main_menu,
            # Rotation commands
            "rot_center": lambda: self._rotate("center"),
            "rot_left": lambda: self._rotate("left"),
            "rot_right": lambda: self._rotate("right"),
            "rot_up": lambda: self._rotate("up"),
            "rot_down": lambda: self._rotate("down"),
        }
        
        handler = handlers.get(list_id)
        if handler:
            handler()
        else:
            self.send_text(f"Unknown command: {list_id}")

    # ==========================================================================
    # SYSTEM ACTIONS
    # ==========================================================================
    
    def _send_status(self):
        """Get and send system status"""
        try:
            res = CameraController.get_status()
            if res.get('success'):
                d = res['data']
                msg = (
                    f"📊 *System Status*\n\n"
                    f"🌡️ Temperature: {d.get('temperature', 'N/A')}°C\n"
                    f"📹 Camera: {'✅ ON' if d.get('camera_on') else '💤 OFF'}\n"
                    f"🔔 Alerts: {'✅ ON' if d.get('notifications_on') else '🔕 OFF'}\n"
                    f"📍 Position: Pan {d.get('pan', 0)}°, Tilt {d.get('tilt', 0)}°"
                )
                self.send_text(msg)
            else:
                self.send_text(f"❌ Error: {res.get('error', 'Unknown error')}")
        except Exception as e:
            LOGGER.error(f"Error getting status: {e}")
            self.send_text("❌ Failed to get system status")
    
    def _send_latest_image(self):
        """Send the most recent captured image"""
        if self.public_url:
            img_url = f"{self.public_url}/rpi-security-cam/web/api/image/latest"
            self.send_alert(img_url, "Latest capture")
        else:
            self.send_text("⚠️ Image serving not configured (missing public_url)")
    
    def _toggle_camera(self):
        """Toggle camera on/off"""
        try:
            status = CameraController.get_status()
            if status.get('success'):
                if status['data'].get('camera_on'):
                    res = CameraController.turn_off()
                else:
                    res = CameraController.turn_on()
                self.send_text(f"📹 {res.get('message', 'Done')}")
            else:
                self.send_text("❌ Could not get camera status")
        except Exception as e:
            LOGGER.error(f"Error toggling camera: {e}")
            self.send_text("❌ Failed to toggle camera")
    
    def _toggle_notifications(self):
        """Toggle notification alerts on/off"""
        try:
            status = CameraController.get_status()
            if status.get('success'):
                enable = not status['data'].get('notifications_on')
                res = CameraController.toggle_notifications(enable)
                state = "enabled" if enable else "disabled"
                self.send_text(f"🔔 Notifications {state}")
            else:
                self.send_text("❌ Could not get notification status")
        except Exception as e:
            LOGGER.error(f"Error toggling notifications: {e}")
            self.send_text("❌ Failed to toggle notifications")
    
    def _rotate(self, direction):
        """Rotate camera in specified direction"""
        try:
            if direction == "center":
                res = CameraController.rotate(40, 10)
            else:
                pos = CameraController.get_position()
                if not pos.get('success'):
                    self.send_text("❌ Could not get current position")
                    return
                
                pan, tilt = pos['data']['pan'], pos['data']['tilt']
                moves = {
                    "left": (20, 0),
                    "right": (-20, 0),
                    "up": (0, 10),
                    "down": (0, -10),
                }
                dp, dt = moves.get(direction, (0, 0))
                res = CameraController.rotate(pan + dp, tilt + dt)
            
            if res.get('success'):
                self.send_text(f"🔄 Moved {direction}")
            else:
                self.send_text(f"❌ {res.get('message', 'Move failed')}")
        except Exception as e:
            LOGGER.error(f"Error rotating: {e}")
            self.send_text("❌ Failed to rotate camera")
    
    def _log_occupancy(self, occupied, ts_slug=None):
        """Log occupancy tag for training data"""
        try:
            if not ts_slug:
                res = CameraController.get_latest_image()
                if res.get('success'):
                    ts_slug = res['data']['filename'].replace('.jpg', '')
                else:
                    ts_slug = "unknown"
            
            tag = "occupied" if occupied else "unoccupied"
            filename = f"{tag}_{ts_slug}.txt"
            filepath = os.path.join(config.TRAIN_DIR, filename)
            
            with open(filepath, 'w') as f:
                f.write(f"tagged_at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            LOGGER.info(f"Logged occupancy: {filename}")
        except Exception as e:
            LOGGER.error(f"Failed to log occupancy: {e}")

    # ==========================================================================
    # MESSAGE SENDING
    # ==========================================================================
    
    def send_message(self, data):
        """Queue a message for sending"""
        self.message_queue.append(data)
        return {"status": "queued"}
    
    def flush_messages(self):
        """Send all queued messages to WhatsApp API"""
        if not self.access_token or not self.phone_number_id:
            LOGGER.error("Cannot send messages - WhatsApp not configured (missing access_token or phone_number_id)")
            return 0
        
        sent = 0
        for data in self.message_queue:
            try:
                LOGGER.info(f"Sending message to WhatsApp API: {self.base_url}")
                response = requests.post(
                    self.base_url,
                    headers=self.auth_header,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    sent += 1
                    LOGGER.info(f"Message sent successfully")
                else:
                    LOGGER.error(f"WhatsApp API error: {response.status_code} - {response.text}")
                
                time.sleep(0.3)  # Rate limit protection
            except requests.RequestException as e:
                LOGGER.error(f"Failed to send message: {e}")
        
        self.message_queue = []
        return sent
    
    def send_text(self, text, recipient=None):
        """Send a simple text message"""
        recipient = recipient or self.wa_id or self.recipient_wa_id
        if not recipient:
            LOGGER.error("No recipient specified for text message")
            return
        
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"body": text}
        }
        return self.send_message(data)
    
    def send_alert(self, image_url, caption, recipient=None):
        """Send an image alert with tagging buttons"""
        recipient = recipient or self.wa_id or self.recipient_wa_id
        if not recipient:
            LOGGER.error("No recipient specified for alert")
            return
        
        # Extract timestamp slug from URL for button IDs
        ts_slug = image_url.split('/')[-1].replace('.jpg', '') if '/' in image_url else "latest"
        
        LOGGER.info(f"Queuing alert for {recipient}: {image_url}")
        
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "header": {
                    "type": "image",
                    "image": {"link": image_url}
                },
                "body": {"text": f"🚨 *Motion Detected!*\n{caption}\n\nTag this image:"},
                "footer": {"text": "Security Mate"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": f"tag_occupied:{ts_slug}", "title": "👤 Occupied"}},
                        {"type": "reply", "reply": {"id": f"tag_unoccupied:{ts_slug}", "title": "🔲 Empty"}}
                    ]
                }
            }
        }
        return self.send_message(data)
    
    def send_main_menu(self, recipient=None):
        """Send the main control menu"""
        recipient = recipient or self.wa_id or self.recipient_wa_id
        if not recipient:
            LOGGER.error("No recipient specified for menu")
            return
        
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": "🔐 Security Mate"},
                "body": {"text": "Control your security system:"},
                "footer": {"text": "Select an option"},
                "action": {
                    "button": "Menu",
                    "sections": [
                        {
                            "title": "Monitor",
                            "rows": [
                                {"id": "cmd_status", "title": "📊 Status", "description": "View system status"},
                                {"id": "cmd_image", "title": "🖼️ Latest Image", "description": "Get last capture"}
                            ]
                        },
                        {
                            "title": "Control",
                            "rows": [
                                {"id": "cmd_camera_toggle", "title": "📹 Camera", "description": "Toggle ON/OFF"},
                                {"id": "cmd_notify_toggle", "title": "🔔 Alerts", "description": "Toggle alerts"},
                                {"id": "cmd_rotate", "title": "🔄 Rotate", "description": "Move camera"}
                            ]
                        }
                    ]
                }
            }
        }
        return self.send_message(data)
    
    def _send_rotation_menu(self, recipient=None):
        """Send the rotation submenu"""
        recipient = recipient or self.wa_id or self.recipient_wa_id
        if not recipient:
            return
        
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": "🔄 Camera Rotation"},
                "body": {"text": "Select direction:"},
                "action": {
                    "button": "Move",
                    "sections": [
                        {
                            "title": "Directions",
                            "rows": [
                                {"id": "rot_center", "title": "📍 Center", "description": "Return to center"},
                                {"id": "rot_left", "title": "⬅️ Left", "description": "Pan left"},
                                {"id": "rot_right", "title": "➡️ Right", "description": "Pan right"},
                                {"id": "rot_up", "title": "⬆️ Up", "description": "Tilt up"},
                                {"id": "rot_down", "title": "⬇️ Down", "description": "Tilt down"},
                                {"id": "main_menu", "title": "🔙 Back", "description": "Main menu"}
                            ]
                        }
                    ]
                }
            }
        }
        return self.send_message(data)
