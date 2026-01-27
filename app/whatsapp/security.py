# whatsapp security imports
from functools import wraps
from flask import current_app, jsonify, request
import logging
import hashlib
import hmac
import base64
import json
from functools import wraps
from flask import current_app, jsonify, request
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.exceptions import InvalidSignature
import os

# key pair generation imports
from pathlib import Path
from dotenv import set_key
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from dotenv import load_dotenv


# *******************************************************************************
# General WhatsApp webhook security functions
# *******************************************************************************
def validate_signature(payload, signature):
    """
    Validate the incoming payload's signature against our expected signature
    """
    # Use the App Secret to hash the payload
    expected_signature = hmac.new(
        bytes(current_app.config["APP_SECRET"], "latin-1"),
        msg=payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # DEBUG: Log the signatures to comparing them
    logging.info(f"DEBUG SIGNATURE ------------")
    logging.info(f"APP_SECRET (first 5 chars): {current_app.config['APP_SECRET'][:5]}...")
    logging.info(f"Received Signature: {signature}")
    logging.info(f"Computed Signature: {expected_signature}")
    logging.info(f"Payload Length: {len(payload)}")
    logging.info(f"DEBUG SIGNATURE ------------")

    # Check if the signature matches
    return hmac.compare_digest(expected_signature, signature)


def signature_required(f):
    """
    Decorator to ensure that the incoming requests to our webhook are valid and signed with the correct signature.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        signature = request.headers.get("X-Hub-Signature-256", "")[
            7:
        ]  # Removing 'sha256='
        if not validate_signature(request.data.decode("utf-8"), signature):
            logging.info("Signature verification failed!")
            return jsonify({"status": "error", "message": "Invalid signature"}), 403
        return f(*args, **kwargs)

    return decorated_function


# *******************************************************************************
# WhatsApp Flow webhook security functions
# *******************************************************************************


def verify_flow_signature(f):
    """
    Decorator to verify the signature of incoming WhatsApp Flow webhook requests.
    Validates the X-Hub-Signature-256 header against the request payload.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get the signature from the header
        signature_header = request.headers.get("X-Hub-Signature-256", "")
        if not signature_header:
            current_app.logger.error("Missing X-Hub-Signature-256 header")
            return (
                jsonify({"status": "error", "message": "Missing signature header"}),
                400,
            )

        # Extract the signature (remove 'sha256=' prefix)
        try:
            signature = signature_header.split("sha256=")[1]
        except IndexError:
            current_app.logger.error("Invalid signature format")
            return (
                jsonify({"status": "error", "message": "Invalid signature format"}),
                400,
            )

        # Get the raw request body
        request_body = request.get_data(as_text=True)

        # Verify the signature
        if not _verify_flow_request_signature(request_body, signature):
            current_app.logger.error("Invalid signature for flow request")
            return jsonify({"status": "error", "message": "Invalid signature"}), 403

        return f(*args, **kwargs)

    return decorated_function


def _verify_flow_request_signature(payload, signature):
    """
    Verify the signature of a WhatsApp Flow webhook request.

    Args:
        payload: The raw request payload as a string
        signature: The signature from the X-Hub-Signature-256 header (without 'sha256=' prefix)

    Returns:
        bool: True if the signature is valid, False otherwise
    """
    try:
        # Get the app secret from config
        app_secret = current_app.config.get("APP_SECRET")
        if not app_secret:
            current_app.logger.error("APP_SECRET not configured")
            return False

        # Create a new HMAC-SHA256 hasher with the app secret
        hmac_obj = hmac.new(
            key=app_secret.encode("utf-8"),
            msg=payload.encode("utf-8"),
            digestmod=hashlib.sha256,
        )

        # Generate the expected signature
        expected_signature = hmac_obj.hexdigest()

        # Compare the signatures in constant time to avoid timing attacks
        return hmac.compare_digest(expected_signature, signature)

    except Exception as e:
        current_app.logger.error(f"Error verifying flow signature: {str(e)}")
        return False


# *******************************************************************************
# Key generation functions
# *******************************************************************************
def generate_Key_pair_sync():
    """
    Generate an RSA key pair and update both the .env file and app.config with the public and private keys.

    This ensures the application uses the latest keys even if .env file updates don't take effect immediately.

    Returns:
        dict: A dictionary containing the public and private keys
    """
    # Get the passphrase from environment variables
    passphrase = os.getenv("PASSPHRASE")
    if not passphrase:
        raise ValueError("PASSPHRASE environment variable is not set")

    try:
        # Generate private key
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        # Get private key in PEM format with encryption
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.BestAvailableEncryption(
                passphrase.encode("utf-8")
            ),
        ).decode("utf-8")

        # Get public key in PEM format
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        # Prepare the key data to return
        key_data = {"privateKey": private_pem, "publicKey": public_pem}

        # Update the .env file with the new keys
        project_root = Path(__file__).parent.parent.parent
        env_path = project_root / ".env"

        set_key(env_path, "PRIVATE_KEY", f'"{private_pem}"')
        set_key(env_path, "PUBLIC_KEY", f'"{public_pem}"')

        # Reload environment variables from the updated .env file
        load_dotenv(env_path, override=True)

        # Update app.config with the new keys
        if current_app:
            current_app.config["PRIVATE_KEY"] = private_pem
            current_app.config["PUBLIC_KEY"] = public_pem
            current_app.config["PASSPHRASE"] = passphrase

        print(f"Key pair generated successfully: {key_data}✅✅✅ 🔑🔑\n")
        return key_data

    except Exception as e:
        current_app.logger.error(f"Error generating key pair: {str(e)}")
        raise


def is_request_signature_valid(req) -> bool:
    """
    Verify request signature from WhatsApp using APP_SECRET.
    """

    APP_SECRET = os.getenv("APP_SECRET")

    if not APP_SECRET:
        logging.warning(
            "App Secret is not set up. Please add your app secret in .env file to check for request validation"
        )
        return True

    signature_header = req.headers.get("x-hub-signature-256")
    if not signature_header:
        logging.error("Missing signature header.")
        return False

    try:
        signature = signature_header.replace("sha256=", "")
        signature_bytes = bytes(signature, "utf-8")

        digest = hmac.new(
            APP_SECRET.encode("utf-8"),
            msg=req.get_data(),
            digestmod=hashlib.sha256,
        ).hexdigest()

        digest_bytes = bytes(digest, "utf-8")

        if not hmac.compare_digest(digest_bytes, signature_bytes):
            logging.error("Error: Request Signature did not match")
            return False
    except Exception as e:
        logging.error(f"Error validating signature: {e}")
        return False

    print(f"Request signature is valid: ✅✅✅ 🔑\n")
    return True
