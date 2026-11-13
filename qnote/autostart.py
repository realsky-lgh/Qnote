"""
Cross-Platform Autostart Manager for Qnote
Supports Linux (XDG Autostart ~/.config/autostart/qnote.desktop)
and Windows (Registry HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run).
"""
import sys
import os
from pathlib import Path

def get_exec_path() -> str:
    """Returns the most appropriate command to launch Qnote silently."""
    # Check if ~/.local/bin/qnote exists on Linux
    if sys.platform != "win32":
        local_bin = Path.home() / ".local" / "bin" / "qnote"
        if local_bin.exists():
            return f"{local_bin} --silent"
        
        # Check binary in dist
        dist_bin = Path(__file__).resolve().parent.parent / "dist" / "qnote-linux-x86_64"
        if dist_bin.exists():
            return f"{dist_bin} --silent"
            
        # Fallback to python script
        main_py = Path(__file__).resolve().parent.parent / "main.py"
        return f"{sys.executable} {main_py} --silent"
    else:
        # Windows
        dist_exe = Path(__file__).resolve().parent.parent / "dist" / "Qnote.exe"
        if dist_exe.exists():
            return f'"{dist_exe}" --silent'
        main_py = Path(__file__).resolve().parent.parent / "main.py"
        return f'pythonw "{main_py}" --silent'


def get_linux_autostart_file() -> Path:
    autostart_dir = Path.home() / ".config" / "autostart"
    autostart_dir.mkdir(parents=True, exist_ok=True)
    return autostart_dir / "qnote.desktop"


def is_autostart_enabled() -> bool:
    """Check if autostart is currently enabled."""
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(key, "Qnote")
                return True
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False
    else:
        desktop_file = get_linux_autostart_file()
        return desktop_file.exists()


def enable_autostart() -> bool:
    """Enable launch on startup."""
    exec_cmd = get_exec_path()
    
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "Qnote", 0, winreg.REG_SZ, exec_cmd)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"[Qnote Autostart] Error enabling on Windows: {e}")
            return False
    else:
        try:
            desktop_file = get_linux_autostart_file()
            content = f"""[Desktop Entry]
Type=Application
Name=Qnote 速记纸
Comment=极简速记纸：双击Alt呼出，双击~切换手绘与文字，10款艺术护眼底纹
Exec={exec_cmd}
Icon=accessories-text-editor
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""
            desktop_file.write_text(content, encoding="utf-8")
            desktop_file.chmod(0o755)
            return True
        except Exception as e:
            print(f"[Qnote Autostart] Error enabling on Linux: {e}")
            return False


def disable_autostart() -> bool:
    """Disable launch on startup."""
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            try:
                winreg.DeleteValue(key, "Qnote")
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"[Qnote Autostart] Error disabling on Windows: {e}")
            return False
    else:
        try:
            desktop_file = get_linux_autostart_file()
            if desktop_file.exists():
                desktop_file.unlink()
            return True
        except Exception as e:
            print(f"[Qnote Autostart] Error disabling on Linux: {e}")
            return False


def set_autostart(enabled: bool) -> bool:
    if enabled:
        return enable_autostart()
    else:
        return disable_autostart()
