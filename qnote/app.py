"""
Qnote Application Lifecycle, System Tray, and Hotkey Orchestration
"""
import sys
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu
)
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush
from PyQt6.QtCore import Qt

from .config import APP_TITLE, APP_VERSION
from .storage import NoteStorage
from .window import NoteSheetWindow
from .hotkey import GlobalHotkeyManager
from .single_instance import SingleInstanceManager
from .autostart import is_autostart_enabled, set_autostart

def create_tray_icon() -> QIcon:
    """Generate a clean, high-DPI minimalist quill/paper tray icon procedurally."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # Mini paper page with folded corner
    painter.setBrush(QBrush(QColor(248, 245, 235)))
    painter.setPen(QPen(QColor(60, 60, 65, 220), 3))
    painter.drawRoundedRect(12, 10, 40, 44, 6, 6)

    # Subtle text lines
    painter.setPen(QPen(QColor(140, 140, 145, 180), 2.5))
    painter.drawLine(20, 24, 38, 24)
    painter.drawLine(20, 32, 44, 32)
    painter.drawLine(20, 40, 32, 40)

    # Accent ink dot
    painter.setBrush(QBrush(QColor(30, 144, 255)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(40, 40, 5, 5)

    painter.end()
    return QIcon(pixmap)


class QnoteApplication:
    def __init__(self, sys_argv):
        self.app = QApplication(sys_argv)
        self.app.setApplicationName("Qnote")
        self.app.setApplicationVersion(APP_VERSION)
        self.app.setQuitOnLastWindowClosed(False)

        self.silent = any(arg in ("--silent", "-s", "--background", "--daemon") for arg in sys_argv)

        # 1. Single instance check
        self.instance_mgr = SingleInstanceManager()
        if len(sys_argv) > 1 and sys_argv[1] in ("--toggle", "-t", "toggle"):
            if self.instance_mgr.try_connect_existing("toggle"):
                print("[Qnote] Sent toggle command to running instance.")
                sys.exit(0)
            else:
                self.silent = False
        elif self.silent:
            if self.instance_mgr.try_connect_existing("ping"):
                print("[Qnote] Qnote is already running in background.")
                sys.exit(0)
        else:
            # Check if an instance is already running
            if self.instance_mgr.try_connect_existing("toggle"):
                print("[Qnote] Qnote is already running. Brought window to front.")
                sys.exit(0)

        self.instance_mgr.start_listening()
        self.instance_mgr.message_received.connect(self._on_ipc_message)

        # 2. Database Storage
        self.storage = NoteStorage()

        # 3. Floating Note Sheet Window
        self.window = NoteSheetWindow(self.storage)

        # 4. System Tray Icon
        self.tray_icon = None
        self._init_tray()

        # 5. Global Alt Double-Press Hotkey Manager
        self.hotkey_mgr = GlobalHotkeyManager()
        self.hotkey_mgr.toggle_requested.connect(self.window.toggle_visibility)
        self.hotkey_mgr.start()

    def _init_tray(self):
        icon = create_tray_icon()
        self.app.setWindowIcon(icon)

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(icon, self.app)
            self.tray_icon.setToolTip("Qnote 极简速记纸 (双击 Alt 呼出)")

            menu = QMenu()
            menu.setStyleSheet("""
                QMenu {
                    background-color: #FFFFFF;
                    border: 1px solid rgba(0,0,0,0.12);
                    border-radius: 8px;
                    padding: 4px;
                    font-size: 13px;
                }
                QMenu::item {
                    padding: 6px 18px;
                    border-radius: 4px;
                }
                QMenu::item:selected {
                    background-color: rgba(0,0,0,0.06);
                }
            """)

            action_show = menu.addAction("✦ 呼出速记纸 (双击 Alt)")
            action_show.triggered.connect(self.window.show_paper)

            action_new = menu.addAction("＋ 换一张新纸 (Ctrl+N)")
            action_new.triggered.connect(self.window.new_sheet)

            action_cycle = menu.addAction("📄 切换纸张底纹 (Ctrl+P)")
            action_cycle.triggered.connect(self.window.cycle_next_theme)

            menu.addSeparator()

            # Autostart toggle option
            action_autostart = menu.addAction("开机自动启动")
            action_autostart.setCheckable(True)
            action_autostart.setChecked(is_autostart_enabled())
            action_autostart.toggled.connect(self._on_autostart_toggled)

            menu.addSeparator()

            action_quit = menu.addAction("✕ 退出 Qnote")
            action_quit.triggered.connect(self.quit)

            self.tray_icon.setContextMenu(menu)
            self.tray_icon.activated.connect(self._on_tray_activated)
            self.tray_icon.show()

    def _on_autostart_toggled(self, checked: bool):
        set_autostart(checked)

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.window.toggle_visibility()

    def _on_ipc_message(self, message: str):
        if message == "toggle":
            self.window.toggle_visibility()
        elif message == "show":
            self.window.show_paper()
        elif message == "new":
            self.window.new_sheet()

    def run(self):
        # Center the sheet initially
        screen_geo = self.app.primaryScreen().availableGeometry()
        x = (screen_geo.width() - self.window.width()) // 2
        y = max(40, (screen_geo.height() - self.window.height()) // 3)
        self.window.move(x, y)
        
        # If launched on startup (--silent), do not popup window immediately
        if not self.silent:
            self.window.show_paper()

        ret = self.app.exec()
        self.hotkey_mgr.stop()
        return ret

    def quit(self):
        self.window.save_current_state()
        self.hotkey_mgr.stop()
        self.app.quit()
