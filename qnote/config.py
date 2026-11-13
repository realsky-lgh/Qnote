"""
Qnote Configuration and Cross-Platform Paths
"""
import os
import sys
from pathlib import Path

APP_NAME = "Qnote"
APP_TITLE = "Qnote - 极简速记纸"
APP_VERSION = "1.0.2"

def get_data_dir() -> Path:
    """Returns platform-specific data directory for storing database and configs."""
    if sys.platform == "win32":
        app_data = os.environ.get("APPDATA")
        if app_data:
            base = Path(app_data)
        else:
            base = Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        # Linux / Unix XDG standard
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            base = Path(xdg_config)
        else:
            base = Path.home() / ".config"
            
    target = base / "qnote"
    target.mkdir(parents=True, exist_ok=True)
    return target

def get_db_path() -> Path:
    """Single-file lightweight sqlite database path."""
    return get_data_dir() / "qnote.db"

# Window geometry defaults
DEFAULT_WIDTH = 480
DEFAULT_HEIGHT = 580
WINDOW_CORNER_RADIUS = 16

# Ink Drawing Settings
DEFAULT_INK_COLOR_LIGHT = "#18181c"  # 深玄墨黑 (接近黑色，柔和有墨韵)
DEFAULT_INK_COLOR_DARK = "#f0f0f4"   # 极夜银白墨 (用于深色暗夜纸)
BASE_PEN_WIDTH = 2.6                 # 基础笔宽
MIN_PEN_WIDTH = 1.6                  # 快速提笔最小笔宽
MAX_PEN_WIDTH = 3.6                  # 沉着慢笔最大笔宽
SMOOTH_FACTOR = 0.65                 # 贝塞尔中点平滑阻尼

# Key timing thresholds (ms)
DOUBLE_PRESS_INTERVAL_MS = 450       # 两次点击判定阈值 (Alt 或 ~)
MIN_PRESS_INTERVAL_MS = 80           # 防抖阈值
