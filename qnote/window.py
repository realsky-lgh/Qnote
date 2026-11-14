"""
Main Window & Interactive Note Sheet for Qnote
Frameless, translucent background, 10 artistic paper textures,
seamless double-tilde switching between text and master-level ink drawing,
immediate cursor focus, and smooth history browsing.
"""
import time
import json
from PyQt6.QtCore import Qt, QPoint, QRectF, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QTextEdit, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QMenu, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QKeyEvent, QMouseEvent,
    QCursor, QIcon, QAction
)

from .config import (
    DEFAULT_WIDTH, DEFAULT_HEIGHT, WINDOW_CORNER_RADIUS,
    DOUBLE_PRESS_INTERVAL_MS, MIN_PRESS_INTERVAL_MS
)
from .storage import NoteStorage
from .themes import THEMES, get_theme, PaperTheme
from .ink import InkEngine


class ToastLabel(QLabel):
    """Subtle floating badge to notify mode changes without interrupting writing."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 30, 35, 215);
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 500;
                padding: 6px 14px;
                border-radius: 12px;
            }
        """)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text: str, duration_ms: int = 1200):
        self.setText(text)
        self.adjustSize()
        if self.parent():
            parent_rect = self.parent().rect()
            self.move((parent_rect.width() - self.width()) // 2, parent_rect.height() - 55)
        self.show()
        self.raise_()
        self._timer.start(duration_ms)


class NoteTextEdit(QTextEdit):
    """
    Transparent Text Area that delegates double-tilde key presses
    back to the parent window for switching to drawing mode.
    """
    double_tilde_detected = pyqtSignal()
    save_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Transparent background so procedural paper texture shines through
        self.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                padding: 10px 18px;
                line-height: 1.6;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 4px 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(120, 120, 120, 0.25);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(120, 120, 120, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        font = QFont("Sans-Serif", 13)
        font.setStyleHint(QFont.StyleHint.SansSerif)
        self.setFont(font)

        self._last_tilde_time = 0.0
        self.textChanged.connect(self._on_text_changed)

        # Save debounce timer
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self.save_requested.emit)

    def _on_text_changed(self):
        self._save_timer.start()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        text = event.text()

        # Check for ~ or ` key for double-press toggle
        if text in ('`', '~') or key in (Qt.Key.Key_AsciiTilde, Qt.Key.Key_QuoteLeft):
            now = time.time()
            dt_ms = (now - self._last_tilde_time) * 1000.0
            if MIN_PRESS_INTERVAL_MS < dt_ms < DOUBLE_PRESS_INTERVAL_MS:
                self._last_tilde_time = 0.0
                # Remove the previously typed backtick if inserted
                cursor = self.textCursor()
                if not cursor.atStart():
                    cursor.deletePreviousChar()
                self.double_tilde_detected.emit()
                event.accept()
                return
            else:
                self._last_tilde_time = now

        super().keyPressEvent(event)


class NoteSheetWindow(QWidget):
    """
    The minimalist physical-feel paper sheet.
    """
    MODE_TEXT = 0
    MODE_DRAW = 1

    def __init__(self, storage: NoteStorage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.mode = self.MODE_TEXT
        
        self.current_note_id: int = 0
        self.current_theme: PaperTheme = get_theme(0)
        self.ink_engine = InkEngine()
        
        # Double-tilde tracking for drawing mode
        self._last_tilde_time = 0.0
        self._last_alt_window_time = 0.0
        
        # Mouse dragging the window
        self._drag_pos = None

        self._init_ui()
        self.load_or_create_initial_note()

    def _init_ui(self):
        # Frameless, on-top, translucent, tool window (floats above other apps)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)

        # Main Layout
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)

        # Paper Container Frame (for shadow and border)
        self.paper_frame = QFrame(self)
        self.paper_frame.setObjectName("paperFrame")
        
        # Drop shadow for float feel
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 8)
        self.paper_frame.setGraphicsEffect(shadow)

        paper_layout = QVBoxLayout(self.paper_frame)
        paper_layout.setContentsMargins(12, 8, 12, 12)
        paper_layout.setSpacing(4)

        # 1. Top Minimalist Header Toolbar
        self.header = self._build_header()
        paper_layout.addWidget(self.header)

        # 2. Text Editor Area
        self.editor = NoteTextEdit(self.paper_frame)
        self.editor.double_tilde_detected.connect(self.toggle_mode)
        self.editor.save_requested.connect(self.save_current_state)
        paper_layout.addWidget(self.editor, 1)

        root_layout.addWidget(self.paper_frame)

        # Toast notification
        self.toast = ToastLabel(self.paper_frame)

    def _build_header(self) -> QWidget:
        header = QWidget(self.paper_frame)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(6, 4, 6, 2)
        h_layout.setSpacing(8)

        # Drag handle / Brand icon
        self.lbl_title = QLabel("✦ Qnote", header)
        self.lbl_title.setStyleSheet("font-size: 13px; font-weight: 600; color: rgba(80,80,85,0.7);")
        h_layout.addWidget(self.lbl_title)

        # History pagination label (e.g. "1 / 5")
        self.lbl_history = QLabel("", header)
        self.lbl_history.setStyleSheet("font-size: 11px; color: rgba(120,120,125,0.6);")
        h_layout.addWidget(self.lbl_history)

        h_layout.addStretch()

        # Mode Indicator Button (⌨️ 文字 / 🎨 涂鸦)
        self.btn_mode = QPushButton("⌨️ 文字", header)
        self.btn_mode.setToolTip("按两次 ~ 键随时切换手绘画画与键盘输入")
        self.btn_mode.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode.setStyleSheet("""
            QPushButton {
                background: rgba(128, 128, 128, 0.12);
                border: none;
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 12px;
                color: #444;
            }
            QPushButton:hover {
                background: rgba(128, 128, 128, 0.22);
            }
        """)
        self.btn_mode.clicked.connect(self.toggle_mode)
        h_layout.addWidget(self.btn_mode)

        # 10 Papers Theme Picker Button
        self.btn_theme = QPushButton("📄 纸张", header)
        self.btn_theme.setToolTip("随心切换10款艺术与护眼纸张底纹 (快捷键: Ctrl+P)")
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.setStyleSheet("""
            QPushButton {
                background: rgba(128, 128, 128, 0.12);
                border: none;
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 12px;
                color: #444;
            }
            QPushButton:hover {
                background: rgba(128, 128, 128, 0.22);
            }
        """)
        self.btn_theme.clicked.connect(self.show_theme_menu)
        h_layout.addWidget(self.btn_theme)

        # Previous Page (Older) Button
        self.btn_prev = QPushButton("◀", header)
        self.btn_prev.setToolTip("翻看上一张历史速记 (PageUp)")
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.setFixedSize(24, 24)
        self.btn_prev.setStyleSheet("""
            QPushButton {
                background: rgba(128, 128, 128, 0.12);
                border: none;
                border-radius: 6px;
                font-size: 11px;
                color: #555;
            }
            QPushButton:hover { background: rgba(128, 128, 128, 0.22); }
        """)
        self.btn_prev.clicked.connect(self.nav_prev_note)
        h_layout.addWidget(self.btn_prev)

        # Next Page (Newer) Button
        self.btn_next = QPushButton("▶", header)
        self.btn_next.setToolTip("翻看下一张速记 (PageDown)")
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setFixedSize(24, 24)
        self.btn_next.setStyleSheet("""
            QPushButton {
                background: rgba(128, 128, 128, 0.12);
                border: none;
                border-radius: 6px;
                font-size: 11px;
                color: #555;
            }
            QPushButton:hover { background: rgba(128, 128, 128, 0.22); }
        """)
        self.btn_next.clicked.connect(self.nav_next_note)
        h_layout.addWidget(self.btn_next)

        # New Sheet Button
        self.btn_new = QPushButton("＋新纸", header)
        self.btn_new.setToolTip("随时换一张新纸开始速记 (Ctrl+N)")
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.setStyleSheet("""
            QPushButton {
                background: rgba(40, 160, 120, 0.16);
                border: 1px solid rgba(40, 160, 120, 0.3);
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 12px;
                font-weight: 600;
                color: #1F7A59;
            }
            QPushButton:hover {
                background: rgba(40, 160, 120, 0.28);
            }
        """)
        self.btn_new.clicked.connect(self.new_sheet)
        h_layout.addWidget(self.btn_new)

        # Close/Hide Button
        self.btn_close = QPushButton("✕", header)
        self.btn_close.setToolTip("收入口袋 / 隐藏 (Esc 或 双击Alt)")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                color: #888;
            }
            QPushButton:hover {
                background: rgba(220, 60, 60, 0.15);
                color: #C02020;
            }
        """)
        self.btn_close.clicked.connect(self.hide_paper)
        h_layout.addWidget(self.btn_close)

        return header

    def load_or_create_initial_note(self):
        """Loads latest active note or starts with a fresh warm ivory paper."""
        note = self.storage.get_or_create_current_note(default_theme_id=0)
        self.load_note_data(note)

    def load_note_data(self, note: dict):
        self.current_note_id = note["id"]
        self.current_theme = get_theme(note.get("theme_id", 0))
        
        # Text
        self.editor.blockSignals(True)
        self.editor.setPlainText(note.get("text_content", ""))
        self.editor.blockSignals(False)
        
        # Strokes
        strokes_json = note.get("strokes_data", "[]")
        try:
            strokes_list = json.loads(strokes_json)
        except Exception:
            strokes_list = []
        self.ink_engine.load_data(strokes_list)

        self.apply_theme(self.current_theme)
        self.update_pagination_label()
        self.paper_frame.update()

    def update_pagination_label(self):
        if not self.current_note_id:
            return
        pos, total = self.storage.get_note_position(self.current_note_id)
        self.lbl_history.setText(f"{pos}/{total}")
        
        # Update button states for visual feedback
        has_prev = pos > 1
        has_next = pos < total
        self.btn_prev.setEnabled(has_prev)
        self.btn_next.setEnabled(has_next)
        
        # Subtle opacity feedback when at boundary
        self.btn_prev.setStyleSheet(self._get_nav_btn_style(has_prev))
        self.btn_next.setStyleSheet(self._get_nav_btn_style(has_next))

    def _get_nav_btn_style(self, enabled: bool) -> str:
        is_dark = self.current_theme.is_dark
        if enabled:
            btn_bg = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.07)"
            btn_hover = "rgba(255, 255, 255, 0.22)" if is_dark else "rgba(0, 0, 0, 0.14)"
            btn_color = "#E0E0E0" if is_dark else "#333333"
        else:
            btn_bg = "transparent"
            btn_hover = "transparent"
            btn_color = "rgba(160, 160, 160, 0.35)"
            
        return f"""
            QPushButton {{
                background: {btn_bg};
                border: none;
                border-radius: 6px;
                font-size: 11px;
                color: {btn_color};
            }}
            QPushButton:hover {{
                background: {btn_hover};
            }}
        """

    def apply_theme(self, theme: PaperTheme):
        self.current_theme = theme
        
        # Update text editor font color & placeholder text
        is_dark = theme.is_dark
        text_hex = theme.text_color.name()
        placeholder_hex = theme.placeholder_color.name()
        
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                padding: 10px 18px;
                color: {text_hex};
                line-height: 1.6;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background: rgba({'200,200,200' if is_dark else '100,100,100'}, 0.25);
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba({'200,200,200' if is_dark else '100,100,100'}, 0.5);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        self.editor.setPlaceholderText("光标已就绪，立即随心速记...\n(按两次 ~ 键可切换为手绘线条涂鸦)")

        # Update header styles
        header_text_color = "rgba(220, 220, 230, 0.85)" if is_dark else "rgba(60, 60, 70, 0.75)"
        btn_bg = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.07)"
        btn_hover = "rgba(255, 255, 255, 0.22)" if is_dark else "rgba(0, 0, 0, 0.14)"
        btn_color = "#E0E0E0" if is_dark else "#333333"

        self.lbl_title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {header_text_color};")
        self.lbl_history.setStyleSheet(f"font-size: 11px; color: {'#999' if is_dark else '#777'};")
        
        for btn in (self.btn_mode, self.btn_theme):
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {btn_bg};
                    border: none;
                    border-radius: 6px;
                    padding: 3px 8px;
                    font-size: 12px;
                    color: {btn_color};
                }}
                QPushButton:hover {{
                    background: {btn_hover};
                }}
            """)

        self.update_pagination_label()
        self.paper_frame.update()

    def show_theme_menu(self):
        """Displays menu for the 10 artistic paper textures."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid rgba(0,0,0,0.12);
                border-radius: 8px;
                padding: 6px;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(0,0,0,0.06);
            }
        """)

        for th in THEMES:
            prefix = "✓ " if th.id == self.current_theme.id else "   "
            action = menu.addAction(f"{prefix}{th.name} — {th.desc}")
            action.triggered.connect(lambda checked, tid=th.id: self.select_theme(tid))

        self.btn_theme.mapToGlobal(QPoint(0, self.btn_theme.height()))
        menu.exec(self.btn_theme.mapToGlobal(QPoint(0, self.btn_theme.height() + 4)))

    def select_theme(self, theme_id: int):
        self.apply_theme(get_theme(theme_id))
        self.save_current_state()
        self.toast.show_message(f"底纹已换为: {self.current_theme.name}")

    def cycle_next_theme(self):
        next_id = (self.current_theme.id + 1) % len(THEMES)
        self.select_theme(next_id)

    def toggle_mode(self):
        """Switch between typing and master-level ink drawing."""
        if self.mode == self.MODE_TEXT:
            self.mode = self.MODE_DRAW
            self.btn_mode.setText("🎨 涂鸦")
            self.editor.clearFocus()
            self.editor.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.toast.show_message("🎨 涂鸦模式 (用鼠标丝滑画画，按两次 ~ 切回打字)")
        else:
            self.mode = self.MODE_TEXT
            self.btn_mode.setText("⌨️ 文字")
            self.editor.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            self.editor.setFocus()
            self.setCursor(Qt.CursorShape.IBeamCursor)
            self.toast.show_message("📝 键盘模式 (直接打字输入，按两次 ~ 切为画画)")
        self.paper_frame.update()

    def new_sheet(self):
        """Immediately save current sheet and present a fresh clean page."""
        self.save_current_state()
        new_id = self.storage.create_new_note(theme_id=self.current_theme.id)
        fresh_note = self.storage.get_note_by_id(new_id)
        self.load_note_data(fresh_note)
        
        # Reset to text mode and autofocus
        if self.mode == self.MODE_DRAW:
            self.toggle_mode()
        self.editor.setFocus()
        self.toast.show_message("✦ 已展开全新一页笔记纸")

    def nav_prev_note(self):
        """Go to previous (older) note."""
        self.save_current_state()
        prev_id = self.storage.get_adjacent_note_id(self.current_note_id, "prev")
        if prev_id:
            note = self.storage.get_note_by_id(prev_id)
            self.load_note_data(note)
            self.toast.show_message("◀ 翻至更早笔记")
        else:
            self.toast.show_message("已是第一页历史速记")

    def nav_next_note(self):
        """Go to next (newer) note."""
        self.save_current_state()
        next_id = self.storage.get_adjacent_note_id(self.current_note_id, "next")
        if next_id:
            note = self.storage.get_note_by_id(next_id)
            self.load_note_data(note)
            self.toast.show_message("▶ 翻至更新笔记")
        else:
            self.toast.show_message("已是最新一页 (可按＋新纸)")

    def save_current_state(self):
        if not self.current_note_id:
            return
        text = self.editor.toPlainText()
        strokes = self.ink_engine.export_data()
        self.storage.save_note(
            self.current_note_id,
            text_content=text,
            strokes=strokes,
            theme_id=self.current_theme.id
        )

    def show_paper(self):
        """Pops up the note paper, instantly ready for input."""
        self.setWindowState((self.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive)
        self.show()
        self.raise_()
        self.activateWindow()
        if self.mode == self.MODE_TEXT:
            self.editor.setFocus()
            # Move text cursor to the very end
            cursor = self.editor.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.editor.setTextCursor(cursor)

    def hide_paper(self):
        self.save_current_state()
        self.hide()

    def toggle_visibility(self):
        if self.isVisible() and self.isActiveWindow():
            self.hide_paper()
        else:
            self.show_paper()

    # --- Mouse & Drawing Events ---
    def mousePressEvent(self, event: QMouseEvent):
        # Window dragging on top header
        if event.button() == Qt.MouseButton.LeftButton:
            header_rect = self.header.rect()
            header_global = self.header.mapTo(self, QPoint(0, 0))
            if QRectF(header_global.x(), header_global.y(), header_rect.width(), header_rect.height()).contains(event.position()):
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return

        # Ink Drawing Mode
        if self.mode == self.MODE_DRAW:
            if event.button() == Qt.MouseButton.LeftButton:
                pos = event.position()
                # Use theme ink color (near black on light paper, moonlight white on dark slate)
                ink_color_hex = self.current_theme.ink_color.name()
                self.ink_engine.start_stroke(pos.x(), pos.y(), ink_color_hex)
                self.paper_frame.update()
                event.accept()
                return
            elif event.button() == Qt.MouseButton.RightButton:
                # Right click in draw mode to undo last stroke
                if self.ink_engine.undo():
                    self.paper_frame.update()
                    self.toast.show_message("↩ 已撤销上一笔画")
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        # Dragging window
        if self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return

        # Ink Drawing Mode
        if self.mode == self.MODE_DRAW and (event.buttons() & Qt.MouseButton.LeftButton):
            pos = event.position()
            dirty_rect = self.ink_engine.continue_stroke(pos.x(), pos.y())
            if dirty_rect:
                self.paper_frame.update(dirty_rect.toRect())
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
        if self.mode == self.MODE_DRAW and event.button() == Qt.MouseButton.LeftButton:
            self.ink_engine.end_stroke()
            self.save_current_state()
            self.paper_frame.update()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    # --- Keyboard Shortcuts on Window Level ---
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        text = event.text()
        modifiers = event.modifiers()

        # Check for ~ key in draw mode or window level to switch back to text mode
        if text in ('`', '~') or key in (Qt.Key.Key_AsciiTilde, Qt.Key.Key_QuoteLeft):
            now = time.time()
            dt_ms = (now - self._last_tilde_time) * 1000.0
            if MIN_PRESS_INTERVAL_MS < dt_ms < DOUBLE_PRESS_INTERVAL_MS:
                self._last_tilde_time = 0.0
                self.toggle_mode()
                event.accept()
                return
            else:
                self._last_tilde_time = now

        # Esc to hide, or Double Alt inside window to hide
        if key == Qt.Key.Key_Alt:
            now = time.time()
            dt_ms = (now - self._last_alt_window_time) * 1000.0
            if 60.0 <= dt_ms <= 550.0:
                self._last_alt_window_time = 0.0
                self.hide_paper()
                event.accept()
                return
            else:
                self._last_alt_window_time = now

        if key == Qt.Key.Key_Escape:
            self.hide_paper()
            event.accept()
            return

        # Ctrl+N -> New Sheet
        if (modifiers & Qt.KeyboardModifier.ControlModifier) and key == Qt.Key.Key_N:
            self.new_sheet()
            event.accept()
            return

        # Ctrl+P or Alt+P -> Cycle Theme
        if ((modifiers & Qt.KeyboardModifier.ControlModifier) or (modifiers & Qt.KeyboardModifier.AltModifier)) and key == Qt.Key.Key_P:
            self.cycle_next_theme()
            event.accept()
            return

        # Ctrl+Z in draw mode -> Undo
        if (modifiers & Qt.KeyboardModifier.ControlModifier) and key == Qt.Key.Key_Z:
            if self.mode == self.MODE_DRAW:
                if self.ink_engine.undo():
                    self.paper_frame.update()
                    self.save_current_state()
                event.accept()
                return

        # PageUp / PageDown for history navigation
        if key == Qt.Key.Key_PageUp:
            self.nav_prev_note()
            event.accept()
            return
        elif key == Qt.Key.Key_PageDown:
            self.nav_next_note()
            event.accept()
            return

        super().keyPressEvent(event)

    # --- Painting Paper Background & Silky Strokes ---
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Draw artistic paper background on the frame geometry
        frame_rect = QRectF(self.paper_frame.geometry())
        
        # Clip rounded rect
        painter.save()
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRoundedRect(frame_rect, WINDOW_CORNER_RADIUS, WINDOW_CORNER_RADIUS)
        painter.setClipPath(path)

        # 1. Procedural Theme Paper Texture
        self.current_theme.render_background(painter, frame_rect)

        # 2. Silky Ink Strokes (rendered over paper texture, under text edit or blended)
        self.ink_engine.render(painter, default_color=self.current_theme.ink_color)

        painter.restore()
