import logging
import json
import os
from flask import Blueprint, request, jsonify, current_app
from app import utils, config
from app.api import CameraController, SystemController
from app.whatsapp.whatsapp import WhatsAppService

LOGGER = logging.getLogger(__name__)

whatsapp_bp = Blueprint('whatsapp', __name__)

@whatsapp_bp.route('/webhook', methods=["GET"])
def verify():
    """WhatsApp webhook verification (GET request from Meta)"""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    # Get verify token from config
    conf = current_app.config.get('whatsapp', {})
    verify_token = conf.get('verify_token')
    
    if mode and token:
        if mode == "subscribe" and token == verify_token:
            LOGGER.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            LOGGER.error("WEBHOOK_VERIFICATION_FAILED")
            return jsonify({"status": "error", "message": "Verification failed"}), 403
            
    return jsonify({"status": "error", "message": "Missing parameters"}), 400

@whatsapp_bp.route('/webhook', methods=["POST"])
def webhook():
    """Handle incoming WhatsApp messages (POST request from Meta)"""
    body = request.get_json()
    
    # Validate WhatsApp message structure
    if not (body.get("entry") and 
            body["entry"][0].get("changes") and 
            body["entry"][0]["changes"][0].get("value") and 
            body["entry"][0]["changes"][0]["value"].get("messages")):
        return jsonify({"status": "ok"}), 200

    entry_value = body["entry"][0]["changes"][0]["value"]
    message = entry_value["messages"][0]
    wa_id = entry_value["contacts"][0]["wa_id"]
    
    wa_service = WhatsAppService(body=body)
    
    try:
        wa_service.process_inbound_message(message)
        # Send all queued responses
        wa_service.flush_messages()
        
    except Exception as e:
        LOGGER.error(f"Error processing WhatsApp webhook: {e}")
        # Optionally send a generic error message to the user
        # wa_service.send_text("⚠️ An error occurred while processing your command.")
        # wa_service.flush_messages()

    return jsonify({"status": "ok"}), 200