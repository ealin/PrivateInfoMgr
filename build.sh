#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "→ Building PWDManager.app ..."
venv/bin/pyinstaller PWDManager.spec --noconfirm

echo ""
echo "✓ 完成！應用程式位於："
echo "  $(pwd)/dist/PWDManager.app"
echo ""
echo "首次執行前，若 macOS 顯示「無法驗證開發者」，請："
echo "  系統設定 → 隱私與安全性 → 仍要開啟"
