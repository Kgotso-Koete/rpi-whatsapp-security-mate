import logging
import json
import os
import requests
import time
from flask import current_app, jsonify
from app.api import CameraController, SystemController
from app import utils, config

LOGGER = logging.getLogger(__name__)

class WhatsAppService:
    """
    Service to handle WhatsApp communication for the Cloud API.
    Tailored for the Raspberry Pi Security System.
    """
    def __init__(self, body=None):
        conf = current_app.config.get('whatsapp', {})
        self.access_token = conf.get('access_token')
        self.phone_number_id = conf.get('phone_number_id')
        self.version = conf.get('version', 'v20.0')
        self.recipient_wa_id = conf.get('recipient_wa_id')
        self.verify_token = conf.get('verify_token')
        
        self.base_url = f"https://graph.facebook.com/{self.version}/{self.phone_number_id}/messages"
        self.auth_header = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        self.body = body
        self.wa_id = None
        self.formatter = None
        self.message_queue = []
        
        if body:
            self.initialise_conversation(body)

    def initialise_conversation(self, body):
        """Extract sender information from the incoming webhook body"""
        try:
            entry = body.get("entry", [{}])[0]
            change = entry.get("changes", [{}])[0]
            value = change.get("value", {})
            messages = value.get("messages", [{}])
            contacts = value.get("contacts", [{}])
            
            if messages and contacts:
                self.wa_id = contacts[0].get("wa_id")
                self.formatter = WhatsMessageFormatter(self.wa_id)
        except Exception as e:
            LOGGER.error(f"Error initializing conversation: {e}")

    def process_inbound_message(self, message):
        """Process incoming WhatsApp message based on its type"""
        msg_type = message.get("type")
        
        if msg_type == "text":
            text = message["text"]["body"].strip().lower()
            self.handle_text_command(text)
        elif msg_type == "interactive":
            interactive = message["interactive"]
            if interactive["type"] == "button_reply":
                self.handle_button_reply(interactive["button_reply"]["id"])
            elif interactive["type"] == "list_reply":
                self.handle_list_reply(interactive["list_reply"]["id"])

    def handle_text_command(self, text):
        """Process incoming text messages as commands"""
        if text in ["menu", "hi", "hello", "help"]:
            self.send_main_menu(self.wa_id)
        elif text == "status":
            self.send_status_report(self.wa_id)
        else:
            self.send_text("🤖 Unrecognized command. Type 'menu' for options.", self.wa_id)

    def handle_button_reply(self, button_id):
        """Process button clicks (e.g., tagging an alert image)"""
        if button_id == "tag_occupied":
            self.log_occupancy(True)
            self.send_text("✅ Tagged as *Occupied*. Thank you!", self.wa_id)
        elif button_id == "tag_unoccupied":
            self.log_occupancy(False)
            self.send_text("🔳 Tagged as *Unoccupied*. Thank you!", self.wa_id)

    def handle_list_reply(self, list_id):
        """Process menu selections from list messages"""
        if list_id == "cmd_status":
            self.send_status_report(self.wa_id)
        elif list_id == "cmd_last_img":
            self.send_latest_image_alert(self.wa_id)
        elif list_id == "cmd_cam_toggle":
            res = self.toggle_camera()
            self.send_text(f"📹 {res['message']}", self.wa_id)
        elif list_id == "cmd_notify_toggle":
            res = self.toggle_notifications()
            self.send_text(f"🔔 {res['message']}", self.wa_id)
        elif list_id == "menu_rotate":
            self.send_rotation_menu(self.wa_id)
        elif list_id.startswith("rot_"):
            res = self.handle_rotation(list_id)
            self.send_text(f"🔄 {res['message']}", self.wa_id)
        elif list_id == "main_menu":
            self.send_main_menu(self.wa_id)

    def send_status_report(self, wa_id):
        """Fetch system status and format as a WhatsApp message"""
        res = CameraController.get_status()
        if res['success']:
            d = res['data']
            msg = f"""📊 *System Status*:
🌡️ Temp: {d['temperature']}°C
📹 Camera: {'✅ ON' if d['camera_on'] else '💤 OFF'}
🔔 Alerts: {'✅ ON' if d['notifications_on'] else '🔕 OFF'}
🤖 Auto-Detect: {'✅ ON' if d['auto_detect_on'] else '👤 OFF'}
📍 Position: Pan {d['pan']}°, Tilt {d['tilt']}°"""
            self.send_text(msg, wa_id)
        else:
            self.send_text(f"❌ Error getting status: {res.get('error')}", wa_id)

    def send_latest_image_alert(self, wa_id):
        """Send the latest captured image to WhatsApp"""
        conf = current_app.config.get('whatsapp', {})
        domain = conf.get('public_url', 'http://your-public-url')
        img_url = f"{domain}/rpi-security-cam/web/api/image/latest"
        self.send_alert(img_url, "Requested Latest Image", wa_id)

    def toggle_camera(self):
        """Toggle camera ON/OFF state"""
        status = CameraController.get_status()
        if status['success'] and status['data']['camera_on']:
            return CameraController.turn_off()
        else:
            return CameraController.turn_on()

    def toggle_notifications(self):
        """Toggle notification ON/OFF state"""
        status = CameraController.get_status()
        if status['success']:
            enable = not status['data']['notifications_on']
            return CameraController.toggle_notifications(enable)
        return {'success': False, 'message': 'Failed to toggle'}

    def handle_rotation(self, rot_cmd):
        """Handle camera rotation commands"""
        if rot_cmd == "rot_center":
            return CameraController.rotate(40, 10)
        
        pos_res = CameraController.get_position()
        if not pos_res['success']:
            return pos_res
            
        pan, tilt = pos_res['data']['pan'], pos_res['data']['tilt']
        if rot_cmd == "rot_left": pan += 20
        elif rot_cmd == "rot_right": pan -= 20
        elif rot_cmd == "rot_up": tilt += 10
        elif rot_cmd == "rot_down": tilt -= 10
        
        return CameraController.rotate(pan, tilt)

    def log_occupancy(self, occupied):
        """Log occupancy tags to files for potential training"""
        res = CameraController.get_latest_image()
        if res['success']:
            filename = f"{occupied}_{res['data']['filename'].replace('.jpg', '')}.txt"
            filepath = os.path.join(config.TRAIN_DIR, filename)
            with open(filepath, 'w') as f:
                f.write('')

    def send_message(self, data):
        """Queue a message to be sent"""
        self.message_queue.append(data)
        return {"status": "queued"}

    def flush_messages(self):
        """Send all queued messages sequentially"""
        sent_count = 0
        for data in self.message_queue:
            try:
                response = requests.post(
                    self.base_url, 
                    headers=self.auth_header, 
                    json=data, 
                    timeout=30
                )
                response.raise_for_status()
                LOGGER.info(f"WhatsApp message sent: {response.json()}")
                sent_count += 1
                time.sleep(0.5) # Avoid rate limits
            except Exception as e:
                LOGGER.error(f"Failed to send WhatsApp message: {e}")
        
        self.message_queue = []
        return sent_count

    def send_text(self, text, recipient=None):
        recipient = recipient or self.recipient_wa_id
        formatter = WhatsMessageFormatter(recipient)
        data = formatter.format_text(text)
        return self.send_message(data)

    def send_alert(self, image_url, timestamp_str, recipient=None):
        recipient = recipient or self.recipient_wa_id
        formatter = WhatsMessageFormatter(recipient)
        data = formatter.format_image_alert(image_url, timestamp_str)
        return self.send_message(data)

    def send_main_menu(self, recipient=None):
        recipient = recipient or self.recipient_wa_id
        formatter = WhatsMessageFormatter(recipient)
        data = formatter.format_main_menu()
        return self.send_message(data)

    def send_rotation_menu(self, recipient=None):
        recipient = recipient or self.recipient_wa_id
        formatter = WhatsMessageFormatter(recipient)
        data = formatter.format_rotation_menu()
        return self.send_message(data)


class WhatsMessageFormatter:
    """Format JSON payloads for the WhatsApp Cloud API"""
    def __init__(self, wa_id):
        self.wa_id = wa_id

    def format_text(self, text):
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.wa_id,
            "type": "text",
            "text": {"body": text}
        }

    def format_image_alert(self, image_url, timestamp_str):
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.wa_id,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "header": {
                    "type": "image",
                    "image": {"link": image_url}
                },
                "body": {
                    "text": f"🚨 *Motion Detected!*\nTime: {timestamp_str}\n\nHow should this image be tagged?"
                },
                "footer": {"text": "Security Mate"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "tag_occupied", "title": "👤 Occupied"}},
                        {"type": "reply", "reply": {"id": "tag_unoccupied", "title": "🔲 Unoccupied"}}
                    ]
                }
            }
        }

    def format_main_menu(self):
        sections = [
            {
                "title": "Monitoring",
                "rows": [
                    {"id": "cmd_status", "title": "📊 Status", "description": "Get system status"},
                    {"id": "cmd_last_img", "title": "🖼️ Latest Image", "description": "View last capture"}
                ]
            },
            {
                "title": "Controls",
                "rows": [
                    {"id": "cmd_cam_toggle", "title": "📹 Camera Toggle", "description": "Turn ON/OFF stream"},
                    {"id": "cmd_notify_toggle", "title": "🔔 Alert Toggle", "description": "Enable/Disable alerts"},
                    {"id": "menu_rotate", "title": "🔄 Rotate Camera", "description": "Move the camera"}
                ]
            }
        ]
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.wa_id,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": "Security Mate"},
                "body": {"text": "Select an action for your security system:"},
                "footer": {"text": "Control Panel"},
                "action": {
                    "button": "Control Menu",
                    "sections": sections
                }
            }
        }

    def format_rotation_menu(self):
        rows = [
            {"id": "rot_center", "title": "📍 Center", "description": "Return to (0,0)"},
            {"id": "rot_left", "title": "⬅️ Left", "description": "Pan left"},
            {"id": "rot_right", "title": "➡️ Right", "description": "Pan right"},
            {"id": "rot_up", "title": "⬆️ Up", "description": "Tilt up"},
            {"id": "rot_down", "title": "⬇️ Down", "description": "Tilt down"},
            {"id": "main_menu", "title": "🔙 Back", "description": "Main menu"}
        ]
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.wa_id,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": "Camera Rotation"},
                "body": {"text": "Select a movement preset:"},
                "action": {
                    "button": "Movement",
                    "sections": [{"title": "Presets", "rows": rows}]
                }
            }
        }
