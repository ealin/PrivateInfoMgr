import os
import secrets
import sys

# When frozen by PyInstaller, resources live in sys._MEIPASS;
# user data goes to ~/Library/Application Support/PWDManager.
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS
    if sys.platform == 'win32':
        # Windows: 儲存於與執行檔 (.exe) 相同目錄下的 data 資料夾中
        DATA_DIR = os.path.join(os.path.dirname(sys.executable), 'data')
    elif sys.platform == 'darwin':
        # macOS: 儲存於與 .app 相同目錄底下的 data 資料夾中。
        # 由於 sys.executable 通常指向 PWDManager.app/Contents/MacOS/PWDManager，
        # 為了取得與 PWDManager.app 同層之目錄，需向上爬升四層父目錄。
        exe_path = sys.executable
        if '.app/Contents/MacOS' in exe_path.replace('\\', '/'):
            app_dir = exe_path
            for _ in range(4):
                app_dir = os.path.dirname(app_dir)
            DATA_DIR = os.path.join(app_dir, 'data')
        else:
            DATA_DIR = os.path.join(os.path.dirname(exe_path), 'data')
    else:
        # 其他平台: 儲存於與執行檔相同目錄底下的 data 資料夾中
        DATA_DIR = os.path.join(os.path.dirname(sys.executable), 'data')
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
