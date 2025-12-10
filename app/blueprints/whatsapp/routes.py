# app/blueprints/whatsapp/routes.py
from flask import Blueprint, request, jsonify

whatsapp_bp = Blueprint('whatsapp', __name__)

@whatsapp_bp.route('/webhook', methods=["POST"])
def webhook():
    """WhatsApp webhook endpoint"""
    # To be implemented
    return jsonify({"status": "WhatsApp integration coming soon"})

@whatsapp_bp.route('/send_alert', methods=["POST"])
def send_alert():
    """Send alert via WhatsApp"""
    # To be implemented
    pass