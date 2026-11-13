@echo off
rem Qnote Windows Launcher
cd /d "%~dp0"
python -c "import PyQt6, pynput" >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装轻量依赖 PyQt6 与 pynput...
    pip install PyQt6 pynput
)
start "" pythonw main.py %*
