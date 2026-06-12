"""
Entry point for the packaged PWDManager.

On macOS:
  1. Starts Flask server in a background thread.
  2. Opens the browser once the server is ready.
  3. Shows a menu-bar icon (via rumps) with Open / Quit items.

On Windows / Other platforms:
  1. Opens the browser once the server is ready.
  2. Runs Flask server in the main thread with user-friendly console guidance.
"""

import socket
import sys
import threading
import time
import webbrowser

PORT = 5000
URL  = f'http://127.0.0.1:{PORT}'


def _run_flask() -> None:
    from app import app
    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)


def _open_browser_when_ready() -> None:
    # Poll until the server accepts connections, then open the browser.
    for _ in range(20):
        try:
            with socket.create_connection(('127.0.0.1', PORT), timeout=0.5):
                break
        except OSError:
            time.sleep(0.3)
    webbrowser.open(URL)


def main() -> None:
    if sys.platform == 'darwin':
        # macOS uses rumps for menu-bar app
        import rumps

        class PWDManagerApp(rumps.App):
            def __init__(self):
                super().__init__('PWDManager', title='🔐', quit_button='結束')
                self.menu = [rumps.MenuItem('開啟管理頁面', callback=self.open_page)]

            def open_page(self, _):
                webbrowser.open(URL)
        
        threading.Thread(target=_run_flask, daemon=True).start()
        threading.Thread(target=_open_browser_when_ready, daemon=True).start()
        PWDManagerApp().run()
    else:
        # Windows/Linux: simple console runner
        print("==================================================")
        print("  Ealin 私人資訊管理系統 (Ealin PrivateInfoMgr)")
        print("==================================================")
        print(" 伺服器正在啟動，請勿關閉此視窗。")
        print(f" 瀏覽器將會自動開啟管理頁面：{URL}")
        print(" 如果網頁沒有自動打開，請手動在瀏覽器中輸入上方網址。")
        print(" 欲結束服務，請直接關閉此視窗，或在視窗內按下 Ctrl+C。")
        print("==================================================")
        
        threading.Thread(target=_open_browser_when_ready, daemon=True).start()
        _run_flask()


if __name__ == '__main__':
    main()
