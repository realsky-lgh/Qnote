#!/usr/bin/env bash
# Qnote Linux One-click Install Script
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.local/share/applications"

# 1. Ensure dependencies
echo "[1/3] 检查 Python 依赖..."
if ! python3 -c "import PyQt6, pynput" 2>/dev/null; then
    echo "安装轻量依赖 PyQt6 & pynput..."
    python3 -m pip install --user --break-system-packages PyQt6 pynput 2>/dev/null || python3 -m pip install --user PyQt6 pynput
fi

# 2. Create qnote command symlink in ~/.local/bin
echo "[2/3] 创建命令行快捷方式 qnote..."
cat << 'EOF' > "$HOME/.local/bin/qnote"
#!/usr/bin/env bash
DIR_TARGET="$(dirname "$(readlink -f "$0")")/../.."
exec python3 -m qnote "$@"
EOF
# Replace with actual absolute path
cat << EOF > "$HOME/.local/bin/qnote"
#!/usr/bin/env bash
exec python3 "$DIR/main.py" "\$@"
EOF
chmod +x "$HOME/.local/bin/qnote"

# 3. Create Desktop Entry
echo "[3/3] 创建桌面应用图标..."
cat << EOF > "$HOME/.local/share/applications/qnote.desktop"
[Desktop Entry]
Name=Qnote 速记纸
Comment=极简速记纸：双击Alt呼出，双击~切换手绘与文字，10款艺术护眼底纹
Exec=$HOME/.local/bin/qnote
Icon=accessories-text-editor
Terminal=false
Type=Application
Categories=Utility;Office;TextEditor;
StartupNotify=false
EOF
chmod +x "$HOME/.local/share/applications/qnote.desktop"

echo "================================================="
echo "  Qnote 安装完成！"
echo "  • 随时在终端输入: qnote"
echo "  • 全局双击 Alt 键: 随时呼出 / 隐藏速记纸"
echo "  • 按两次 ~ 键: 随意切换丝滑涂鸦与文字"
echo "  • 换新纸: Ctrl+N | 切纸张底纹: Ctrl+P"
echo "================================================="
