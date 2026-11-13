"""
Master-level Smooth Ink Drawing Engine for Qnote
Eliminates mouse jitter, uses Midpoint Quadratic Bezier Splines and dynamic velocity-based stroke width.
Produces silky, organic, burr-free ink lines like a master artist's sketching pen.
"""
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QPainterPath, QColor
import math
import time
from typing import List, Dict, Any, Optional
from .config import BASE_PEN_WIDTH, MIN_PEN_WIDTH, MAX_PEN_WIDTH

class StrokePoint:
    __slots__ = ('x', 'y', 'time', 'width')
    def __init__(self, x: float, y: float, t: float, width: float = BASE_PEN_WIDTH):
        self.x = x
        self.y = y
        self.time = t
        self.width = width

    def pos(self) -> QPointF:
        return QPointF(self.x, self.y)

class InkStroke:
    def __init__(self, color_hex: str = "#18181c"):
        self.points: List[StrokePoint] = []
        self.color_hex = color_hex
        self._path = QPainterPath()

    def add_point(self, x: float, y: float, t: float) -> Optional[QRectF]:
        """
        Adds point with jitter filtering and dynamic stroke calculation.
        Returns the dirty update rect for partial repainting.
        """
        if not self.points:
            pt = StrokePoint(x, y, t, BASE_PEN_WIDTH)
            self.points.append(pt)
            self._path.moveTo(pt.pos())
            return QRectF(x - 5, y - 5, 10, 10)

        prev = self.points[-1]
        dx = x - prev.x
        dy = y - prev.y
        dist = math.hypot(dx, dy)

        # 1. Jitter filter: discard sub-pixel micro tremors
        if dist < 2.0:
            return None

        # 2. Moving-average smoothing towards natural stroke path
        alpha = 0.65
        smoothed_x = prev.x * (1.0 - alpha) + x * alpha
        smoothed_y = prev.y * (1.0 - alpha) + y * alpha
        
        # 3. Velocity estimation & dynamic pen width
        dt = max(t - prev.time, 0.005)
        speed = dist / dt  # pixels per second
        
        # Fast stroke -> slightly thinner (graceful sweep); Slow stroke -> full ink
        # Normalize speed (0 to 1800 px/sec)
        norm_speed = min(speed / 1600.0, 1.0)
        target_width = MAX_PEN_WIDTH - norm_speed * (MAX_PEN_WIDTH - MIN_PEN_WIDTH)
        # Low pass filter on width transition
        curr_width = prev.width * 0.7 + target_width * 0.3

        curr = StrokePoint(smoothed_x, smoothed_y, t, curr_width)
        self.points.append(curr)

        # 4. Midpoint Quadratic Bezier Spline
        # When we have at least 2 points:
        # Segment starts from midpoint(prev-1, prev) to midpoint(prev, curr), control point is prev
        n = len(self.points)
        if n == 2:
            mid = QPointF((prev.x + curr.x) / 2.0, (prev.y + curr.y) / 2.0)
            self._path.lineTo(mid)
        else:
            prev_prev = self.points[-2]
            mid_start = QPointF((prev_prev.x + prev.x) / 2.0, (prev_prev.y + prev.y) / 2.0)
            mid_end = QPointF((prev.x + curr.x) / 2.0, (prev.y + curr.y) / 2.0)
            self._path.quadTo(prev.pos(), mid_end)

        margin = max(curr_width, prev.width) * 2.0 + 4.0
        min_x = min(prev.x, curr.x) - margin
        min_y = min(prev.y, curr.y) - margin
        max_x = max(prev.x, curr.x) + margin
        max_y = max(prev.y, curr.y) + margin
        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)

    def finish(self):
        """Finalize the last segment to the end point."""
        if len(self.points) > 1:
            last = self.points[-1]
            self._path.lineTo(last.pos())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "color": self.color_hex,
            "pts": [[round(p.x, 1), round(p.y, 1), round(p.width, 1)] for p in self.points]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InkStroke":
        stroke = cls(color_hex=data.get("color", "#18181c"))
        pts = data.get("pts", [])
        if not pts:
            return stroke

        t = 0.0
        for i, item in enumerate(pts):
            x, y = item[0], item[1]
            w = item[2] if len(item) > 2 else BASE_PEN_WIDTH
            p = StrokePoint(x, y, t, w)
            stroke.points.append(p)
            t += 0.01

        # Reconstruct path using Midpoint Bezier
        if len(stroke.points) == 1:
            p0 = stroke.points[0].pos()
            stroke._path.moveTo(p0)
            stroke._path.lineTo(p0)
        else:
            stroke._path.moveTo(stroke.points[0].pos())
            for i in range(1, len(stroke.points)):
                prev = stroke.points[i - 1]
                curr = stroke.points[i]
                if i == 1:
                    mid = QPointF((prev.x + curr.x) / 2.0, (prev.y + curr.y) / 2.0)
                    stroke._path.lineTo(mid)
                else:
                    prev_prev = stroke.points[i - 2]
                    mid_end = QPointF((prev.x + curr.x) / 2.0, (prev.y + curr.y) / 2.0)
                    stroke._path.quadTo(prev.pos(), mid_end)
            stroke._path.lineTo(stroke.points[-1].pos())

        return stroke


class InkEngine:
    def __init__(self):
        self.strokes: List[InkStroke] = []
        self.current_stroke: Optional[InkStroke] = None
        self.redo_stack: List[InkStroke] = []

    def start_stroke(self, x: float, y: float, color_hex: str):
        self.current_stroke = InkStroke(color_hex=color_hex)
        self.current_stroke.add_point(x, y, time.time())
        self.redo_stack.clear()

    def continue_stroke(self, x: float, y: float) -> Optional[QRectF]:
        if self.current_stroke:
            return self.current_stroke.add_point(x, y, time.time())
        return None

    def end_stroke(self):
        if self.current_stroke:
            self.current_stroke.finish()
            if len(self.current_stroke.points) > 0:
                self.strokes.append(self.current_stroke)
            self.current_stroke = None

    def undo(self) -> bool:
        if self.strokes:
            stroke = self.strokes.pop()
            self.redo_stack.append(stroke)
            return True
        return False

    def redo(self) -> bool:
        if self.redo_stack:
            stroke = self.redo_stack.pop()
            self.strokes.append(stroke)
            return True
        return False

    def clear(self):
        self.strokes.clear()
        self.redo_stack.clear()
        self.current_stroke = None

    def render(self, painter: QPainter, default_color: Optional[QColor] = None):
        """Render all strokes with high quality antialiasing and natural round joints."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        all_strokes = list(self.strokes)
        if self.current_stroke:
            all_strokes.append(self.current_stroke)

        for stroke in all_strokes:
            if not stroke.points:
                continue

            color = default_color if default_color is not None else QColor(stroke.color_hex)
            
            # If stroke has varying widths, render segmented quadratic beziers
            if len(stroke.points) > 2:
                for i in range(1, len(stroke.points)):
                    p_prev = stroke.points[i - 1]
                    p_curr = stroke.points[i]
                    w = (p_prev.width + p_curr.width) / 2.0
                    
                    pen = QPen(color, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    painter.setPen(pen)
                    
                    if i == 1:
                        mid = QPointF((p_prev.x + p_curr.x) / 2.0, (p_prev.y + p_curr.y) / 2.0)
                        painter.drawLine(p_prev.pos(), mid)
                    else:
                        p_prev_prev = stroke.points[i - 2]
                        mid_start = QPointF((p_prev_prev.x + p_prev.x) / 2.0, (p_prev_prev.y + p_prev.y) / 2.0)
                        mid_end = QPointF((p_prev.x + p_curr.x) / 2.0, (p_prev.y + p_curr.y) / 2.0)
                        path = QPainterPath()
                        path.moveTo(mid_start)
                        path.quadTo(p_prev.pos(), mid_end)
                        painter.drawPath(path)
                # Last segment to end point
                pen = QPen(color, stroke.points[-1].width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                painter.drawLine(stroke.points[-1].pos(), stroke.points[-1].pos())
            else:
                # Single point or 2 points
                w = stroke.points[0].width
                pen = QPen(color, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                painter.drawPath(stroke._path)

        painter.restore()

    def export_data(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self.strokes]

    def load_data(self, data: List[Dict[str, Any]]):
        self.clear()
        for item in data:
            self.strokes.append(InkStroke.from_dict(item))
