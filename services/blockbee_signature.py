# blockbee_signature.py
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from flask import request
from config import BLOCKBEE_PUBLIC_KEY


def verify_blockbee_signature(req=None):
    """
    Verify that an incoming BlockBee webhook really came from them.
    Expects the Flask `request` object (or uses the global if not passed).
    """
    req = req or request
    signature_b64 = req.headers.get('x-ca-signature')
    if not signature_b64:
        return False

    # Determine data to verify
    if req.method == 'GET':
        data_to_verify = req.url
    else:
        data_to_verify = req.get_data(as_text=True)

    # Load the public key
    public_key = serialization.load_pem_public_key(
        BLOCKBEE_PUBLIC_KEY.encode(),
        backend=default_backend()
    )

    # Decode and verify
    try:
        signature = base64.b64decode(signature_b64)
        public_key.verify(
            signature,
            data_to_verify.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False
