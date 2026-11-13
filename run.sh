#!/usr/bin/env bash
# Qnote Linux Launcher
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check if PyQt6 is installed
if ! python3 -c "import PyQt6, pynput" 2>/dev/null; then
    echo "正在自动安装轻量依赖 PyQt6 & pynput..."
    python3 -m pip install --user --break-system-packages PyQt6 pynput || python3 -m pip install PyQt6 pynput
fi

exec python3 "$DIR/main.py" "$@"
