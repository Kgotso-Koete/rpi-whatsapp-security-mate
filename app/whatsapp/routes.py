"""
WhatsApp webhook routes for Flask

Handles:
- GET /webhook - Meta verification handshake
- POST /webhook - Incoming messages from WhatsApp
"""
import logging
import json
from flask import Blueprint, request, Response, current_app
from app.whatsapp.whatsapp import WhatsAppService

LOGGER = logging.getLogger(__name__)

whatsapp_bp = Blueprint('whatsapp', __name__)


@whatsapp_bp.route('/webhook', methods=["GET"])
def verify():
    """
    WhatsApp webhook verification (GET request from Meta)
    
    Meta sends:
    - hub.mode: should be "subscribe"
    - hub.verify_token: must match our configured token
    - hub.challenge: we return this to confirm
    
    IMPORTANT: Must return the challenge as plain text, not JSON
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    # Get verify token from config
    # Config is loaded from private.yml into Flask's config dict
    whatsapp_config = current_app.config.get('whatsapp', {})
    verify_token = whatsapp_config.get('verify_token')
    
    # Debug logging to help diagnose issues
    LOGGER.info(f"=== WEBHOOK VERIFICATION REQUEST ===")
    LOGGER.info(f"Received: mode={mode}, token={token}, challenge={challenge[:20] if challenge else None}...")
    LOGGER.info(f"Expected verify_token from config: {verify_token}")
    LOGGER.info(f"WhatsApp config keys: {list(whatsapp_config.keys())}")
    
    # Check if config is missing
    if not verify_token:
        LOGGER.error("VERIFICATION FAILED: No verify_token in config. Check that private.yml exists and is loaded.")
        return Response(
            json.dumps({"error": "Server misconfigured - missing verify_token"}),
            status=500,
            mimetype='application/json'
        )
    
    # Validate the request
    if not mode or not token:
        LOGGER.warning("VERIFICATION FAILED: Missing hub.mode or hub.verify_token in request")
        return Response(
            json.dumps({"error": "Missing required parameters"}),
            status=400,
            mimetype='application/json'
        )
    
    # Check mode and token match
    # Convert both to strings to handle YAML parsing integers as int
    if mode == "subscribe" and str(token) == str(verify_token):
        LOGGER.info("WEBHOOK VERIFIED SUCCESSFULLY!")
        # CRITICAL: Return challenge as plain text, not JSON
        return Response(str(challenge), status=200, mimetype='text/plain')
    else:
        LOGGER.warning(f"VERIFICATION FAILED: Token mismatch. Got '{token}', expected '{verify_token}'")
        return Response(
            json.dumps({"error": "Verification failed - token mismatch"}),
            status=403,
            mimetype='application/json'
        )


@whatsapp_bp.route('/webhook', methods=["POST"])
def webhook():
    """
    Handle incoming WhatsApp messages (POST request from Meta)
    
    Meta sends various webhooks including:
    - Incoming messages (text, interactive, etc.)
    - Message status updates (sent, delivered, read)
    - Other notifications
    """
    body = request.get_json()
    
    LOGGER.debug(f"Webhook POST received: {json.dumps(body)[:500]}...")
    
    # Validate basic WhatsApp webhook structure
    if not body:
        LOGGER.warning("Empty webhook body received")
        return Response(json.dumps({"status": "ok"}), status=200, mimetype='application/json')
    
    # Extract the entry/changes/value structure
    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
    except (IndexError, KeyError) as e:
        LOGGER.debug(f"Non-standard webhook structure: {e}")
        return Response(json.dumps({"status": "ok"}), status=200, mimetype='application/json')

    if not value:
        LOGGER.debug("No value in webhook")
        return Response(json.dumps({"status": "ok"}), status=200, mimetype='application/json')
    
    # Handle status updates (delivered, read, etc.) - just acknowledge
    if value.get("statuses"):
        status = value["statuses"][0].get("status", "unknown")
        LOGGER.debug(f"Message status update: {status}")
        return Response(json.dumps({"status": "ok"}), status=200, mimetype='application/json')
        
    # Handle incoming messages
    messages = value.get("messages")
    if not messages:
        LOGGER.debug("No messages in webhook")
        return Response(json.dumps({"status": "ok"}), status=200, mimetype='application/json')

    # Process the message
    message = messages[0]
    LOGGER.info(f"Processing incoming message type: {message.get('type')}")
    
    try:
        wa_service = WhatsAppService(body=body)
        wa_service.process_inbound_message(message)
        wa_service.flush_messages()
    except Exception as e:
        LOGGER.error(f"Error processing WhatsApp message: {e}", exc_info=True)
        # Still return 200 to prevent Meta from retrying
    
    return Response(json.dumps({"status": "ok"}), status=200, mimetype='application/json')