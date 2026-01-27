# whatsapp open api chat bot imports
from app.api import bp
import logging
import json
import sys
from flask import request, jsonify, current_app, make_response, json
import base64
from app.api.encryption import (
    decrypt_request,
    encrypt_response,
    FlowEndpointException,
)
from app.api.security import (
    signature_required,
    verify_flow_signature,
    generate_Key_pair_sync,
    is_request_signature_valid,
)
from app.services.whatsapp import WhatsAppService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)


@bp.route("/chatbot", methods=["GET"])
def get_chatbot():
    print("Getting chatbot response---->")
    return "Getting chatbot response---->"


@bp.route("/chatbot/webhook", methods=["GET"])
# Required webhook verification for WhatsApp
def verify():
    # Parse params from the webhook verification request
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    # Check if a token and mode were sent
    if mode and token:
        # Check the mode and token sent are correct
        if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]:
            # Respond with 200 OK and challenge token from the request
            logging.info("WEBHOOK_VERIFIED")
            print("WEBHOOK_VERIFIED ✅✅✅\n")
            return challenge, 200
        else:
            # Responds with '403 Forbidden' if verify tokens do not match
            logging.info("VERIFICATION_FAILED")
            print("VERIFICATION_FAILED ❌❌❌\n")
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    else:
        # Responds with '400 Bad Request' if verify tokens do not match
        logging.info("MISSING_PARAMETER")
        print("MISSING_PARAMETER ❌❌❌\n")
        return jsonify({"status": "error", "message": "Missing parameters"}), 400


@bp.route("/chatbot/webhook", methods=["POST"])
@signature_required
@verify_flow_signature
def handle_message():
    """
    Handle incoming webhook events from the WhatsApp API.
    This function processes incoming WhatsApp messages and other events,
    such as delivery statuses. If the event is a valid message, it gets
    processed. If the incoming payload is not a recognized WhatsApp event,
    an error is returned.
    """
    body = request.get_json()
    if current_app.config["DEBUG_WHATSAPP"] == "1":
        logging.info(f"Received webhook: {json.dumps(body, indent=2)}")

    # Check if it's a status update (message delivery reports, reads, etc.)
    if (
        body.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("statuses")
    ):
        logging.info("Received a WhatsApp status update.")
        return jsonify({"status": "ok"}), 200

    # Check if it's a flow status update
    if body.get("entry", [{}])[0].get("changes", [{}])[0].get("field") == "flows":
        logging.info("Received flow status update")
        return jsonify({"status": "ok"}), 200

    # Process regular messages
    try:
        whatsapp_service = WhatsAppService(body=body)

        # If this is a duplicate message (retry), return OK immediately to stop the loop
        if getattr(whatsapp_service, "is_duplicate", False):
            return jsonify({"status": "ok", "message": "Duplicate skipped"}), 200

        # Check if we have a valid message format
        if (
            not hasattr(whatsapp_service, "message_formatter")
            or not whatsapp_service.message_formatter
        ):
            logging.error("Message formatter not initialized")
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Failed to initialize message handler",
                    }
                ),
                500,
            )

        # Start conversation with the sender
        whatsapp_service.start_conversation_with_inbound_sender()
        # Auto-flush any remaining messages
        whatsapp_service.flush_messages()
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logging.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/chatbot/create-flow", methods=["GET"])
def create_flow():
    whatsapp_service = WhatsAppService()
    whatsapp_service.create_flow()
    return jsonify({"status": "ok"}), 200


@bp.route("/chatbot/webhook/flow/health", methods=["GET"])
def flow_health_check():
    """
    Health check endpoint for WhatsApp Flow.
    WhatsApp will periodically call this endpoint to verify the endpoint is healthy.
    """
    return jsonify({"data": {"status": "active"}}), 200


@bp.route("/chatbot/generate-key-pair", methods=["GET"])
def generate_key_pair():
    try:
        keys = generate_Key_pair_sync()
        result = {
            "success": True,
            "message": "Key pair generated successfully",
            "publicKey": keys["publicKey"],
            # Note: privateKey is intentionally not returned for security
        }

        return (jsonify(result), 200)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/chatbot/set_business_public_key", methods=["GET"])
def set_business_public_key():
    try:
        generate_Key_pair_sync()
        whatsapp_service = WhatsAppService()
        result = whatsapp_service.set_business_public_key()
        if (
            isinstance(result, tuple) and len(result) == 2
        ):  # If it's an error response with status code
            return jsonify(result[0].get_json()), result[1]
        return jsonify({"data": result})
    except Exception as e:
        logging.error(f"Error in set_business_public_key: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/chatbot/register-phone-number", methods=["GET"])
def register_phone_number():
    """
    Manually register the phone number using a PIN.
    Query Params: ?pin=123456
    """
    pin = request.args.get("pin")
    if not pin:
        return jsonify({"error": "PIN is required"}), 400
        
    try:
        whatsapp_service = WhatsAppService()
        result = whatsapp_service.register_phone_number(pin)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error in register_phone_number: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/chatbot/subscribe-business-to-apps", methods=["GET"])
def subscribe_business_to_apps():
    """
    Manually subscribe the WABA to the App to fix webhook delivery issues.
    """
    try:
        whatsapp_service = WhatsAppService()
        result = whatsapp_service.subscribe_business_to_app()
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error in subscribe_business_to_apps: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/chatbot/flow", methods=["POST"])
def handle_flow():
    """
    Handle WhatsApp Flow requests with end-to-end encryption.
    This endpoint processes the encrypted flow requests, decrypts them,
    processes the flow logic, and returns an encrypted response.
    """
    # Verify request signature first
    if not is_request_signature_valid(request):
        return jsonify({"error": "Invalid signature"}), 432

    # Get the private key and passphrase from config
    private_key = current_app.config.get("PRIVATE_KEY")
    passphrase = current_app.config.get("PASSPHRASE")

    if not private_key:
        current_app.logger.error("Private key is not configured")
        return jsonify({"error": "Server configuration error"}), 500

    try:
        # Decrypt the incoming request
        decrypted = decrypt_request(request.get_json(), private_key, passphrase)
        body = decrypted["decryptedBody"]

        # Log the decrypted request for debugging

        if current_app.config["DEBUG_WHATSAPP"] == "1":
            current_app.logger.info(f"Decrypted request: {json.dumps(body, indent=2)}")
        whatsapp_service = WhatsAppService(decrypted_flow_body=body)
        # get the next response screen
        screen_response = whatsapp_service.get_next_booking_flow_screen()
        print("Screen Response: \n\n", json.dumps(screen_response, indent=2))
        # Encrypt the response
        encrypted_response = encrypt_response(
            screen_response,
            decrypted["aesKeyBuffer"],
            decrypted["initialVectorBuffer"],
        )

        # Create a response object
        response = make_response(encrypted_response)

        # Get a reference to the current app before the request ends
        app = current_app._get_current_object()

        # Add a callback to flush messages after the response is sent
        @response.call_on_close
        def process_after_request():
            with app.app_context():  # Create a new application context
                try:
                    whatsapp_service.flush_messages()
                    if app.config["DEBUG_WHATSAPP"] == "1":
                        app.logger.info(
                            "Successfully processed messages after flow response"
                        )
                except Exception as e:
                    app.logger.error(f"Error in after-request processing: {str(e)}")

        return response

    except FlowEndpointException as e:
        current_app.logger.error(f"Flow endpoint error: {str(e)}")
        return jsonify({"error": str(e)}), e.status_code
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
