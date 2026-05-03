import os
import secrets
import sys

# When frozen by PyInstaller, resources live in sys._MEIPASS;
# user data goes to ~/Library/Application Support/PWDManager.
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS
    DATA_DIR   = os.path.expanduser('~/Library/Application Support/PWDManager')
else:
    BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR
    DATA_DIR   = os.path.join(BASE_DIR, 'data')


def _get_or_create_secret_key() -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    key_file = os.path.join(DATA_DIR, '.secret_key')
    if os.path.exists(key_file):
        with open(key_file, 'r') as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(key_file, 'w') as f:
        f.write(key)
    os.chmod(key_file, 0o600)
    return key


SECRET_KEY = _get_or_create_secret_key()
