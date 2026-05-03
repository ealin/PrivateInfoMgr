"""
Encryption core module.

Design:
- Argon2id  : password hashing (authentication)
- PBKDF2-SHA256 (600k iterations) : derive AES key from Layer-2 password
- AES-256-GCM : encrypt Master Key and all record fields
- Master Key (32 random bytes) is never stored in plaintext; it lives only in
  server memory during an authenticated session.
"""

import base64
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError, InvalidHashError
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


# ── Password hashing (Argon2id) ──────────────────────────────────────────────

def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return _ph.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# ── Master Key management ────────────────────────────────────────────────────

def generate_master_key() -> bytes:
    return secrets.token_bytes(32)


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    return kdf.derive(password.encode('utf-8'))


def encrypt_master_key(master_key: bytes, password2: str) -> tuple[bytes, bytes]:
    """Return (encrypted_master_key, salt). Both stored in DB."""
    salt = secrets.token_bytes(16)
    key = _derive_key(password2, salt)
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, master_key, None)
    return nonce + ciphertext, salt


def decrypt_master_key(encrypted: bytes, password2: str, salt: bytes) -> bytes:
    key = _derive_key(password2, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(encrypted[:12], encrypted[12:], None)


# ── Field encryption (AES-256-GCM) ──────────────────────────────────────────

def encrypt_field(value: str, master_key: bytes) -> str:
    """Encrypt a text field. Returns base64(nonce[12] + ciphertext+tag)."""
    if value is None:
        value = ''
    aesgcm = AESGCM(master_key)
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, value.encode('utf-8'), None)
    return base64.b64encode(nonce + ciphertext).decode('ascii')


def decrypt_field(encrypted: str, master_key: bytes) -> str:
    """Decrypt a field encrypted by encrypt_field. Returns empty string for empty input."""
    if not encrypted:
        return ''
    raw = base64.b64decode(encrypted.encode('ascii'))
    aesgcm = AESGCM(master_key)
    return aesgcm.decrypt(raw[:12], raw[12:], None).decode('utf-8')
