"""Admin authentication: password hashing and self-issued session tokens.

No external auth service (Cognito, etc.) is used -- there's exactly one
admin user (the site owner), so a signed bearer token is enough. The token
is a minimal hand-rolled analog of a JWT (base64url payload + HMAC-SHA256
signature) rather than a PyJWT dependency, to avoid adding a library for
something this small.
"""
import base64
import hashlib
import hmac
import json
import os
import time
from functools import wraps

from flask import jsonify, request

TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
PBKDF2_ITERATIONS = 210_000

LOCAL_MODE = os.getenv('LOCAL_MODE') == 'true'

_param_cache = {}


def _fetch_ssm_parameter(name):
    import boto3
    ssm = boto3.client('ssm')
    return ssm.get_parameter(Name=name, WithDecryption=True)['Parameter']['Value']


def _cached_param(name):
    # Cached per warm Lambda container, mirroring how DynamoUtil/S3Util
    # construct their AWS clients once at import time rather than per-request.
    if name not in _param_cache:
        _param_cache[name] = _fetch_ssm_parameter(name)
    return _param_cache[name]


if LOCAL_MODE:
    def _admin_username():
        return os.getenv('ADMIN_USERNAME', 'admin')

    def _admin_password_hash():
        # Local-dev-only default credential: username "admin", password
        # "admin". Never reachable outside LOCAL_MODE.
        return os.getenv('ADMIN_PASSWORD_HASH') or hash_password('admin', salt=b'local-dev-salt-0000')

    def _token_secret():
        return os.getenv('ADMIN_TOKEN_SECRET', 'local-dev-token-secret-do-not-use-in-prod')
else:
    def _admin_username():
        return _cached_param('AdminUsername')

    def _admin_password_hash():
        return _cached_param('AdminPasswordHash')

    def _token_secret():
        return _cached_param('AdminTokenSecret')


def hash_password(password, salt=None):
    """Return a `<salt_hex>$<digest_hex>` string suitable for storing in
    the AdminPasswordHash SSM parameter."""
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS)
    return f'{salt.hex()}${digest.hex()}'


def _verify_password(password, stored_hash):
    try:
        salt_hex, digest_hex = stored_hash.split('$', 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(actual, expected)


def verify_credentials(username, password):
    return hmac.compare_digest(username, _admin_username()) and _verify_password(password, _admin_password_hash())


def _b64encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _b64decode(data):
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def issue_token(username):
    payload = {'sub': username, 'exp': int(time.time()) + TOKEN_TTL_SECONDS}
    payload_b64 = _b64encode(json.dumps(payload).encode('utf-8'))
    signature = hmac.new(_token_secret().encode('utf-8'), payload_b64.encode('ascii'), hashlib.sha256).digest()
    return f'{payload_b64}.{_b64encode(signature)}'


def _verify_token(token):
    try:
        payload_b64, signature_b64 = token.split('.', 1)
    except ValueError:
        return None

    expected_sig = hmac.new(_token_secret().encode('utf-8'), payload_b64.encode('ascii'), hashlib.sha256).digest()
    try:
        actual_sig = _b64decode(signature_b64)
    except ValueError:  # binascii.Error is a ValueError subclass
        return None
    if not hmac.compare_digest(expected_sig, actual_sig):
        return None

    try:
        payload = json.loads(_b64decode(payload_b64))
    except (ValueError, UnicodeDecodeError):
        return None
    if payload.get('exp', 0) < time.time():
        return None
    return payload


def require_admin_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        if _verify_token(header[len('Bearer '):]) is None:
            return jsonify({'error': 'Invalid or expired session'}), 401
        return view(*args, **kwargs)
    return wrapper
