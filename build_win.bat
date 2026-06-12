@echo off
chcp 65001 > NUL
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo → 正在虛擬環境中安裝/更新 PyInstaller 打包工具...
call venv\Scripts\pip.exe install pyinstaller

echo.
echo → 正在打包 Windows 執行檔 PWDManager.exe...
call venv\Scripts\pyinstaller.exe PWDManager_win.spec --noconfirm

echo.
echo ==================================================
echo   ✓ 打包完成！執行檔位於：
echo     %~dp0dist\PWDManager.exe
echo ==================================================
echo.
pause
