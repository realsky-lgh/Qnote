"""
Qnote - 极简速记纸
"""
from .app import QnoteApplication
from .autostart import enable_autostart, disable_autostart, is_autostart_enabled

__all__ = ["QnoteApplication", "enable_autostart", "disable_autostart", "is_autostart_enabled"]
