"""
Copyright (c) Meta Platforms, Inc. and affiliates.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import json
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


class FlowEndpointException(Exception):
    """Custom exception for Flow endpoint errors"""

    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code
        self.name = self.__class__.__name__


def decrypt_request(body, private_pem, passphrase):
    """
    Decrypt the request from WhatsApp Flow

    Args:
        body (dict): Request body containing encrypted data
        private_pem (str): Private key in PEM format
        passphrase (str): Passphrase for the private key

    Returns:
        dict: Decrypted data including body, AES key buffer, and initial vector
    """
    encrypted_aes_key = body["encrypted_aes_key"]
    encrypted_flow_data = body["encrypted_flow_data"]
    initial_vector = body["initial_vector"]

    # Load private key
    private_key = serialization.load_pem_private_key(
        private_pem.encode("utf-8"),
        password=passphrase.encode("utf-8") if passphrase else None,
        backend=default_backend(),
    )

    try:
        # Decrypt AES key created by client
        decrypted_aes_key = private_key.decrypt(
            base64.b64decode(encrypted_aes_key),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except Exception as error:
        print(f"Decryption error: {error}")
        raise FlowEndpointException(
            421, "Failed to decrypt the request. Please verify your private key."
        )

    # Decrypt flow data
    flow_data_buffer = base64.b64decode(encrypted_flow_data)
    initial_vector_buffer = base64.b64decode(initial_vector)

    TAG_LENGTH = 16
    encrypted_flow_data_body = flow_data_buffer[:-TAG_LENGTH]
    encrypted_flow_data_tag = flow_data_buffer[-TAG_LENGTH:]

    # Create cipher for AES-128-GCM decryption
    cipher = Cipher(
        algorithms.AES(decrypted_aes_key),
        modes.GCM(initial_vector_buffer, encrypted_flow_data_tag),
        backend=default_backend(),
    )
    decryptor = cipher.decryptor()

    # Decrypt the data
    decrypted_data = decryptor.update(encrypted_flow_data_body) + decryptor.finalize()
    decrypted_json_string = decrypted_data.decode("utf-8")

    return {
        "decryptedBody": json.loads(decrypted_json_string),
        "aesKeyBuffer": decrypted_aes_key,
        "initialVectorBuffer": initial_vector_buffer,
    }


def encrypt_response(response, aes_key_buffer, initial_vector_buffer):
    """
    Encrypt the response to send back to WhatsApp Flow

    Args:
        response (dict): Response data to encrypt
        aes_key_buffer (bytes): AES key buffer
        initial_vector_buffer (bytes): Initial vector buffer

    Returns:
        str: Base64 encoded encrypted response
    """
    # Flip initial vector (bitwise NOT operation)
    flipped_iv = bytes([~byte & 0xFF for byte in initial_vector_buffer])

    # Create cipher for AES-128-GCM encryption
    cipher = Cipher(
        algorithms.AES(aes_key_buffer), modes.GCM(flipped_iv), backend=default_backend()
    )
    encryptor = cipher.encryptor()

    # Encrypt response data
    response_json = json.dumps(response)
    encrypted_data = (
        encryptor.update(response_json.encode("utf-8")) + encryptor.finalize()
    )

    # Combine encrypted data with auth tag
    encrypted_response = encrypted_data + encryptor.tag

    return base64.b64encode(encrypted_response).decode("utf-8")
