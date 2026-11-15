"""
Main Window & Interactive Note Sheet for Qnote
Frameless, translucent background, 10 artistic paper textures,
seamless double-tilde switching between text and master-level ink drawing,
immediate cursor focus, and smooth history browsing.
"""
import time
import json
from PyQt6.QtCore import Qt, QPoint, QRect, QRectF, QTimer, pyqtSignal, QEvent, QPointF, QSize
from PyQt6.QtWidgets import (
    QWidget, QTextEdit, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QMenu, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QKeyEvent, QMouseEvent,
    QCursor, QIcon, QAction, QPixmap, QPainterPath
)

from .config import (
    DEFAULT_WIDTH, DEFAULT_HEIGHT, MIN_WIDTH, MIN_HEIGHT, MAX_WIDTH, MAX_HEIGHT,
    WINDOW_CORNER_RADIUS, DOUBLE_PRESS_INTERVAL_MS, MIN_PRESS_INTERVAL_MS
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


def create_trash_icon(color: QColor, size: int = 16) -> QIcon:
    """Renders a crisp, anti-aliased minimalist trash can vector icon."""
    px_size = size * 2
    pm = QPixmap(px_size, px_size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    s = px_size / 32.0
    p.scale(s, s)

    pen = QPen(color, 2.2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    # Lid handle
    p.drawPolyline([QPointF(12.5, 7.5), QPointF(12.5, 5.5), QPointF(19.5, 5.5), QPointF(19.5, 7.5)])
    # Lid horizontal bar
    p.drawLine(QPointF(7.0, 7.5), QPointF(25.0, 7.5))

    # Bin body
    body = QPainterPath()
    body.moveTo(9.5, 9.5)
    body.lineTo(10.5, 23.5)
    body.quadTo(10.5, 26.0, 13.0, 26.0)
    body.lineTo(19.0, 26.0)
    body.quadTo(21.5, 26.0, 21.5, 23.5)
    body.lineTo(22.5, 9.5)
    p.drawPath(body)

    # Vertical slit accents
    p.drawLine(QPointF(13.5, 12.0), QPointF(13.5, 22.0))
    p.drawLine(QPointF(16.0, 12.0), QPointF(16.0, 22.0))
    p.drawLine(QPointF(18.5, 12.0), QPointF(18.5, 22.0))
    p.end()
    return QIcon(pm)


class TrashButton(QPushButton):
    """
    Minimalist floating trash can button placed at the bottom-right of each note sheet.
    Subtle watermark appearance by default; illuminates coral red on hover.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_dark = False
        self._hovered = False
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("删除当前速记 (Ctrl+D)")
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: rgba(220, 60, 60, 0.16);
            }
            QPushButton:pressed {
                background: rgba(220, 60, 60, 0.32);
            }
        """)
        self._refresh_icon()

    def set_dark_mode(self, is_dark: bool):
        self._is_dark = is_dark
        self._refresh_icon()

    def enterEvent(self, event):
        self._hovered = True
        self._refresh_icon()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._refresh_icon()
        super().leaveEvent(event)

    def _refresh_icon(self):
        if self._hovered:
            color = QColor(220, 60, 60, 230)
        elif self._is_dark:
            color = QColor(190, 190, 195, 120)
        else:
            color = QColor(110, 110, 115, 100)
        self.setIcon(create_trash_icon(color, 16))
        self.setIconSize(QSize(16, 16))


class CornerResizeGrip(QWidget):
    """
    Subtle tactile diagonal grip handle in the bottom-right corner of the note.
    Displays 3 minimalist diagonal ridges and allows dragging to resize the sheet.
    """
    def __init__(self, parent=None, window=None):
        super().__init__(parent)
        self.window_ref = window
        self._is_dark = False
        self._hovered = False
        self.setFixedSize(18, 18)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip("拖拽此角调整速记纸尺寸")

    def set_dark_mode(self, is_dark: bool):
        self._is_dark = is_dark
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.window_ref:
            self.window_ref._start_window_resize(
                Qt.Edge.BottomEdge | Qt.Edge.RightEdge,
                event.globalPosition().toPoint()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if (event.buttons() & Qt.MouseButton.LeftButton) and self.window_ref:
            self.window_ref._perform_window_resize(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.window_ref:
            self.window_ref._resizing_edges = None
            self.window_ref._persist_geometry()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._hovered:
            color = QColor(40, 40, 45, 180) if not self._is_dark else QColor(230, 230, 240, 200)
        else:
            color = QColor(120, 120, 125, 80) if not self._is_dark else QColor(180, 180, 190, 70)

        pen = QPen(color, 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)

        # 3 tactile diagonal ridges in the corner
        p.drawLine(QPointF(14, 6), QPointF(6, 14))
        p.drawLine(QPointF(14, 10), QPointF(10, 14))
        p.drawLine(QPointF(14, 14), QPointF(14, 14))
        p.end()


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
        
        # Mouse dragging & resizing the window
        self._drag_pos = None
        self._resizing_edges = None
        self._resize_start_pos = None
        self._resize_start_geo = None

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

        # Restore persistent window size or fall back to defaults
        saved_w = self.storage.get_setting("window_width")
        saved_h = self.storage.get_setting("window_height")
        if saved_w and saved_h:
            try:
                w = max(MIN_WIDTH, min(MAX_WIDTH, int(saved_w)))
                h = max(MIN_HEIGHT, min(MAX_HEIGHT, int(saved_h)))
                self.resize(w, h)
            except Exception:
                self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        else:
            self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)

        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)
        self.setMaximumSize(MAX_WIDTH, MAX_HEIGHT)
        self.setMouseTracking(True)

        # Main Layout
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)

        # Paper Container Frame (for shadow and border)
        self.paper_frame = QFrame(self)
        self.paper_frame.setObjectName("paperFrame")
        self.paper_frame.setMouseTracking(True)
        
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

        # 3. Corner Resize Grip & Floating Trash Can at Bottom-Right
        self.resize_grip = CornerResizeGrip(self.paper_frame, window=self)
        self.btn_delete = TrashButton(self.paper_frame)
        self.btn_delete.clicked.connect(self.delete_current_note)

        # Install event filters for smooth window dragging and border resizing
        self.header.installEventFilter(self)
        self.lbl_drag.installEventFilter(self)
        self.lbl_title.installEventFilter(self)
        self.lbl_history.installEventFilter(self)
        self.editor.installEventFilter(self)
        self.paper_frame.installEventFilter(self)

        # Toast notification
        self.toast = ToastLabel(self.paper_frame)
        self._update_bottom_right_widgets_pos()

    def _build_header(self) -> QWidget:
        header = QWidget(self.paper_frame)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(6, 4, 6, 2)
        h_layout.setSpacing(6)

        # Drag handle icon (visible affordance for window movement)
        self.lbl_drag = QLabel("⠿", header)
        self.lbl_drag.setToolTip("按住拖动速记纸位置 (也可按住标题栏任意空白拖动，或 Alt+鼠标左键任意拖动)")
        self.lbl_drag.setCursor(Qt.CursorShape.SizeAllCursor)
        self.lbl_drag.setStyleSheet("font-size: 15px; color: rgba(120, 120, 125, 0.45); padding: 0 1px;")
        h_layout.addWidget(self.lbl_drag)

        # Brand title
        self.lbl_title = QLabel("✦ Qnote", header)
        self.lbl_title.setToolTip("按住拖动速记纸")
        self.lbl_title.setCursor(Qt.CursorShape.SizeAllCursor)
        self.lbl_title.setStyleSheet("font-size: 13px; font-weight: 600; color: rgba(80,80,85,0.7);")
        h_layout.addWidget(self.lbl_title)

        # History pagination label (e.g. "1 / 5")
        self.lbl_history = QLabel("", header)
        self.lbl_history.setToolTip("当前页码 / 总页数")
        self.lbl_history.setCursor(Qt.CursorShape.SizeAllCursor)
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

        if hasattr(self, "btn_delete"):
            self.btn_delete.set_dark_mode(is_dark)
        if hasattr(self, "resize_grip"):
            self.resize_grip.set_dark_mode(is_dark)

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

    def delete_current_note(self):
        """Deletes the current note sheet and navigates to adjacent note or opens a fresh sheet."""
        if not self.current_note_id:
            return

        # Determine adjacent note before deleting
        target_id = self.storage.get_adjacent_note_id(self.current_note_id, "prev")
        if not target_id:
            target_id = self.storage.get_adjacent_note_id(self.current_note_id, "next")

        # Delete current note from database
        self.storage.delete_note(self.current_note_id)

        if target_id:
            next_note = self.storage.get_note_by_id(target_id)
            if next_note:
                self.load_note_data(next_note)
            else:
                self.load_or_create_initial_note()
        else:
            # If all notes deleted, create and load a fresh empty sheet
            new_id = self.storage.create_new_note(theme_id=self.current_theme.id)
            fresh_note = self.storage.get_note_by_id(new_id)
            self.load_note_data(fresh_note)

        # Focus editor if in text mode
        if self.mode == self.MODE_TEXT:
            self.editor.setFocus()

        self.toast.show_message("🗑 已删除当前笔记")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_bottom_right_widgets_pos()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_bottom_right_widgets_pos()

    def _update_bottom_right_widgets_pos(self):
        if not hasattr(self, "paper_frame"):
            return
        fw = self.paper_frame.width()
        fh = self.paper_frame.height()

        # 1. Corner resize grip in the corner
        if hasattr(self, "resize_grip"):
            gw = self.resize_grip.width()
            gh = self.resize_grip.height()
            self.resize_grip.move(fw - gw - 3, fh - gh - 3)
            self.resize_grip.raise_()

        # 2. Trash can button adjacent to resize grip
        if hasattr(self, "btn_delete"):
            bw = self.btn_delete.width()
            bh = self.btn_delete.height()
            self.btn_delete.move(fw - bw - 24, fh - bh - 6)
            self.btn_delete.raise_()

    _update_delete_button_pos = _update_bottom_right_widgets_pos

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
        self._persist_geometry()
        self.hide()

    def toggle_visibility(self):
        if self.isVisible() and self.isActiveWindow():
            self.hide_paper()
        else:
            self.show_paper()

    def _determine_edges(self, pos: QPoint) -> Qt.Edge:
        """Determines which window border/corner the point is hovering on."""
        margin = 18
        x = pos.x()
        y = pos.y()
        w = self.width()
        h = self.height()

        edges = Qt.Edge(0)
        if y <= margin:
            edges |= Qt.Edge.TopEdge
        elif y >= h - margin:
            edges |= Qt.Edge.BottomEdge

        if x <= margin:
            edges |= Qt.Edge.LeftEdge
        elif x >= w - margin:
            edges |= Qt.Edge.RightEdge

        return edges

    def _cursor_for_edges(self, edges: Qt.Edge) -> Qt.CursorShape:
        is_top = bool(edges & Qt.Edge.TopEdge)
        is_bottom = bool(edges & Qt.Edge.BottomEdge)
        is_left = bool(edges & Qt.Edge.LeftEdge)
        is_right = bool(edges & Qt.Edge.RightEdge)

        if (is_top and is_left) or (is_bottom and is_right):
            return Qt.CursorShape.SizeFDiagCursor
        if (is_top and is_right) or (is_bottom and is_left):
            return Qt.CursorShape.SizeBDiagCursor
        if is_left or is_right:
            return Qt.CursorShape.SizeHorCursor
        if is_top or is_bottom:
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    def _start_window_resize(self, edges: Qt.Edge, global_pos: QPoint):
        """Starts smooth window resizing, prioritizing compositor-level native resize."""
        handle = self.windowHandle()
        if handle and hasattr(handle, "startSystemResize"):
            if handle.startSystemResize(edges):
                self._resizing_edges = None
                return

        # Client-side fallback
        self._resizing_edges = edges
        self._resize_start_pos = global_pos
        self._resize_start_geo = self.geometry()

    def _perform_window_resize(self, global_pos: QPoint):
        """Client-side resize logic when system resize is not supported."""
        if not self._resizing_edges or not self._resize_start_geo:
            return

        delta = global_pos - self._resize_start_pos
        orig = self._resize_start_geo
        new_left = orig.left()
        new_top = orig.top()
        new_right = orig.right()
        new_bottom = orig.bottom()

        if self._resizing_edges & Qt.Edge.RightEdge:
            new_w = max(MIN_WIDTH, min(MAX_WIDTH, orig.width() + delta.x()))
            new_right = orig.left() + new_w - 1
        elif self._resizing_edges & Qt.Edge.LeftEdge:
            new_w = max(MIN_WIDTH, min(MAX_WIDTH, orig.width() - delta.x()))
            new_left = orig.right() - new_w + 1

        if self._resizing_edges & Qt.Edge.BottomEdge:
            new_h = max(MIN_HEIGHT, min(MAX_HEIGHT, orig.height() + delta.y()))
            new_bottom = orig.top() + new_h - 1
        elif self._resizing_edges & Qt.Edge.TopEdge:
            new_h = max(MIN_HEIGHT, min(MAX_HEIGHT, orig.height() - delta.y()))
            new_top = orig.bottom() - new_h + 1

        self.setGeometry(QRect(QPoint(new_left, new_top), QPoint(new_right, new_bottom)))

    def _persist_geometry(self):
        """Saves resized window dimensions to persistent storage."""
        try:
            self.storage.set_setting("window_width", str(self.width()))
            self.storage.set_setting("window_height", str(self.height()))
        except Exception:
            pass

    def _start_window_drag(self, global_pos: QPoint):
        """Starts smooth window dragging, prioritizing native Wayland/Windows compositor drag."""
        handle = self.windowHandle()
        if handle and hasattr(handle, "startSystemMove") and handle.startSystemMove():
            self._drag_pos = None
            return
        self._drag_pos = global_pos - self.frameGeometry().topLeft()

    def _perform_window_drag(self, global_pos: QPoint):
        """Perform client-side drag when system move is unavailable."""
        if self._drag_pos is not None:
            self.move(global_pos - self._drag_pos)

    def eventFilter(self, obj, event):
        """Intercept mouse drag events on header, title, and labels, plus border resizing."""
        # 1. Border resize check for child widgets (paper_frame, editor, header)
        if obj in (self.paper_frame, self.header, self.editor):
            if event.type() in (QEvent.Type.MouseMove, QEvent.Type.HoverMove):
                if self._resizing_edges is not None:
                    self._perform_window_resize(event.globalPosition().toPoint())
                    return True
                if self.mode != self.MODE_DRAW:
                    win_pos = self.mapFromGlobal(event.globalPosition().toPoint())
                    edges = self._determine_edges(win_pos)
                    if edges != Qt.Edge(0):
                        self.setCursor(self._cursor_for_edges(edges))
                    else:
                        if obj == self.editor:
                            self.setCursor(Qt.CursorShape.IBeamCursor)
                        elif obj in (self.header, self.lbl_title, self.lbl_drag):
                            self.setCursor(Qt.CursorShape.SizeAllCursor)
                        else:
                            self.setCursor(Qt.CursorShape.ArrowCursor)

            elif event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                win_pos = self.mapFromGlobal(event.globalPosition().toPoint())
                edges = self._determine_edges(win_pos)
                if edges != Qt.Edge(0):
                    self._start_window_resize(edges, event.globalPosition().toPoint())
                    return True

            elif event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                if self._resizing_edges is not None:
                    self._resizing_edges = None
                    self._persist_geometry()
                    return True

        # 2. Header drag events for window movement
        if obj in (self.header, self.lbl_drag, self.lbl_title, self.lbl_history):
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._start_window_drag(event.globalPosition().toPoint())
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                if event.buttons() & Qt.MouseButton.LeftButton:
                    self._perform_window_drag(event.globalPosition().toPoint())
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._drag_pos = None
                    return True

        # Alt + Left Click anywhere on the text editor allows moving the sheet
        if obj == self.editor:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                    self._start_window_drag(event.globalPosition().toPoint())
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                if self._drag_pos is not None and (event.buttons() & Qt.MouseButton.LeftButton):
                    self._perform_window_drag(event.globalPosition().toPoint())
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if self._drag_pos is not None and event.button() == Qt.MouseButton.LeftButton:
                    self._drag_pos = None
                    return True

        return super().eventFilter(obj, event)

    # --- Mouse & Drawing Events ---
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check window border resizing
            edges = self._determine_edges(event.position().toPoint())
            if edges != Qt.Edge(0):
                self._start_window_resize(edges, event.globalPosition().toPoint())
                event.accept()
                return

            # Window dragging if clicked on top header or if Alt key held
            header_rect = self.header.rect()
            header_global = self.header.mapTo(self, QPoint(0, 0))
            in_header = QRectF(header_global.x(), header_global.y(), header_rect.width(), header_rect.height()).contains(event.position())
            alt_held = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
            if in_header or alt_held:
                self._start_window_drag(event.globalPosition().toPoint())
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
        # Resizing window
        if self._resizing_edges is not None:
            self._perform_window_resize(event.globalPosition().toPoint())
            event.accept()
            return

        # Dragging window
        if self._drag_pos is not None:
            self._perform_window_drag(event.globalPosition().toPoint())
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

        # Update hover cursor for borders
        if self.mode != self.MODE_DRAW:
            edges = self._determine_edges(event.position().toPoint())
            if edges != Qt.Edge(0):
                self.setCursor(self._cursor_for_edges(edges))
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._resizing_edges is not None:
            self._resizing_edges = None
            self._persist_geometry()

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

        # Ctrl+D -> Delete Current Note
        if (modifiers & Qt.KeyboardModifier.ControlModifier) and key == Qt.Key.Key_D:
            self.delete_current_note()
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
