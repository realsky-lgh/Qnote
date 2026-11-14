#!/usr/bin/env bash
# ===================================================
# Qnote Linux Standalone Binary Build Script
# Produces dist/qnote-linux-x86_64
# ===================================================
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "[1/3] 检查构建环境与依赖..."
python3 -m pip install --user --break-system-packages PyQt6 pynput pyinstaller 2>/dev/null || python3 -m pip install PyQt6 pynput pyinstaller

echo "[2/3] 开始打包独立二进制 qnote-linux-x86_64..."
python3 -m PyInstaller \
    --name qnote-linux-x86_64 \
    --onefile \
    --windowed \
    --icon resources/qnote.png \
    --add-data "resources/qnote.png:resources" \
    --hidden-import PyQt6.QtCore \
    --hidden-import PyQt6.QtGui \
    --hidden-import PyQt6.QtWidgets \
    --hidden-import PyQt6.QtNetwork \
    --hidden-import pynput.keyboard \
    --hidden-import pynput.keyboard._xorg \
    --hidden-import pynput.keyboard._uinput \
    --collect-all qnote \
    main.py

echo "[3/3] 打包完成！独立二进制位于 dist/qnote-linux-x86_64"
