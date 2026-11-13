"""
10 Artistic and Eye-Friendly Paper Themes for Qnote
Curated color palettes and procedural textures designed for maximum eye comfort and artistic feel.
"""
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient, QFont
from PyQt6.QtCore import Qt, QRectF, QPointF
import math

class PaperTheme:
    def __init__(
        self,
        theme_id: int,
        name: str,
        desc: str,
        bg_color: str,
        text_color: str,
        ink_color: str,
        placeholder_color: str,
        accent_color: str,
        is_dark: bool = False
    ):
        self.id = theme_id
        self.name = name
        self.desc = desc
        self.bg_color = QColor(bg_color)
        self.text_color = QColor(text_color)
        self.ink_color = QColor(ink_color)
        self.placeholder_color = QColor(placeholder_color)
        self.accent_color = QColor(accent_color)
        self.is_dark = is_dark

    def render_background(self, painter: QPainter, rect: QRectF):
        """Draw the artistic paper background and texture."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # 1. Base solid paper color
        painter.fillRect(rect, self.bg_color)
        
        # 2. Specific artistic procedural texture
        self._render_texture(painter, rect)
        
        # 3. Soft vignette / border shade
        self._render_vignette(painter, rect)
        
        painter.restore()

    def _render_texture(self, painter: QPainter, rect: QRectF):
        pass

    def _render_vignette(self, painter: QPainter, rect: QRectF):
        # Subtle vignette to give realistic paper edge depth
        vignette_color = QColor(0, 0, 0, 10 if not self.is_dark else 25)
        pen = QPen(vignette_color, 1.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 16, 16)


# 1. 暖玉柔光 (Warm Ivory) - 极佳护眼色温，漫反射柔和微光
class WarmIvoryTheme(PaperTheme):
    def __init__(self):
        super().__init__(
            0, "暖玉柔光", "3800K温润柔光，漫反射低蓝光刺激",
            "#FAF7EE", "#232326", "#161619", "#9E9B91", "#C7B99D"
        )
    def _render_texture(self, painter: QPainter, rect: QRectF):
        # Delicate warm gradient
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor(255, 252, 245, 100))
        grad.setColorAt(1.0, QColor(245, 240, 228, 80))
        painter.fillRect(rect, grad)


# 2. 复古羊皮卷 (Aged Parchment) - 手稿典雅与微泛黄岁月暗角
class ParchmentTheme(PaperTheme):
    def __init__(self):
        super().__init__(
            1, "复古羊皮卷", "古典欧洲羊皮手卷，温厚泛黄暗角",
            "#F4EBD2", "#2B261D", "#1C1710", "#9B8F77", "#A98E5E"
        )
    def _render_texture(self, painter: QPainter, rect: QRectF):
        # Radial vignette for aged parchment feel
        center = rect.center()
        radius = max(rect.width(), rect.height()) * 0.75
        radial = QRadialGradient(center, radius)
        radial.setColorAt(0.0, QColor(250, 243, 226, 40))
        radial.setColorAt(0.7, QColor(238, 222, 190, 80))
        radial.setColorAt(1.0, QColor(215, 195, 156, 140))
        painter.fillRect(rect, radial)


# 3. 东方生宣 (Calligraphy Xuan) - 传统宣纸微透与温润墨韵
class XuanPaperTheme(PaperTheme):
    def __init__(self):
        super().__init__(
            2, "东方生宣", "安徽宣纸韵味，微润质感与墨色深沉",
            "#F8F5EE", "#1F2022", "#121314", "#8F8D87", "#8A948D"
        )
    def _render_texture(self, painter: QPainter, rect: QRectF):
        # Soft subtle fiber mist
        grad = QLinearGradient(0, rect.top(), 0, rect.bottom())
        grad.setColorAt(0.0, QColor(255, 255, 255, 60))
        grad.setColorAt(0.5, QColor(245, 241, 233, 40))
        grad.setColorAt(1.0, QColor(240, 234, 222, 80))
        painter.fillRect(rect, grad)


# 4. 日式和纸 (Japanese Washi) - 轻盈天然构树纤维肌理
class WashiTheme(PaperTheme):
    def __init__(self):
        super().__init__(
            3, "日式和纸", "天然和纸纤维肌理，极简禅意温润",
            "#F5F3EC", "#262522", "#181715", "#99968E", "#8F7D6B"
        )
    def _render_texture(self, painter: QPainter, rect: QRectF):
        # Procedural subtle fiber dashes
        pen = QPen(QColor(180, 172, 155, 30), 1)
        painter.setPen(pen)
        # Deterministic scattered fiber accents
        for i in range(15):
            y = (i * 47) % int(rect.height())
            x = (i * 83) % int(rect.width() - 50)
            painter.drawLine(QPointF(x, y), QPointF(x + 18, y + 2))


# 5. 手作牛皮纸 (Artisan Kraft) - 粗粝温润的工坊卡其纸
class KraftPaperTheme(PaperTheme):
    def __init__(self):
        super().__init__(
            4, "手作牛皮纸", "工坊质朴暖金牛皮纸，灵感速写首选",
            "#E8DCBE", "#2A2318", "#17120B", "#8C7D64", "#9C6F3B"
        )
    def _render_texture(self, painter: QPainter, rect: QRectF):
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor(242, 232, 206, 60))
        grad.setColorAt(1.0, QColor(218, 201, 168, 80))
        painter.fillRect(rect, grad)


# 6. 极简点阵纸 (Dot Grid) - 现代草稿与手账标配
class DotGridTheme(PaperTheme):
    def __init__(self):
        super().__init__(
            5, "极简点阵纸", "22px隐形淡灰圆点阵列，排版绘图两相宜",
            "#F9F9F8", "#222326", "#141416", "#A0A0A5", "#5E81AC"
        )
    def _render_texture(self, painter: QPainter, rect: QRectF):
        step = 22.0
        dot_color = QColor(190, 190, 195, 120)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(dot_color))
        
        start_y = rect.top() + 45.0
        start_x = rect.left() + 20.0
        y = start_y
        while y < rect.bottom() - 15:
            x = start_x
            while x < rect.right() - 15:
                painter.drawEllipse(QPointF(x, y), 1.0, 1.0)
                x += step
            y += step


# 7. 薄荷晨曦 (Morning Mint) - 莫兰迪淡青绿方格，深度解眼疲劳
class MorningMintTheme(PaperTheme):
    def __init__(self):
        super().__init__(
            6, "薄荷晨曦", "清晨淡薄荷浅青绿，5mm舒目微方格",
            "#EEF4F0", "#1C2721", "#0F1A14", "#8B9E93", "#4E876B"
        )
    def _render_texture(self, painter: QPainter, rect: QRectF):
        # Delicate grid
        grid_pen = QPen(QColor(180, 205, 190, 75), 0.8)
        painter.setPen(grid_pen)
        step = 20.0
        start_y = rect.top() + 40.0
        y = start_y
        while y < rect.bottom() - 10:
            painter.drawLine(QPointF(rect.left() + 15, y), QPointF(rect.right() - 15, y))
            y += step
        x = rect.left() + 15.0
        while x < rect.right() - 15:
            painter.drawLine(QPointF(x, start_y), QPointF(x, rect.bottom() - 10))
            x += step


# 8. 冷压水彩纸 (Cold-Pressed Watercolor) - 棉浆微浮雕凹凸颗粒质感
class WatercolorTheme(PaperTheme):
    def __init__(self):
        super().__init__(
            7, "冷压水彩纸", "手工棉浆凹凸压纹颗粒，画画有真实阻尼感",
            "#F9F6F0", "#242321", "#151413", "#9C978D", "#D4A373"
        )
    def _render_texture(self, painter: QPainter, rect: QRectF):
        # Watercolor grain feel via two layered subtle linear gradients
        grad1 = QLinearGradient(0, rect.top(), 0, rect.bottom())
        grad1.setColorAt(0.0, QColor(255, 253, 248, 80))
        grad1.setColorAt(1.0, QColor(240, 235, 224, 70))
        painter.fillRect(rect, grad1)
        
        # Subtle horizontal pressure bars
        pen = QPen(QColor(210, 202, 190, 25), 1.5)
        painter.setPen(pen)
        for i in range(12):
            y = rect.top() + 50 + i * 40
            if y < rect.bottom() - 20:
                painter.drawLine(QPointF(rect.left() + 15, y), QPointF(rect.right() - 15, y))


# 9. 复古打字机信纸 (Vintage Typewriter) - 经典蓝红信笺横线
class TypewriterTheme(PaperTheme):
    def __init__(self):
        super().__init__(
            8, "打字机信笺", "复古横线信笺与淡红页边距线，诗意排版",
            "#FAF7F0", "#262320", "#181512", "#9C958A", "#C25953"
        )
    def _render_texture(self, painter: QPainter, rect: QRectF):
        # Left margin line (soft red)
        margin_x = rect.left() + 52.0
        red_pen = QPen(QColor(220, 110, 110, 75), 1.2)
        painter.setPen(red_pen)
        painter.drawLine(QPointF(margin_x, rect.top() + 42), QPointF(margin_x, rect.bottom() - 15))
        
        # Horizontal ledger lines (soft blue/grey)
        line_pen = QPen(QColor(170, 190, 210, 70), 0.9)
        painter.setPen(line_pen)
        step = 28.0
        y = rect.top() + 68.0
        while y < rect.bottom() - 15:
            painter.drawLine(QPointF(rect.left() + 18, y), QPointF(rect.right() - 18, y))
            y += step


# 10. 竹炭墨石 (Charcoal Slate - 暗夜模式) - 极夜深灰碳素石板
class CharcoalSlateTheme(PaperTheme):
    def __init__(self):
        super().__init__(
            9, "竹炭墨石", "深灰竹炭石板极夜护眼，非刺眼死黑，配月影白墨",
            "#202227", "#E4E6EB", "#F2F4F8", "#6D717E", "#7289DA",
            is_dark=True
        )
    def _render_texture(self, painter: QPainter, rect: QRectF):
        # Subtle slate gradient
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor(38, 41, 48, 120))
        grad.setColorAt(1.0, QColor(26, 28, 33, 160))
        painter.fillRect(rect, grad)


# All 10 Themes Registry
THEMES = [
    WarmIvoryTheme(),
    ParchmentTheme(),
    XuanPaperTheme(),
    WashiTheme(),
    KraftPaperTheme(),
    DotGridTheme(),
    MorningMintTheme(),
    WatercolorTheme(),
    TypewriterTheme(),
    CharcoalSlateTheme(),
]

def get_theme(theme_id: int) -> PaperTheme:
    if 0 <= theme_id < len(THEMES):
        return THEMES[theme_id]
    return THEMES[0]
