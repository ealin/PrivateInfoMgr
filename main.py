"""
macOS entry point for the packaged PWDManager.app.

Responsibilities:
  1. Start Flask server in a background thread.
  2. Open the browser once the server is ready.
  3. Show a menu-bar icon (via rumps) with Open / Quit items.
"""

import threading
import time
import webbrowser

import rumps

PORT = 5000
URL  = f'http://127.0.0.1:{PORT}'


def _run_flask() -> None:
    from app import app
    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)


def _open_browser_when_ready() -> None:
    # Poll until the server accepts connections, then open the browser.
    import socket
    for _ in range(20):
        try:
            with socket.create_connection(('127.0.0.1', PORT), timeout=0.5):
                break
        except OSError:
            time.sleep(0.3)
    webbrowser.open(URL)


class PWDManagerApp(rumps.App):
    def __init__(self):
        super().__init__('PWDManager', title='🔐', quit_button='結束')
        self.menu = [rumps.MenuItem('開啟管理頁面', callback=self.open_page)]

    def open_page(self, _):
        webbrowser.open(URL)


def main() -> None:
    threading.Thread(target=_run_flask, daemon=True).start()
    threading.Thread(target=_open_browser_when_ready, daemon=True).start()
    PWDManagerApp().run()


if __name__ == '__main__':
    main()
