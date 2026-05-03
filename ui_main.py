import os
import sys
import math
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime, QTimer
from PyQt6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QPen
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import commands


DEBUG_SERIAL = False
from database import TestDatabase


ACCENT = "#00bdca"

DARK_BG = "#1e1e1e"
LIGHT_BG = "#ffffff"

DARK_PANEL = "#1e1e1e"
LIGHT_PANEL = "#F3F4F6"

DARK_TEXT = "#ffffff"
LIGHT_TEXT = "#000000"


def resource_path(relative_path: str) -> str:
    """Path for read-only bundled assets (inside the exe / script folder)."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)


def data_path(relative_path: str) -> str:
    """Path for writable user data (next to the exe, or next to the script in dev)."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base, relative_path)


class ToggleSwitch(QFrame):
    toggled = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setFixedSize(50, 24)
        self._circle_pos = 2
        self._is_dark = False
        self._icon_font = QFont("Segoe UI Emoji", 10)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        track_color = QColor("#555") if self._is_dark else QColor("#00bfff")
        painter.setBrush(track_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)

        painter.setBrush(QColor("#111213"))
        painter.drawEllipse(self._circle_pos, 2, 20, 20)

        icon = "🌙" if self._is_dark else "☀"
        painter.setFont(self._icon_font)
        painter.setPen(QColor("#d0d0d0"))
        painter.drawText(self._circle_pos, 2, 20, 20, Qt.AlignmentFlag.AlignCenter, icon)

    def mousePressEvent(self, event):
        self.toggled.emit(not self._is_dark)

    def set_state(self, dark: bool):
        self._is_dark = dark
        self._circle_pos = 28 if dark else 2
        self.update()


class GraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._dark = False
        self._degrees = []
        self._joules = []
        self._time_ms = []
        self._test_started = False
        self._initial_energy = None
        self._parent_window = parent
        self._graph_mode = "angle"
        self._start_time_ms = None

    def set_theme(self, dark: bool):
        self._dark = dark
        self.update()
    
    def set_graph_mode(self, mode: str):
        self._graph_mode = mode
        self.update()

    def set_data_point(self, x_value: float, y_value: float, is_end: bool = False):
        if abs(y_value - 6.30) < 0.1:
            return
        
        if not self._test_started:
            self._test_started = True
            self._initial_energy = y_value
            from PyQt6.QtCore import QTime
            self._start_time_ms = QTime.currentTime().msecsSinceStartOfDay()
        
        self._degrees.append(float(x_value))
        self._joules.append(float(y_value))
        
        from PyQt6.QtCore import QTime
        current_time_ms = QTime.currentTime().msecsSinceStartOfDay()
        elapsed_ms = current_time_ms - self._start_time_ms if self._start_time_ms else 0
        self._time_ms.append(elapsed_ms)
        
        self.update()
        
        if is_end:
            self._finalize_test()
    
    def _finalize_test(self):
        if self._parent_window and hasattr(self._parent_window, '_save_test'):
            self._parent_window._save_test()

    def clear(self):
        self._degrees.clear()
        self._joules.clear()
        self._time_ms.clear()
        self._test_started = False
        self._initial_energy = None
        self._start_time_ms = None
        self.update()

    def set_series(self, degrees: list[float], joules: list[float]):
        try:
            self._degrees = [float(x) for x in (degrees or [])]
            self._joules = [float(y) for y in (joules or [])]
            self._time_ms = list(range(0, len(self._degrees) * 100, 100)) if self._degrees else []
        except Exception:
            self._degrees = []
            self._joules = []
            self._time_ms = []
        self._test_started = len(self._degrees) > 0
        self._initial_energy = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg = QColor(DARK_BG) if self._dark else QColor(LIGHT_BG)
        painter.fillRect(self.rect(), bg)

        w = self.width()
        h = self.height()
        if w <= 10 or h <= 10:
            return

        plot_rect = self.rect().adjusted(80, 26, -26, -58)

        grid_color = QColor(255, 255, 255, 18) if self._dark else QColor(0, 0, 0, 25)
        axis_color = QColor(255, 255, 255, 60) if self._dark else QColor(0, 0, 0, 90)
        label_color = QColor(210, 210, 210) if self._dark else QColor(60, 60, 60)

        painter.setPen(QPen(grid_color, 0.5))
        grid_v = 8
        grid_h = 6
        for i in range(1, grid_v):
            x = plot_rect.left() + int(plot_rect.width() * i / grid_v)
            painter.drawLine(x, plot_rect.top(), x, plot_rect.bottom())
        for i in range(1, grid_h):
            y = plot_rect.top() + int(plot_rect.height() * i / grid_h)
            painter.drawLine(plot_rect.left(), y, plot_rect.right(), y)

        painter.setPen(QPen(axis_color, 1))

        painter.setPen(QPen(axis_color, 1))
        painter.drawLine(plot_rect.bottomLeft(), plot_rect.bottomRight())
        painter.drawLine(plot_rect.bottomLeft(), plot_rect.topLeft())

        painter.setPen(QPen(label_color, 1))
        painter.setFont(QFont("Segoe UI", 9))
        
        if self._graph_mode == "time":
            x_label = "Time (ms)"
            x_data = self._time_ms
        else:
            x_label = "Degree"
            x_data = self._degrees
        
        painter.drawText(plot_rect.center().x() - 18, self.rect().bottom() - 10, x_label)
        painter.save()
        painter.translate(18, plot_rect.center().y() + 18)
        painter.rotate(-90)
        painter.drawText(0, 0, "Joules")
        painter.restore()

        if len(x_data) < 2 or len(self._joules) < 2:
            return

        pen = QPen(QColor(ACCENT), 2)
        painter.setPen(pen)

        min_x = min(x_data)
        max_x = max(x_data)
        min_y = min(self._joules)
        max_y = max(self._joules)

        if max_x - min_x < 1e-9:
            max_x = min_x + 1.0
        if max_y - min_y < 1e-9:
            max_y = min_y + 1.0

        ticks = 5
        painter.setPen(QPen(label_color, 1))
        painter.setFont(QFont("Segoe UI", 8))
        for i in range(ticks + 1):
            tx = min_x + (max_x - min_x) * i / ticks
            x = plot_rect.left() + (plot_rect.width() * i / ticks)
            painter.drawLine(int(x), plot_rect.bottom(), int(x), plot_rect.bottom() + 4)
            painter.drawText(int(x) - 18, plot_rect.bottom() + 18, f"{tx:.2f}")
        for i in range(ticks + 1):
            ty = min_y + (max_y - min_y) * i / ticks
            y = plot_rect.bottom() - (plot_rect.height() * i / ticks)
            painter.drawLine(plot_rect.left() - 4, int(y), plot_rect.left(), int(y))
            painter.drawText(plot_rect.left() - 68, int(y) + 4, f"{ty:.2f}")

        def map_x(x: float) -> float:
            return plot_rect.left() + (x - min_x) * plot_rect.width() / (max_x - min_x)

        def map_y(y: float) -> float:
            return plot_rect.bottom() - (y - min_y) * plot_rect.height() / (max_y - min_y)

        prev_x = map_x(x_data[0])
        prev_y = map_y(self._joules[0])
        for idx in range(1, len(x_data)):
            x = map_x(x_data[idx])
            y = map_y(self._joules[idx])
            painter.drawLine(int(prev_x), int(prev_y), int(x), int(y))
            prev_x, prev_y = x, y


class ComparisonGraphWidget(QWidget):
    SERIES_COLORS = [
        "#00bdca", "#ff6b6b", "#ffd93d", "#6bcb77",
        "#4d96ff", "#c77dff", "#ff9a3c",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._dark = False
        self._series = []
        self._graph_mode = "angle"

    def set_theme(self, dark: bool):
        self._dark = dark
        self.update()

    def set_graph_mode(self, mode: str):
        self._graph_mode = mode
        self.update()

    def set_all_series(self, series_list: list):
        self._series = []
        for i, (label, degrees, joules) in enumerate(series_list):
            color = self.SERIES_COLORS[i % len(self.SERIES_COLORS)]
            self._series.append((label, list(degrees), list(joules), color))
        self.update()

    def clear(self):
        self._series = []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg = QColor(DARK_BG) if self._dark else QColor(LIGHT_BG)
        painter.fillRect(self.rect(), bg)

        w = self.width()
        h = self.height()
        if w <= 10 or h <= 10:
            return

        legend_w = 170 if self._series else 0
        plot_rect = self.rect().adjusted(80, 26, -10 - legend_w, -58)

        grid_color = QColor(255, 255, 255, 18) if self._dark else QColor(0, 0, 0, 25)
        axis_color = QColor(255, 255, 255, 60) if self._dark else QColor(0, 0, 0, 90)
        label_color = QColor(210, 210, 210) if self._dark else QColor(60, 60, 60)

        painter.setPen(QPen(grid_color, 0.5))
        for i in range(1, 8):
            x = plot_rect.left() + int(plot_rect.width() * i / 8)
            painter.drawLine(x, plot_rect.top(), x, plot_rect.bottom())
        for i in range(1, 6):
            y = plot_rect.top() + int(plot_rect.height() * i / 6)
            painter.drawLine(plot_rect.left(), y, plot_rect.right(), y)

        painter.setPen(QPen(axis_color, 1))
        painter.drawLine(plot_rect.bottomLeft(), plot_rect.bottomRight())
        painter.drawLine(plot_rect.bottomLeft(), plot_rect.topLeft())

        painter.setPen(QPen(label_color, 1))
        painter.setFont(QFont("Segoe UI", 9))
        x_label = "Time (ms)" if self._graph_mode == "time" else "Degree"
        painter.drawText(plot_rect.center().x() - 18, self.rect().bottom() - 10, x_label)
        painter.save()
        painter.translate(18, plot_rect.center().y() + 18)
        painter.rotate(-90)
        painter.drawText(0, 0, "Joules")
        painter.restore()

        if not self._series:
            painter.setPen(QPen(label_color, 1))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(plot_rect, Qt.AlignmentFlag.AlignCenter, "No tests loaded for comparison")
            return

        all_x, all_y = [], []
        for label, degrees, joules, color in self._series:
            xd = list(range(0, len(degrees) * 100, 100)) if self._graph_mode == "time" else degrees
            all_x.extend(xd)
            all_y.extend(joules)

        if not all_x or not all_y:
            return

        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        if max_x - min_x < 1e-9:
            max_x = min_x + 1.0
        if max_y - min_y < 1e-9:
            max_y = min_y + 1.0

        ticks = 5
        painter.setPen(QPen(label_color, 1))
        painter.setFont(QFont("Segoe UI", 8))
        for i in range(ticks + 1):
            tx = min_x + (max_x - min_x) * i / ticks
            x = plot_rect.left() + (plot_rect.width() * i / ticks)
            painter.drawLine(int(x), plot_rect.bottom(), int(x), plot_rect.bottom() + 4)
            painter.drawText(int(x) - 18, plot_rect.bottom() + 18, f"{tx:.2f}")
        for i in range(ticks + 1):
            ty = min_y + (max_y - min_y) * i / ticks
            y = plot_rect.bottom() - (plot_rect.height() * i / ticks)
            painter.drawLine(plot_rect.left() - 4, int(y), plot_rect.left(), int(y))
            painter.drawText(plot_rect.left() - 68, int(y) + 4, f"{ty:.2f}")

        def map_x(xv):
            return plot_rect.left() + (xv - min_x) * plot_rect.width() / (max_x - min_x)

        def map_y(yv):
            return plot_rect.bottom() - (yv - min_y) * plot_rect.height() / (max_y - min_y)

        for label, degrees, joules, color in self._series:
            if len(degrees) < 2 or len(joules) < 2:
                continue
            xd = list(range(0, len(degrees) * 100, 100)) if self._graph_mode == "time" else degrees
            painter.setPen(QPen(QColor(color), 2))
            px, py = map_x(xd[0]), map_y(joules[0])
            for idx in range(1, len(xd)):
                cx, cy = map_x(xd[idx]), map_y(joules[idx])
                painter.drawLine(int(px), int(py), int(cx), int(cy))
                px, py = cx, cy

        if legend_w > 0:
            leg_x = plot_rect.right() + 14
            leg_y = plot_rect.top()
            painter.setFont(QFont("Segoe UI", 8))
            for i, (label, _, _, color) in enumerate(self._series):
                sy = leg_y + i * 24
                painter.setBrush(QColor(color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(leg_x, sy + 1, 16, 10, 3, 3)
                painter.setPen(QPen(label_color, 1))
                disp = label if len(label) <= 18 else label[:16] + ".."
                painter.drawText(leg_x + 22, sy, legend_w - 26, 14,
                                 Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, disp)


class SettingsDialog(QDialog):
    def __init__(
        self,
        current_graph_mode: str = "angle",
        company_name: str = "",
        company_logo_path: str = "",
        is_dark: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setFixedSize(700, 440)

        self.selected_graph_mode = current_graph_mode
        self.company_name = company_name
        self.company_logo_path = company_logo_path
        self._is_dark = is_dark

        bg        = "#1e1e1e" if is_dark else "#ffffff"
        sidebar_bg = "#171718" if is_dark else "#f3f4f6"
        text      = "#ffffff" if is_dark else "#111827"
        muted     = "#9CA3AF" if is_dark else "#6B7280"
        border    = "rgba(255,255,255,0.10)" if is_dark else "rgba(0,0,0,0.08)"
        input_bg  = "#252526" if is_dark else "#ffffff"
        input_bdr = "1px solid rgba(255,255,255,0.10)" if is_dark else "1px solid rgba(0,0,0,0.10)"

        self.setStyleSheet(
            f"QDialog {{ background-color: {bg}; border-radius: 14px; "
            f"border: 1px solid {border}; }}"
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- SIDEBAR ----
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(
            f"QFrame {{ background-color: {sidebar_bg}; "
            f"border-right: 1px solid {border}; "
            "border-top-left-radius: 14px; border-bottom-left-radius: 14px; }}"
        )
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(12, 20, 12, 20)
        sb_layout.setSpacing(4)

        sb_title = QLabel("Settings")
        sb_title.setStyleSheet(
            f"color: {text}; font-size: 15px; font-weight: 800; "
            "padding: 0 6px 14px 6px; background: transparent;"
        )
        sb_layout.addWidget(sb_title)

        self._nav_btns: dict[str, QPushButton] = {}
        nav_items = [("graph", "Graph Display Mode"), ("company", "Company Details")]
        nav_active  = f"background-color: {'rgba(0,189,202,0.18)' if is_dark else 'rgba(0,189,202,0.13)'}; color: {ACCENT};"
        nav_normal  = f"background-color: transparent; color: {muted};"
        nav_hover   = f"background-color: {'rgba(255,255,255,0.06)' if is_dark else 'rgba(0,0,0,0.05)'}; color: {text};"
        nav_style   = (
            "QPushButton {{ border: none; border-radius: 8px; padding: 9px 12px; "
            "font-size: 12px; font-weight: 600; text-align: left; {state} }}"
            "QPushButton:hover {{ {hover} }}"
        )
        for key, label in nav_items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda _, k=key: self._switch_section(k))
            btn.setStyleSheet(
                f"QPushButton {{ border: none; border-radius: 8px; padding: 9px 12px; "
                f"font-size: 12px; font-weight: 600; text-align: left; {nav_normal} }}"
                f"QPushButton:checked {{ {nav_active} }}"
                f"QPushButton:hover {{ {nav_hover} }}"
            )
            sb_layout.addWidget(btn)
            self._nav_btns[key] = btn

        sb_layout.addStretch()
        root.addWidget(sidebar)

        # ---- RIGHT PANEL ----
        right = QFrame()
        right.setStyleSheet(
            f"QFrame {{ background-color: {bg}; "
            "border-top-right-radius: 14px; border-bottom-right-radius: 14px; }}"
        )
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Custom title bar with macOS red close
        tbar = QFrame()
        tbar.setFixedHeight(46)
        tbar.setStyleSheet("background: transparent;")
        tbar_l = QHBoxLayout(tbar)
        tbar_l.setContentsMargins(16, 14, 16, 0)
        tbar_l.addStretch()
        close_btn = QPushButton()
        close_btn.setFixedSize(14, 14)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet(
            "QPushButton { background-color: #FF5F57; border: none; border-radius: 7px; }"
            "QPushButton:hover { background-color: #e0524a; }"
        )
        close_btn.clicked.connect(self.reject)
        tbar_l.addWidget(close_btn)
        right_layout.addWidget(tbar)

        # Content stack
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background: transparent;")
        right_layout.addWidget(self.content_stack, 1)

        # --- Graph page ---
        graph_page = QWidget()
        graph_page.setStyleSheet("background: transparent;")
        gp_l = QVBoxLayout(graph_page)
        gp_l.setContentsMargins(28, 0, 28, 16)
        gp_l.setSpacing(10)
        gp_title = QLabel("Graph Display Mode")
        gp_title.setStyleSheet(f"color: {text}; font-size: 14px; font-weight: 700;")
        gp_l.addWidget(gp_title)
        gp_desc = QLabel("Choose how the graph X-axis is displayed.")
        gp_desc.setStyleSheet(f"color: {muted}; font-size: 11px;")
        gp_l.addWidget(gp_desc)
        self.radio_angle = QRadioButton("Energy vs Angle")
        self.radio_time  = QRadioButton("Energy vs Time (ms)")
        for rb in (self.radio_angle, self.radio_time):
            rb.setStyleSheet(
                f"QRadioButton {{ color: {text}; font-size: 12px; padding: 6px 2px; background: transparent; }}"
                f"QRadioButton::indicator {{ width: 16px; height: 16px; }}"
            )
        if current_graph_mode == "angle":
            self.radio_angle.setChecked(True)
        else:
            self.radio_time.setChecked(True)
        gp_l.addWidget(self.radio_angle)
        gp_l.addWidget(self.radio_time)
        gp_l.addStretch()
        self.content_stack.addWidget(graph_page)

        # --- Company details page ---
        co_page = QWidget()
        co_page.setStyleSheet("background: transparent;")
        co_l = QVBoxLayout(co_page)
        co_l.setContentsMargins(28, 0, 28, 16)
        co_l.setSpacing(10)
        co_title = QLabel("Company Details")
        co_title.setStyleSheet(f"color: {text}; font-size: 14px; font-weight: 700;")
        co_l.addWidget(co_title)
        co_desc = QLabel("These will appear on all printed reports.")
        co_desc.setStyleSheet(f"color: {muted}; font-size: 11px;")
        co_l.addWidget(co_desc)

        lbl_name = QLabel("Company Name")
        lbl_name.setStyleSheet(f"color: {text}; font-size: 11px; font-weight: 700; margin-top: 4px;")
        co_l.addWidget(lbl_name)
        self.txt_company_name = QLineEdit()
        self.txt_company_name.setPlaceholderText("Enter company name…")
        self.txt_company_name.setText(company_name)
        self.txt_company_name.setFixedHeight(36)
        self.txt_company_name.setStyleSheet(
            f"QLineEdit {{ background-color: {input_bg}; color: {text}; border: {input_bdr}; "
            f"border-radius: 10px; padding: 0 12px; font-size: 12px; }}"
            f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
        )
        co_l.addWidget(self.txt_company_name)

        lbl_logo = QLabel("Company Logo")
        lbl_logo.setStyleSheet(f"color: {text}; font-size: 11px; font-weight: 700; margin-top: 4px;")
        co_l.addWidget(lbl_logo)

        logo_row = QWidget()
        logo_row.setStyleSheet("background: transparent;")
        logo_row_l = QHBoxLayout(logo_row)
        logo_row_l.setContentsMargins(0, 0, 0, 0)
        logo_row_l.setSpacing(8)
        self.txt_logo_path = QLineEdit()
        self.txt_logo_path.setPlaceholderText("No logo selected")
        self.txt_logo_path.setText(company_logo_path)
        self.txt_logo_path.setReadOnly(True)
        self.txt_logo_path.setFixedHeight(36)
        self.txt_logo_path.setStyleSheet(
            f"QLineEdit {{ background-color: {input_bg}; color: {text}; border: {input_bdr}; "
            "border-radius: 10px; padding: 0 12px; font-size: 11px; }}"
        )
        logo_row_l.addWidget(self.txt_logo_path, 1)

        btn_brw = QPushButton("Browse…")
        btn_brw.setFixedSize(78, 36)
        btn_brw.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        _brw_bg = "#2d2d2d" if is_dark else "#E5E7EB"
        _brw_tx = "#ffffff" if is_dark else "#374151"
        btn_brw.setStyleSheet(
            f"QPushButton {{ background-color: {_brw_bg}; color: {_brw_tx}; "
            "border: none; border-radius: 10px; font-size: 11px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {'#3d3d3d' if is_dark else '#D1D5DB'}; }}"
        )
        btn_brw.clicked.connect(self._on_browse_logo)
        logo_row_l.addWidget(btn_brw)
        co_l.addWidget(logo_row)

        fmt_lbl = QLabel("Supported: PNG, JPG, JPEG, BMP, GIF, WEBP, SVG, ICO")
        fmt_lbl.setStyleSheet(f"color: {muted}; font-size: 10px;")
        co_l.addWidget(fmt_lbl)
        co_l.addStretch()
        self.content_stack.addWidget(co_page)

        # ---- Bottom button bar ----
        bbar = QFrame()
        bbar.setStyleSheet(f"background: transparent; border-top: 1px solid {border};")
        bbar_l = QHBoxLayout(bbar)
        bbar_l.setContentsMargins(20, 12, 20, 14)
        bbar_l.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedSize(90, 32)
        btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        _sec_bg = "#2d2d2d" if is_dark else "#E5E7EB"
        _sec_tx = "#ffffff" if is_dark else "#374151"
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background-color: {_sec_bg}; color: {_sec_tx}; "
            "border: none; border-radius: 8px; font-size: 12px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {'#3d3d3d' if is_dark else '#D1D5DB'}; }}"
        )
        btn_cancel.clicked.connect(self.reject)
        bbar_l.addWidget(btn_cancel)

        btn_apply = QPushButton("Apply")
        btn_apply.setFixedSize(90, 32)
        btn_apply.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_apply.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT}; color: #000000; "
            "border: none; border-radius: 8px; font-size: 12px; font-weight: 600; }}"
            "QPushButton:hover { background-color: #00a8b5; }"
        )
        btn_apply.clicked.connect(self._on_apply)
        bbar_l.addWidget(btn_apply)
        right_layout.addWidget(bbar)

        root.addWidget(right, 1)

        self._switch_section("graph")

    def _switch_section(self, key: str):
        idx_map = {"graph": 0, "company": 1}
        self.content_stack.setCurrentIndex(idx_map.get(key, 0))
        for k, btn in self._nav_btns.items():
            btn.setChecked(k == key)

    def _on_browse_logo(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Company Logo", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.svg *.ico);;All Files (*)",
        )
        if path:
            self.txt_logo_path.setText(path)

    def _on_apply(self):
        self.selected_graph_mode = "angle" if self.radio_angle.isChecked() else "time"
        self.company_name = self.txt_company_name.text().strip()
        self.company_logo_path = self.txt_logo_path.text().strip()
        self.accept()


class LoadTestDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.selected_test_id = None
        
        self.setWindowTitle("Load Test Data")
        self.setModal(True)
        self.resize(800, 500)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("Select a Test to Load")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Sr No", "Test ID", "Test Name", "Date", "Time"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 180)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 120)
        
        layout.addWidget(self.table)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self._load_tests()
    
    def _load_tests(self):
        tests = self.db.get_all_tests()
        self.table.setRowCount(len(tests))
        
        for row, test in enumerate(tests):
            sr_no, test_id, test_name, date, time, timestamp = test
            
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.table.setItem(row, 1, QTableWidgetItem(test_id))
            self.table.setItem(row, 2, QTableWidgetItem(test_name))
            self.table.setItem(row, 3, QTableWidgetItem(date))
            self.table.setItem(row, 4, QTableWidgetItem(time))
    
    def _on_accept(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            test_id_item = self.table.item(row, 1)
            if test_id_item:
                self.selected_test_id = test_id_item.text()
                self.accept()
        else:
            self.reject()


class MultiLoadTestsDialog(QDialog):
    def __init__(self, db, selected_test_ids: list[str] | None = None, parent=None, max_select: int = 7, is_dark: bool = False):
        super().__init__(parent)
        self.db = db
        self.max_select = max_select
        self.selected_test_ids: list[str] = list(selected_test_ids or [])

        self.setWindowTitle("Load Tests")
        self.setModal(True)
        self.resize(900, 520)

        bg   = "#1e1e1e" if is_dark else "#ffffff"
        text = "#ffffff" if is_dark else "#111827"
        muted = "#9CA3AF" if is_dark else "#6B7280"
        tbl_bg = "#252526" if is_dark else "#ffffff"
        hdr_bg = "#171718" if is_dark else "#f3f4f6"
        sel_bg = "rgba(0,189,202,0.18)" if is_dark else "rgba(0,189,202,0.12)"
        border = "rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.08)"
        btn_bg = "#2d2d2d" if is_dark else "#E5E7EB"
        btn_tx = "#ffffff" if is_dark else "#374151"

        self.setStyleSheet(f"QDialog {{ background-color: {bg}; color: {text}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        title = QLabel(f"Select up to {self.max_select} tests")
        title.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {text}; margin-bottom: 4px;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["", "Sr No", "Test ID", "Test Name", "Date", "Time"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setColumnWidth(0, 48)
        self.table.setColumnWidth(1, 60)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 240)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 100)
        self.table.setStyleSheet(
            f"QTableWidget {{ background-color: {tbl_bg}; color: {text}; "
            f"gridline-color: transparent; border: 1px solid {border}; border-radius: 10px; }}"
            f"QTableWidget::item {{ padding: 6px 8px; border-bottom: 1px solid {border}; }}"
            f"QTableWidget::item:selected {{ background-color: {sel_bg}; color: {text}; }}"
            f"QHeaderView::section {{ background-color: {hdr_bg}; color: {muted}; "
            f"font-size: 11px; font-weight: 700; padding: 8px; border: none; "
            f"border-bottom: 1px solid {border}; }}"
        )
        layout.addWidget(self.table)

        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent;")
        btn_row_l = QHBoxLayout(btn_row)
        btn_row_l.setContentsMargins(0, 0, 0, 0)
        btn_row_l.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedSize(88, 32)
        btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background-color: {btn_bg}; color: {btn_tx}; "
            "border: none; border-radius: 8px; font-size: 12px; font-weight: 600; }}"
        )
        btn_cancel.clicked.connect(self.reject)
        btn_row_l.addWidget(btn_cancel)

        btn_ok = QPushButton("OK")
        btn_ok.setFixedSize(88, 32)
        btn_ok.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_ok.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT}; color: #000000; "
            "border: none; border-radius: 8px; font-size: 12px; font-weight: 600; }}"
            "QPushButton:hover { background-color: #00a8b5; }"
        )
        btn_ok.clicked.connect(self._on_accept)
        btn_row_l.addWidget(btn_ok)
        layout.addWidget(btn_row)

        self._is_updating = False
        self._load_tests()
        self.table.itemChanged.connect(self._on_item_changed)

    def _load_tests(self):
        tests = self.db.get_all_tests()
        self.table.setRowCount(len(tests))

        self._is_updating = True
        try:
            for row, test in enumerate(tests):
                _sr_no, test_id, test_name, date, time, _timestamp = test

                sel_item = QTableWidgetItem()
                sel_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                sel_item.setCheckState(
                    Qt.CheckState.Checked if test_id in self.selected_test_ids else Qt.CheckState.Unchecked
                )
                sel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 0, sel_item)

                for col, val in enumerate([str(row + 1), test_id, test_name, date, time], start=1):
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                    self.table.setItem(row, col, item)
        finally:
            self._is_updating = False

    def _on_item_changed(self, item: QTableWidgetItem):
        if self._is_updating:
            return
        if item.column() != 0:
            return

        test_id_item = self.table.item(item.row(), 2)
        if test_id_item is None:
            return
        test_id = test_id_item.text()

        checked_ids = []
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            tid_it = self.table.item(r, 2)
            if it is None or tid_it is None:
                continue
            if it.checkState() == Qt.CheckState.Checked:
                checked_ids.append(tid_it.text())

        if len(checked_ids) > self.max_select:
            self._is_updating = True
            try:
                item.setCheckState(Qt.CheckState.Unchecked)
            finally:
                self._is_updating = False
            return

        self.selected_test_ids = checked_ids

    def _on_accept(self):
        checked_ids = []
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            tid_it = self.table.item(r, 2)
            if it is None or tid_it is None:
                continue
            if it.checkState() == Qt.CheckState.Checked:
                checked_ids.append(tid_it.text())
        self.selected_test_ids = checked_ids[: self.max_select]
        self.accept()


class IzodMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("Izod")
        self.setWindowIcon(QIcon(resource_path("hexa_logo.ico")))
        self.resize(1600, 900)

        self.is_dark_theme = False
        self._serial = None
        self._serial_send_timer = None
        self._set_retry_timer = None
        self._rx_buffer = bytearray()
        self._pending_set_expected_parts = None
        self._pending_set_cmd = None
        self._pending_set_retries_left = 0

        self._comparison_active = False
        self._comparison_selected_test_ids: list[str] = []
        self._graph_mode = "angle"
        
        self.db = TestDatabase(db_path=data_path("izod_tests.db"))
        self.current_test_id = None
        self.test_in_progress = False
        self.is_loaded_test = False
        self.test_completed = False
        self.editable_controls = []
        self._company_name = self.db.get_setting("company_name", "")
        self._company_logo_path = self.db.get_setting("company_logo_path", "")

        central = QWidget()
        self.setCentralWidget(central)
        self._main_layout = QVBoxLayout(central)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self._main_layout.addWidget(self._create_title_bar())
        self._main_layout.addWidget(self._create_header())
        self._main_layout.addWidget(self._create_body(), 1)
        self._main_layout.addWidget(self._create_status_bar())

        self._apply_light_theme()
        self.theme_toggle.set_state(False)
        self._update_export_button_state()

        self._set_retry_timer = QTimer(self)
        self._set_retry_timer.setInterval(100)
        self._set_retry_timer.timeout.connect(self._tick_set_retry)

    def _create_title_bar(self):
        title_frame = QFrame()
        title_frame.setFixedHeight(34)
        self.title_bar = title_frame

        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(10, 0, 10, 0)
        title_layout.setSpacing(8)

        close_btn = QPushButton()
        close_btn.setFixedSize(14, 14)
        close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #FF5F57;
                border: none;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: #FF5F57CC;
            }
            """
        )
        close_btn.clicked.connect(self.close)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        min_btn = QPushButton()
        min_btn.setFixedSize(14, 14)
        min_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #FFBD2E;
                border: none;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: #FFBD2ECC;
            }
            """
        )
        min_btn.clicked.connect(self.showMinimized)
        min_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        max_btn = QPushButton()
        max_btn.setFixedSize(14, 14)
        max_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #28C940;
                border: none;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: #28C940CC;
            }
            """
        )
        max_btn.clicked.connect(self._toggle_maximize)
        max_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        title_layout.addWidget(close_btn)
        title_layout.addWidget(min_btn)
        title_layout.addWidget(max_btn)
        title_layout.addStretch()

        self._drag_pos = None

        def mousePressEvent(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

        def mouseMoveEvent(event):
            if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
                self.move(event.globalPosition().toPoint() - self._drag_pos)

        def mouseReleaseEvent(event):
            self._drag_pos = None

        title_frame.mousePressEvent = mousePressEvent
        title_frame.mouseMoveEvent = mouseMoveEvent
        title_frame.mouseReleaseEvent = mouseReleaseEvent

        return title_frame

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _create_header(self):
        header = QFrame()
        header.setFixedHeight(75)
        self.header_frame = header

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 2, 14, 2)
        header_layout.setSpacing(10)

        logo_container = QWidget()
        logo_container.setMinimumWidth(180)
        logo_container.setMinimumHeight(75)
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)

        self.logo_widget = QSvgWidget(resource_path("hexaplast_logo_gray.svg"))
        self.logo_widget.setFixedSize(175, 70)
        logo_layout.addWidget(self.logo_widget)

        header_layout.addWidget(logo_container, 0)

        title_sep = QLabel("|")
        title_sep.setObjectName("appSep")
        title_sep.setStyleSheet("font-size: 20px; font-weight: 600;")
        header_layout.addWidget(title_sep, 0, Qt.AlignmentFlag.AlignVCenter)

        title_lbl = QLabel("IZOD")
        title_lbl.setObjectName("appTitle")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: 800; letter-spacing: 1.2px;")
        header_layout.addWidget(title_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        header_layout.addStretch()

        controls_container = QWidget()
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        self.header_buttons = []

        btn_new = self._create_header_button("+")
        btn_new.setFixedWidth(40)
        btn_new.clicked.connect(self._on_new_test)
        controls_layout.addWidget(btn_new)
        self.header_buttons.append(btn_new)

        self.btn_comparison = self._create_header_button("Comparison")
        self.btn_comparison.clicked.connect(self._on_toggle_comparison)
        controls_layout.addWidget(self.btn_comparison)
        self.header_buttons.append(self.btn_comparison)

        btn_load = self._create_header_button("Load Data")
        btn_load.clicked.connect(self._on_load_data)
        controls_layout.addWidget(btn_load)
        self.header_buttons.append(btn_load)

        self.btn_export = self._create_header_button("Export")
        self.btn_export.clicked.connect(self._on_export)
        controls_layout.addWidget(self.btn_export)
        self.header_buttons.append(self.btn_export)

        btn_settings = QPushButton("⚙")
        btn_settings.setFixedSize(40, 32)
        btn_settings.setFont(QFont("Segoe UI Symbol", 13))
        btn_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_settings.clicked.connect(self._on_settings)
        controls_layout.addWidget(btn_settings)
        self.header_buttons.append(btn_settings)

        self.theme_toggle = ToggleSwitch()
        self.theme_toggle.set_state(self.is_dark_theme)
        self.theme_toggle.toggled.connect(self._on_theme_toggle)
        controls_layout.addWidget(self.theme_toggle)

        controls_scroll = QScrollArea()
        controls_scroll.setObjectName("headerControlsScroll")
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        controls_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        controls_scroll.setFrameShape(QFrame.Shape.NoFrame)
        controls_scroll.setWidget(controls_container)

        header_layout.addWidget(controls_scroll, 0)
        return header

    def _create_header_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        return btn

    def _create_body(self):
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(10, 10, 10, 10)
        body_layout.setSpacing(10)

        self._main_left_panel = self._create_control_panel()
        self._comparison_left_panel = self._create_comparison_control_panel()
        self.left_stack = QStackedWidget()
        self.left_stack.setObjectName("leftStack")
        self.left_stack.addWidget(self._main_left_panel)
        self.left_stack.addWidget(self._comparison_left_panel)
        self.left_stack.setCurrentIndex(0)
        left_scroll = QScrollArea()
        left_scroll.setWidget(self.left_stack)
        left_scroll.setObjectName("leftScroll")
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setWidget(self.left_stack)
        left_scroll.setMinimumWidth(240)
        left_scroll.setMaximumWidth(460)
        body_layout.addWidget(left_scroll, 0)

        self.divider = QFrame()
        self.divider.setObjectName("mainDivider")
        self.divider.setFixedWidth(1)
        self.divider.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        body_layout.addWidget(self.divider, 0)

        self._main_right_panel = self._create_graph_panel()
        self._comparison_panel = self._create_comparison_panel()

        self.right_stack = QStackedWidget()
        self.right_stack.setObjectName("rightStack")
        self.right_stack.addWidget(self._main_right_panel)
        self.right_stack.addWidget(self._comparison_panel)
        self.right_stack.setCurrentIndex(0)

        body_layout.addWidget(self.right_stack, 1)

        return body

    def _create_comparison_panel(self):
        panel = QFrame()
        panel.setObjectName("comparisonPanel")
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("Comparisons")
        title.setObjectName("comparisonTitle")
        layout.addWidget(title)

        self.comparison_empty_hint = QLabel("Click + to load up to 7 previous tests.")
        self.comparison_empty_hint.setObjectName("comparisonHint")
        self.comparison_empty_hint.setWordWrap(True)
        layout.addWidget(self.comparison_empty_hint)

        self.comparison_graph = ComparisonGraphWidget()
        self.comparison_graph.set_theme(self.is_dark_theme)
        layout.addWidget(self.comparison_graph, 1)
        self.comparison_graph.hide()

        return panel

    def _create_comparison_control_panel(self):
        panel = QFrame()
        panel.setObjectName("comparisonLeftPanel")
        panel.setMinimumWidth(220)
        panel.setMaximumWidth(420)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        top_row = QWidget(panel)
        top_row_l = QHBoxLayout(top_row)
        top_row_l.setContentsMargins(0, 0, 0, 0)
        top_row_l.setSpacing(10)

        self.btn_comparison_add = QPushButton("+")
        self.btn_comparison_add.setObjectName("BtnSquare")
        self.btn_comparison_add.setFixedSize(36, 36)
        self.btn_comparison_add.clicked.connect(self._on_comparison_add_tests)
        top_row_l.addWidget(self.btn_comparison_add, 0)

        title = QLabel("Load Tests")
        title.setObjectName("comparisonLeftTitle")
        top_row_l.addWidget(title, 1)
        layout.addWidget(top_row)

        self.comparison_selected_container = QWidget(panel)
        self.comparison_selected_layout = QVBoxLayout(self.comparison_selected_container)
        self.comparison_selected_layout.setContentsMargins(0, 0, 0, 0)
        self.comparison_selected_layout.setSpacing(10)
        layout.addWidget(self.comparison_selected_container)

        layout.addStretch()

        self.btn_comparison_print = QPushButton("Print")
        self.btn_comparison_print.setObjectName("BtnPrimary")
        self.btn_comparison_print.setFixedHeight(36)
        self.btn_comparison_print.clicked.connect(self._on_comparison_print)
        layout.addWidget(self.btn_comparison_print)

        return panel

    def _clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _on_comparison_add_tests(self):
        dlg = MultiLoadTestsDialog(
            self.db,
            selected_test_ids=self._comparison_selected_test_ids,
            parent=self,
            max_select=7,
            is_dark=self.is_dark_theme,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._comparison_selected_test_ids = list(dlg.selected_test_ids or [])
            self._refresh_comparison_views()

    def _refresh_comparison_views(self):
        if not hasattr(self, "comparison_graph") or self.comparison_graph is None:
            return

        self._clear_layout(self.comparison_selected_layout)
        self.comparison_graph.clear()

        selected_ids = list(self._comparison_selected_test_ids or [])
        if not selected_ids:
            if hasattr(self, "comparison_empty_hint") and self.comparison_empty_hint is not None:
                self.comparison_empty_hint.show()
            self.comparison_graph.hide()
            return

        if hasattr(self, "comparison_empty_hint") and self.comparison_empty_hint is not None:
            self.comparison_empty_hint.hide()
        self.comparison_graph.show()

        series_list = []
        colors = ComparisonGraphWidget.SERIES_COLORS

        for idx, test_id in enumerate(selected_ids):
            test_data = self.db.get_test_by_id(test_id)
            if not test_data:
                continue

            color = colors[idx % len(colors)]

            info_card = QFrame(self.comparison_selected_container)
            info_card.setObjectName("comparisonInfoCard")
            info_l = QVBoxLayout(info_card)
            info_l.setContentsMargins(10, 8, 10, 8)
            info_l.setSpacing(3)

            dot = QLabel(f"● {test_data.get('test_name', test_id)}")
            dot.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 11px;")
            info_l.addWidget(dot)

            for lbl_text in [
                f"{test_data.get('date', '')}  {test_data.get('time', '')}",
                f"Width: {test_data.get('width', '')}   Thickness: {test_data.get('thickness', '')}",
                f"Energy: {test_data.get('final_energy', '')}   Angle: {test_data.get('final_angle', '')}",
            ]:
                lbl = QLabel(lbl_text)
                lbl.setObjectName("cmpCardDetail")
                info_l.addWidget(lbl)

            self.comparison_selected_layout.addWidget(info_card)
            series_list.append((test_id, test_data.get("graph_degrees", []), test_data.get("graph_joules", [])))

        self.comparison_selected_layout.addStretch()
        self.comparison_graph.set_theme(self.is_dark_theme)
        self.comparison_graph.set_all_series(series_list)
        self._apply_panel_styles(self.is_dark_theme)

    def _on_export(self):
        if not (self.is_loaded_test or self.test_completed):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Export Unavailable",
                "Export is only available after a test has been completed or loaded.",
            )
            return
        self._do_export()

    def _do_export(self):
        from PyQt6.QtGui import QPageSize, QPageLayout
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)

        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        painter = QPainter(printer)
        try:
            self._draw_report_page(painter, printer)
        finally:
            painter.end()

    def _draw_report_page(self, painter: QPainter, printer: QPrinter):
        from PyQt6.QtCore import QRect, QRectF, Qt
        from PyQt6.QtGui import QColor, QFont, QPen, QBrush, QPixmap

        page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        W = int(page_rect.width())
        H = int(page_rect.height())

        painter.fillRect(page_rect.toRect(), QColor("#ffffff"))

        mx = int(W * 0.06)
        my = int(H * 0.025)
        cw = W - 2 * mx

        y = my

        # --- HEADER ---
        header_h = int(H * 0.07)
        company_name = getattr(self, "_company_name", "")
        company_logo = getattr(self, "_company_logo_path", "")
        self._render_report_header(painter, mx, my, cw, header_h, W, H, company_name, company_logo)
        y += header_h

        # Accent separator
        sep_pen = QPen(QColor(ACCENT))
        sep_pen.setWidth(max(2, W // 400))
        painter.setPen(sep_pen)
        painter.drawLine(mx, y, mx + cw, y)
        y += int(H * 0.014)

        title_font = QFont("Segoe UI", 11)
        title_font.setBold(True)
        label_font = QFont("Segoe UI", 8)
        label_font.setBold(True)
        value_font = QFont("Segoe UI", 8)

        # --- TEST DETAILS BOX ---
        test_details = [
            ("Test ID",    self.txt_test_id.text().strip()),
            ("Test Name",  self.txt_test_name.text().strip()),
            ("Test Type",  self.comb_test_type.currentText()),
            ("Standard",   self.comb_standard.currentText()),
            ("Party Name", self.txt_party_name.text().strip()),
        ]
        test_box_h = int(H * 0.155)
        self._draw_report_box(
            painter, mx, y, cw, test_box_h,
            "Test Details", test_details,
            title_font, label_font, value_font, W, H,
        )
        y += test_box_h + int(H * 0.012)

        # --- SAMPLE DETAILS BOX ---
        impact_unit = ""
        if hasattr(self, "impact_strength_unit_label") and self.impact_strength_unit_label:
            impact_unit = self.impact_strength_unit_label.text()

        def _fv(w):
            return w.text().strip()

        def _mm(w):
            v = _fv(w)
            return f"{v} mm" if v else ""

        def _j(w):
            v = _fv(w)
            return f"{v} J" if v else ""

        is_val = _fv(self.txt_impact_strength)
        is_str = f"{is_val} {impact_unit}".strip() if is_val else ""

        sample_details = [
            ("Sample Type",    self.comb_sample_type.currentText()),
            ("Batch Number",   _fv(self.txt_batch_number)),
            ("Width",          _mm(self.txt_width)),
            ("Thickness",      _mm(self.txt_thickness)),
            ("Length",         _mm(self.txt_sample_length)),
            ("Depth of Notch", _mm(self.txt_depth_notch)),
            ("Error of M/C",   _j(self.txt_error_mc)),
            ("Scale / Hammer", _j(self.txt_scale_hammer)),
            ("Impact Strength", is_str),
        ]
        sample_box_h = int(H * 0.215)
        self._draw_report_box(
            painter, mx, y, cw, sample_box_h,
            "Sample Details", sample_details,
            title_font, label_font, value_font, W, H,
        )
        y += sample_box_h + int(H * 0.012)

        # --- GRAPH ---
        footer_h = int(H * 0.075)
        graph_h = H - y - footer_h - int(H * 0.012) - my

        degrees = list(self.graph_widget._degrees)
        joules  = list(self.graph_widget._joules)

        render_w = 1200
        render_h = max(400, int(render_w * graph_h / max(cw, 1)))

        temp_graph = GraphWidget()
        temp_graph.set_theme(False)
        temp_graph.set_series(degrees, joules)
        temp_graph.resize(render_w, render_h)

        graph_pix = QPixmap(render_w, render_h)
        graph_pix.fill(QColor("#ffffff"))
        temp_graph.render(graph_pix)

        radius = W * 0.018
        border_pen = QPen(QColor("#d1d5db"))
        border_pen.setWidth(max(1, W // 500))
        painter.setPen(border_pen)
        painter.setBrush(QBrush(QColor("#ffffff")))
        graph_draw_rect = QRectF(mx, y, cw, graph_h)
        painter.drawRoundedRect(graph_draw_rect, radius, radius)

        clip_margin = max(2, W // 500)
        painter.drawPixmap(
            QRect(mx + clip_margin, y + clip_margin, cw - 2 * clip_margin, graph_h - 2 * clip_margin),
            graph_pix,
        )
        y += graph_h + int(H * 0.012)

        # --- FOOTER METRICS ---
        gap = int(cw * 0.012)
        each_w = (cw - 2 * gap) // 3
        metrics_data = [
            ("CURRENT ENERGY",  f"{self.lbl_pressure_value.text()} J"),
            ("CURRENT ANGLE",   f"{self.lbl_degree_value.text()} °"),
            ("IMPACT STRENGTH", self.lbl_impact_value.text()),
        ]

        m_title_font = QFont("Segoe UI", 8)
        m_title_font.setBold(True)
        m_val_font = QFont("Segoe UI", 11)
        m_val_font.setBold(True)

        small_radius = radius * 0.6
        for i, (m_title, m_value) in enumerate(metrics_data):
            gx = mx + i * (each_w + gap)
            m_rect = QRectF(gx, y, each_w, footer_h)
            painter.setPen(QPen(QColor("#d1d5db"), max(1, W // 500)))
            painter.setBrush(QBrush(QColor("#f9fafb")))
            painter.drawRoundedRect(m_rect, small_radius, small_radius)

            pad = int(each_w * 0.06)
            half_h = int(footer_h / 2)

            painter.setFont(m_title_font)
            painter.setPen(QColor("#6B7280"))
            painter.drawText(
                QRect(gx + pad, y + int(footer_h * 0.1), each_w - 2 * pad, half_h),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                m_title,
            )

            painter.setFont(m_val_font)
            painter.setPen(QColor(ACCENT))
            painter.drawText(
                QRect(gx + pad, y + half_h, each_w - 2 * pad, half_h - int(footer_h * 0.1)),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                m_value,
            )

    def _draw_report_box(
        self, painter: QPainter,
        x: int, y: int, w: int, h: int,
        title: str, fields: list,
        title_font: QFont, label_font: QFont, value_font: QFont,
        page_w: int, page_h: int,
    ):
        from PyQt6.QtCore import QRect, QRectF, Qt
        from PyQt6.QtGui import QColor, QPen, QBrush

        radius = page_w * 0.018
        painter.setPen(QPen(QColor("#d1d5db"), max(1, page_w // 500)))
        painter.setBrush(QBrush(QColor("#f9fafb")))
        painter.drawRoundedRect(QRectF(x, y, w, h), radius, radius)

        pad_x = int(page_w * 0.016)
        title_h = int(h * 0.22)

        painter.setFont(title_font)
        painter.setPen(QColor("#111827"))
        painter.drawText(
            QRect(x + pad_x, y + int(page_h * 0.006), w - 2 * pad_x, title_h),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title,
        )

        sep_y = y + title_h
        accent_pen = QPen(QColor(ACCENT))
        accent_pen.setWidth(max(1, page_w // 600))
        painter.setPen(accent_pen)
        painter.drawLine(x + pad_x, sep_y, x + w - pad_x, sep_y)

        fields_top  = sep_y + int(page_h * 0.005)
        fields_h    = h - title_h - int(page_h * 0.005) - int(page_h * 0.008)

        num_fields = len(fields)
        cols = 2
        rows = max(1, (num_fields + cols - 1) // cols)
        col_w = w // cols
        row_h = fields_h // rows if rows else fields_h

        for idx, (label, value) in enumerate(fields):
            col = idx % cols
            row = idx // cols
            fx  = x + col * col_w + pad_x
            fy  = fields_top + row * row_h
            fw  = col_w - 2 * pad_x
            fh  = row_h

            painter.setFont(label_font)
            painter.setPen(QColor("#6B7280"))
            painter.drawText(
                QRect(fx, fy, fw, fh // 2),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                label,
            )

            painter.setFont(value_font)
            painter.setPen(QColor("#111827"))
            display_val = value if value else "\u2014"
            painter.drawText(
                QRect(fx, fy + fh // 2, fw, fh // 2),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                display_val,
            )

    def _on_comparison_print(self):
        if not self._comparison_selected_test_ids:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "No Tests", "Please load at least one test for comparison.")
            return

        from PyQt6.QtGui import QPageSize, QPageLayout
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)

        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        painter = QPainter(printer)
        try:
            self._draw_comparison_report(painter, printer)
        finally:
            painter.end()

    def _draw_comparison_report(self, painter: QPainter, printer: QPrinter):
        from PyQt6.QtCore import QRect, QRectF, Qt
        from PyQt6.QtGui import QColor, QFont, QPen, QBrush, QPixmap

        page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        W = int(page_rect.width())
        H = int(page_rect.height())

        painter.fillRect(page_rect.toRect(), QColor("#ffffff"))

        mx = int(W * 0.06)
        my = int(H * 0.025)
        cw = W - 2 * mx
        y  = my

        # Header
        header_h = int(H * 0.07)
        company_name = getattr(self, "_company_name", "")
        company_logo = getattr(self, "_company_logo_path", "")
        self._render_report_header(painter, mx, my, cw, header_h, W, H, company_name, company_logo)
        y += header_h

        sep_pen = QPen(QColor(ACCENT))
        sep_pen.setWidth(max(2, W // 400))
        painter.setPen(sep_pen)
        painter.drawLine(mx, y, mx + cw, y)
        y += int(H * 0.014)

        # Title
        painter.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        painter.setPen(QColor("#111827"))
        painter.drawText(QRect(mx, y, cw, int(H * 0.04)),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         "Comparison Report")
        y += int(H * 0.05)

        colors = ComparisonGraphWidget.SERIES_COLORS
        all_series = []
        test_rows = []
        for idx, test_id in enumerate(self._comparison_selected_test_ids):
            td = self.db.get_test_by_id(test_id)
            if td:
                all_series.append((test_id, td.get("graph_degrees", []), td.get("graph_joules", [])))
                test_rows.append((idx, td, colors[idx % len(colors)]))

        # Test summary cards (2-column grid)
        card_h = int(H * 0.09)
        card_gap = int(cw * 0.012)
        card_w = (cw - card_gap) // 2
        lf = QFont("Segoe UI", 7)
        lf.setBold(True)
        vf = QFont("Segoe UI", 7)
        radius = W * 0.012

        for i, (c_idx, td, color) in enumerate(test_rows):
            col = i % 2
            row = i // 2
            cx = mx + col * (card_w + card_gap)
            cy = y + row * (card_h + int(H * 0.006))
            cr = QRectF(cx, cy, card_w, card_h)

            painter.setPen(QPen(QColor(color), max(2, W // 400)))
            painter.setBrush(QBrush(QColor("#f9fafb")))
            painter.drawRoundedRect(cr, radius, radius)

            pad = int(card_w * 0.04)
            painter.setFont(lf)
            painter.setPen(QColor(color))
            painter.drawText(QRect(cx + pad, cy + int(card_h * 0.06), card_w - 2 * pad, int(card_h * 0.28)),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             f"● {td.get('test_name', td.get('test_id', ''))}")
            painter.setPen(QColor("#6B7280"))
            detail_lines = [
                f"{td.get('date', '')}  {td.get('time', '')}",
                f"Width: {td.get('width', '')} mm   Thickness: {td.get('thickness', '')} mm",
                f"Final Energy: {td.get('final_energy', '')} J   Final Angle: {td.get('final_angle', '')}°",
            ]
            line_h = int(card_h * 0.22)
            for li, line in enumerate(detail_lines):
                painter.drawText(
                    QRect(cx + pad, cy + int(card_h * 0.34) + li * line_h, card_w - 2 * pad, line_h),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, line,
                )

        rows_count = max(1, (len(test_rows) + 1) // 2)
        y += rows_count * (card_h + int(H * 0.006)) + int(H * 0.012)

        # Merged graph
        graph_h = H - y - my
        render_w = 1200
        render_h = max(400, int(render_w * graph_h / max(cw, 1)))

        temp_g = ComparisonGraphWidget()
        temp_g.set_theme(False)
        temp_g.set_all_series(all_series)
        temp_g.resize(render_w, render_h)

        g_pix = QPixmap(render_w, render_h)
        g_pix.fill(QColor("#ffffff"))
        temp_g.render(g_pix)

        border_pen = QPen(QColor("#d1d5db"))
        border_pen.setWidth(max(1, W // 500))
        painter.setPen(border_pen)
        painter.setBrush(QBrush(QColor("#ffffff")))
        g_rect = QRectF(mx, y, cw, graph_h)
        painter.drawRoundedRect(g_rect, radius, radius)

        clip_m = max(2, W // 500)
        painter.drawPixmap(
            QRect(mx + clip_m, y + clip_m, cw - 2 * clip_m, graph_h - 2 * clip_m),
            g_pix,
        )

    def _render_report_header(self, painter, mx, my, cw, header_h, W, H, company_name, company_logo_path):
        from PyQt6.QtCore import QRect, Qt
        from PyQt6.QtGui import QColor, QFont, QPixmap

        # Logo: constrained to 15 % of content width and 85 % of header height
        logo_max_w = int(cw * 0.15)
        logo_max_h = int(header_h * 0.85)

        if company_logo_path and os.path.isfile(company_logo_path):
            logo_pix = QPixmap(company_logo_path)
            if not logo_pix.isNull():
                scaled = logo_pix.scaled(
                    logo_max_w, logo_max_h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                # Vertically centred, left-aligned
                painter.drawPixmap(mx, my + (header_h - scaled.height()) // 2, scaled)

        # Company name centred across the full content width
        if company_name:
            painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            painter.setPen(QColor("#111827"))
            painter.drawText(
                QRect(mx, my, cw, header_h),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                company_name,
            )

    def _on_settings(self):
        dialog = SettingsDialog(
            current_graph_mode=self._graph_mode,
            company_name=self._company_name,
            company_logo_path=self._company_logo_path,
            is_dark=self.is_dark_theme,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._graph_mode = dialog.selected_graph_mode
            self._company_name = dialog.company_name
            self._company_logo_path = dialog.company_logo_path
            self.db.save_setting("company_name", self._company_name)
            self.db.save_setting("company_logo_path", self._company_logo_path)
            if hasattr(self, 'graph_widget'):
                self.graph_widget.set_graph_mode(self._graph_mode)
    
    def _on_toggle_comparison(self):
        self._comparison_active = not self._comparison_active
        if hasattr(self, "right_stack") and self.right_stack is not None:
            self.right_stack.setCurrentIndex(1 if self._comparison_active else 0)
        if hasattr(self, "left_stack") and self.left_stack is not None:
            self.left_stack.setCurrentIndex(1 if self._comparison_active else 0)

    def _create_control_panel(self):
        panel = QFrame()
        panel.setObjectName("leftPanel")
        panel.setMinimumWidth(220)
        panel.setMaximumWidth(420)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        self.connection_box = QWidget(panel)
        self.connection_box.setObjectName("connectionBox")
        conn_layout = QVBoxLayout(self.connection_box)
        conn_layout.setContentsMargins(0, 0, 0, 0)
        conn_layout.setSpacing(10)

        conn_layout.addWidget(self._section_header("SELECT COM PORT"))

        self.comb_ports = QComboBox(self.connection_box)
        self.comb_ports.setObjectName("Combo")
        self.comb_ports.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.comb_ports.setFixedHeight(36)
        conn_layout.addWidget(self.comb_ports)

        btn_row = QWidget(self.connection_box)
        btn_row_layout = QHBoxLayout(btn_row)
        btn_row_layout.setContentsMargins(0, 0, 0, 0)
        btn_row_layout.setSpacing(10)

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("BtnPrimary")
        self.btn_connect.setFixedHeight(36)

        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setObjectName("BtnSecondary")
        self.btn_disconnect.setFixedHeight(36)

        self.btn_refresh = QPushButton("↻")
        self.btn_refresh.setObjectName("BtnSquare")
        self.btn_refresh.setFixedSize(36, 36)

        btn_row_layout.addWidget(self.btn_connect)
        btn_row_layout.addWidget(self.btn_disconnect)
        btn_row_layout.addWidget(self.btn_refresh)

        conn_layout.addWidget(btn_row)

        self.btn_refresh.clicked.connect(self._refresh_ports)
        self.btn_connect.clicked.connect(self._connect_serial)
        self.btn_disconnect.clicked.connect(self._disconnect_serial)

        layout.addWidget(self.connection_box)

        self.btn_start = QPushButton("Start")
        self.btn_start.setObjectName("BtnPrimary")
        self.btn_start.setFixedHeight(36)
        self.btn_start.clicked.connect(self._on_start)
        layout.addWidget(self.btn_start)

        test_section, test_layout = self._create_collapsible_section("Test Details")
        self.txt_test_id = QLineEdit()
        self.txt_test_id.setObjectName("LineEdit")
        self.txt_test_id.setReadOnly(True)
        self.txt_test_id.setText(self._generate_test_id())
        test_layout.addWidget(self._field("ID", self.txt_test_id))

        self.txt_test_name = QLineEdit()
        self.txt_test_name.setObjectName("LineEdit")
        test_layout.addWidget(self._field("Name", self.txt_test_name))
        self.editable_controls.append(self.txt_test_name)

        self.comb_test_type = QComboBox()
        self.comb_test_type.setObjectName("Combo")
        self.comb_test_type.addItems(["Izod", "Charpy"])
        self.comb_test_type.setFixedHeight(36)
        self.comb_test_type.currentTextChanged.connect(self._on_test_type_changed)
        test_layout.addWidget(self._field("Type", self.comb_test_type, is_combo=True))
        self.editable_controls.append(self.comb_test_type)

        self.comb_standard = QComboBox()
        self.comb_standard.setObjectName("Combo")
        self.comb_standard.setFixedHeight(36)
        self.comb_standard.currentTextChanged.connect(self._calculate_impact_strength)
        test_layout.addWidget(self._field("Standard", self.comb_standard, is_combo=True))
        self.editable_controls.append(self.comb_standard)

        self.txt_party_name = QLineEdit()
        self.txt_party_name.setObjectName("LineEdit")
        test_layout.addWidget(self._field("Party Name", self.txt_party_name))
        self.editable_controls.append(self.txt_party_name)
        layout.addWidget(test_section)

        sample_section, sample_layout = self._create_collapsible_section("Sample Details")
        
        self.comb_sample_type = QComboBox()
        self.comb_sample_type.setObjectName("Combo")
        self.comb_sample_type.addItems(["Unnotched", "Notched"])
        self.comb_sample_type.setFixedHeight(36)
        self.comb_sample_type.currentTextChanged.connect(self._on_sample_type_changed)
        sample_layout.addWidget(self._field("Sample Type", self.comb_sample_type, is_combo=True))
        self.editable_controls.append(self.comb_sample_type)

        self.txt_batch_number = QLineEdit()
        self.txt_batch_number.setObjectName("LineEdit")
        sample_layout.addWidget(self._field("Batch Number", self.txt_batch_number))
        self.editable_controls.append(self.txt_batch_number)

        self.txt_width = QLineEdit()
        self.txt_width.setObjectName("LineEdit")
        sample_layout.addWidget(self._field_with_unit("Width", self.txt_width, "mm"))
        self.editable_controls.append(self.txt_width)

        self.txt_thickness = QLineEdit()
        self.txt_thickness.setObjectName("LineEdit")
        sample_layout.addWidget(self._field_with_unit("Thickness", self.txt_thickness, "mm"))
        self.editable_controls.append(self.txt_thickness)

        self.txt_sample_length = QLineEdit()
        self.txt_sample_length.setObjectName("LineEdit")
        sample_layout.addWidget(self._field_with_unit("Length", self.txt_sample_length, "mm"))
        self.editable_controls.append(self.txt_sample_length)

        self.txt_depth_notch = QLineEdit()
        self.txt_depth_notch.setObjectName("LineEdit")
        sample_layout.addWidget(self._field_with_unit("Depth of Notch", self.txt_depth_notch, "mm"))
        self.editable_controls.append(self.txt_depth_notch)

        self.txt_error_mc = QLineEdit()
        self.txt_error_mc.setObjectName("LineEdit")
        sample_layout.addWidget(self._field_with_unit("Error of M/C", self.txt_error_mc, "J"))
        self.editable_controls.append(self.txt_error_mc)

        self.txt_scale_hammer = QLineEdit()
        self.txt_scale_hammer.setObjectName("LineEdit")
        sample_layout.addWidget(self._field_with_unit("Scale / Hammer", self.txt_scale_hammer, "J"))
        self.editable_controls.append(self.txt_scale_hammer)

        self.txt_impact_strength = QLineEdit()
        self.txt_impact_strength.setObjectName("LineEdit")
        self.txt_impact_strength.setReadOnly(True)
        self.impact_strength_field = self._field_with_unit("Impact Strength", self.txt_impact_strength, "KJ/m²")
        sample_layout.addWidget(self.impact_strength_field)
        self.editable_controls.append(self.txt_impact_strength)
        self.impact_strength_unit_label = self.impact_strength_field.findChild(QLabel, "UnitLabel")

        btns = QWidget()
        btns_l = QHBoxLayout(btns)
        btns_l.setContentsMargins(0, 6, 0, 0)
        btns_l.setSpacing(10)

        self.btn_set = QPushButton("Set")
        self.btn_set.setObjectName("BtnPrimary")
        self.btn_set.setFixedHeight(36)
        self.btn_set.clicked.connect(self._on_set)
        self.editable_controls.append(self.btn_set)

        self.btn_get = QPushButton("Get")
        self.btn_get.setObjectName("BtnSecondary")
        self.btn_get.setFixedHeight(36)
        self.btn_get.clicked.connect(self._on_get)
        self.editable_controls.append(self.btn_get)

        btns_l.addWidget(self.btn_set)
        btns_l.addWidget(self.btn_get)
        sample_layout.addWidget(btns)

        layout.addWidget(sample_section)
        layout.addStretch()

        self._on_test_type_changed("Izod")
        self._refresh_ports()
        return panel

    def _generate_test_id(self) -> str:
        return QDateTime.currentDateTime().toString("yyyyMMdd-HHmmss")

    def _create_collapsible_section(self, title: str) -> tuple[QWidget, QVBoxLayout]:
        root = QWidget()
        root.setObjectName("Collapsible")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(8)

        header = QToolButton()
        header.setObjectName("CollapsibleHeader")
        header.setText(title)
        header.setCheckable(True)
        header.setChecked(False)
        header.setArrowType(Qt.ArrowType.RightArrow)
        header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        header.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        content = QWidget()
        content.setObjectName("CollapsibleContent")
        content.setVisible(False)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        def _toggle(checked: bool):
            content.setVisible(checked)
            header.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)

        header.toggled.connect(_toggle)

        root_layout.addWidget(header)
        root_layout.addWidget(content)
        return root, content_layout

    def _field(self, label: str, edit, is_combo: bool = False) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        lbl = QLabel(label)
        lbl.setObjectName("FieldLabel")
        v.addWidget(lbl)
        v.addWidget(edit)
        return w
    
    def _field_with_unit(self, label: str, edit: QLineEdit, unit: str) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        lbl = QLabel(label)
        lbl.setObjectName("FieldLabel")
        v.addWidget(lbl)
        
        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        h.addWidget(edit)
        
        unit_lbl = QLabel(unit)
        unit_lbl.setObjectName("UnitLabel")
        unit_lbl.setStyleSheet("font-size: 12px; color: #9CA3AF; font-weight: 500;")
        h.addWidget(unit_lbl)
        
        unit_container = QWidget()
        unit_container.setLayout(h)
        v.addWidget(unit_container)
        return w

    def _section_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("SectionHeader")
        return lbl
    
    def _on_test_type_changed(self, test_type: str):
        if test_type == "Izod":
            standards = ["ASTM D 256", "ISO 180", "IS 13360 Part 5 Sec 4"]
        else:
            standards = ["ASTM D 6110", "ISO 179-1", "IS 13360 (Part 5/Sec 5)"]
        
        self.comb_standard.clear()
        self.comb_standard.addItems(standards)
        self._calculate_impact_strength()
    
    def _on_sample_type_changed(self, sample_type: str):
        self._calculate_impact_strength()
    
    def _calculate_impact_strength(self):
        try:
            width = float(self.txt_width.text().strip())
            thickness = float(self.txt_thickness.text().strip())
            depth_notch = float(self.txt_depth_notch.text().strip())
            
            if hasattr(self, 'lbl_pressure_value'):
                energy = float(self.lbl_pressure_value.text().strip())
            else:
                return
            
            test_type = self.comb_test_type.currentText()
            standard = self.comb_standard.currentText()
            sample_type = self.comb_sample_type.currentText()
            
            if test_type == "Izod" and standard == "ASTM D 256":
                impact_strength = energy / (width - depth_notch)
                unit = "J/m"
            else:
                if sample_type == "Unnotched":
                    impact_strength = (energy / (thickness * width)) * 1000
                else:
                    impact_strength = (energy / (thickness * (width - depth_notch))) * 1000
                unit = "KJ/m²"
            
            self.txt_impact_strength.setText(f"{impact_strength:.2f}")
            
            if hasattr(self, 'impact_strength_unit_label') and self.impact_strength_unit_label is not None:
                self.impact_strength_unit_label.setText(unit)
            
            if hasattr(self, 'lbl_impact_value'):
                self.lbl_impact_value.setText(f"{impact_strength:.2f}")
        except Exception:
            self.txt_impact_strength.setText("")
            if hasattr(self, 'lbl_impact_value'):
                self.lbl_impact_value.setText("0.00")

    def _create_status_bar(self):
        status_bar = QFrame()
        status_bar.setObjectName("statusBar")
        status_bar.setFixedHeight(28)

        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(15, 4, 15, 4)
        layout.setSpacing(20)

        self.connection_status_label = QLabel("● Disconnected")
        self.connection_status_label.setStyleSheet("color: #ff5f56; font-size: 12px; font-weight: 500;")
        layout.addWidget(self.connection_status_label)

        self.fishing_label = QLabel("Fishing: 0.05")
        layout.addWidget(self.fishing_label)

        self.version_label = QLabel("Version: v1.0.0")
        layout.addWidget(self.version_label)

        layout.addStretch()

        self.datetime_label = QLabel()
        layout.addWidget(self.datetime_label)

        self._update_datetime()
        self.datetime_timer = QTimer()
        self.datetime_timer.timeout.connect(self._update_datetime)
        self.datetime_timer.start(1000)

        return status_bar

    def _update_datetime(self):
        current = QDateTime.currentDateTime()
        self.datetime_label.setText(current.toString("dd/MM/yyyy, hh:mm:ss AP"))

    def _refresh_ports(self):
        ports = []
        try:
            import serial.tools.list_ports

            ports = [p.device for p in serial.tools.list_ports.comports()]
        except Exception:
            ports = []

        combo = getattr(self, 'comb_ports', None)
        if combo is None:
            return

        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        for p in ports:
            combo.addItem(p)
        if current and current in ports:
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def _connect_serial(self):
        port = ""
        if hasattr(self, 'comb_ports'):
            port = self.comb_ports.currentText().strip()
        if not port:
            if hasattr(self, 'connection_status_label'):
                self.connection_status_label.setText("● Disconnected")
                self.connection_status_label.setStyleSheet("color: #ff5f56; font-size: 12px; font-weight: 500;")
            return

        try:
            import serial

            if self._serial is not None:
                try:
                    self._serial.close()
                except Exception:
                    pass

            self._serial = serial.Serial(
                port=port,
                baudrate=commands.RS232_BAUDRATE,
                bytesize=commands.RS232_BYTESIZE,
                parity=commands.RS232_PARITY,
                stopbits=commands.RS232_STOPBITS,
                timeout=0.1,
                write_timeout=0.5,
            )
            try:
                self._serial.setDTR(True)
                self._serial.setRTS(True)
            except Exception:
                pass
            try:
                self._serial.reset_output_buffer()
            except Exception:
                pass

            if hasattr(self, 'connection_status_label'):
                self.connection_status_label.setText("● Connected")
                self.connection_status_label.setStyleSheet("color: #28c940; font-size: 12px; font-weight: 500;")

            if self._serial_send_timer is None:
                self._serial_send_timer = QTimer(self)
                self._serial_send_timer.setInterval(250)
                self._serial_send_timer.timeout.connect(self._send_poll)
            self._serial_send_timer.start()
        except Exception as e:
            if hasattr(self, 'connection_status_label'):
                self.connection_status_label.setText("● Disconnected")
                self.connection_status_label.setStyleSheet("color: #ff5f56; font-size: 12px; font-weight: 500;")

    def _disconnect_serial(self):
        if self._serial_send_timer is not None:
            self._serial_send_timer.stop()
        if self._set_retry_timer is not None:
            self._set_retry_timer.stop()
        self._pending_set_expected_parts = None
        self._pending_set_cmd = None
        self._pending_set_retries_left = 0
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        self._rx_buffer = bytearray()

        if hasattr(self, 'connection_status_label'):
            self.connection_status_label.setText("● Disconnected")
            self.connection_status_label.setStyleSheet("color: #ff5f56; font-size: 12px; font-weight: 500;")

    def _send_poll(self):
        if self._serial is None:
            return
        try:
            waiting = int(getattr(self._serial, "in_waiting", 0) or 0)
            if waiting <= 0:
                return
            data = self._serial.read(waiting)
            if not data:
                return
            if DEBUG_SERIAL:
                print(f"RX_BYTES: {data!r}")
                try:
                    print(f"RX_HEX: {data.hex()}")
                except Exception:
                    pass
            self._rx_buffer.extend(data)

            def _pop_frame() -> bytes | None:
                idx_hash = self._rx_buffer.find(b"#")
                idx_rs = self._rx_buffer.find(b"\x1e")
                idx_nl = self._rx_buffer.find(b"\n")
                idx_e = -1
                if self._rx_buffer.startswith(b"sp$") and idx_hash == -1 and idx_rs == -1 and idx_nl == -1:
                    idx_e = self._rx_buffer.find(b"E")

                idxs = [i for i in [idx_hash, idx_rs, idx_nl, idx_e] if i != -1]
                if not idxs:
                    return None
                idx = min(idxs)
                frame = bytes(self._rx_buffer[: idx + 1])
                del self._rx_buffer[: idx + 1]
                return frame

            while True:
                frame = _pop_frame()
                if frame is None:
                    break
                text = frame.decode(errors="ignore").strip()
                if not text:
                    continue
                print(f"RX: {text}")
                self._handle_rx_line(text)
        except Exception:
            self._disconnect_serial()

    def _handle_rx_line(self, line: str):
        try:
            if not line.startswith("sp$"):
                return
            
            is_end = "$2E" in line or line.endswith("2E")
            
            clean = line
            if clean.endswith("#"):
                clean = clean[:-1]
            if clean.endswith("\x1e"):
                clean = clean[:-1]
            if clean.endswith("2E"):
                clean = clean[:-2]
            if clean.endswith("1E"):
                clean = clean[:-2]
            if clean.endswith("E"):
                clean = clean[:-1]
            clean = clean.strip()

            parts = clean.split("$")
            if len(parts) < 3:
                return
            if parts[0] != "sp":
                return

            if self._pending_set_expected_parts is not None and len(parts) >= 7:
                expected = self._pending_set_expected_parts
                got = parts[1:7]
                if got == expected and ("E" in line or line.endswith("E")):
                    if self._set_retry_timer is not None:
                        self._set_retry_timer.stop()
                    self._pending_set_expected_parts = None
                    self._pending_set_cmd = None
                    self._pending_set_retries_left = 0

            def _decode(v: str) -> float:
                v = v.strip()
                if v.isdigit():
                    return int(v) / 100.0
                return float(v)

            # GET PARAM response: sp$0500$0298$0100$0500$0000$0063
            if len(parts) >= 7:
                width = _decode(parts[1])
                thickness = _decode(parts[2])
                sample_length = _decode(parts[3])
                depth_notch = _decode(parts[4])
                error_mc = _decode(parts[5])
                scale_hammer = _decode(parts[6])

                if hasattr(self, "txt_width"):
                    self.txt_width.setText(f"{width:.2f}")
                if hasattr(self, "txt_thickness"):
                    self.txt_thickness.setText(f"{thickness:.2f}")
                if hasattr(self, "txt_sample_length"):
                    self.txt_sample_length.setText(f"{sample_length:.2f}")
                if hasattr(self, "txt_depth_notch"):
                    self.txt_depth_notch.setText(f"{depth_notch:.2f}")
                if hasattr(self, "txt_error_mc"):
                    self.txt_error_mc.setText(f"{error_mc:.2f}")
                if hasattr(self, "txt_scale_hammer"):
                    self.txt_scale_hammer.setText(f"{scale_hammer:.2f}")
                return

            # START auto response: sp$Joules$Degree$1E or sp$Joules$Degree$2E
            if len(parts) >= 3:
                joules = _decode(parts[1])
                degree_raw = parts[2].strip()
                degree = int(degree_raw) if degree_raw.isdigit() else float(degree_raw)
                if hasattr(self, "lbl_degree_value"):
                    self.lbl_degree_value.setText(f"{degree:.0f}")
                if hasattr(self, "lbl_pressure_value"):
                    error_mc = 0.0
                    try:
                        error_mc = float(self.txt_error_mc.text().strip())
                    except:
                        pass
                    
                    if abs(joules - 6.30) < 0.01:
                        current_energy = 0.0
                    else:
                        current_energy = abs(error_mc - joules)
                    
                    self.lbl_pressure_value.setText(f"{current_energy:.2f}")
                    self._calculate_impact_strength()
                if hasattr(self, "graph_widget"):
                    self.graph_widget.set_data_point(degree, joules, is_end=is_end)
        except Exception:
            return

    def _send_command(self, cmd: str):
        print(f"TX: {cmd}")
        if self._serial is None:
            return
        try:
            self._serial.write((cmd + "\r\n").encode("ascii", errors="ignore"))
            try:
                self._serial.flush()
            except Exception:
                pass
        except Exception:
            self._disconnect_serial()

    def _tick_set_retry(self):
        if self._pending_set_cmd is None:
            if self._set_retry_timer is not None:
                self._set_retry_timer.stop()
            return
        if self._pending_set_retries_left <= 0:
            if self._set_retry_timer is not None:
                self._set_retry_timer.stop()
            self._pending_set_expected_parts = None
            self._pending_set_cmd = None
            return

        self._pending_set_retries_left -= 1
        self._send_command(self._pending_set_cmd)

    def _on_start(self):
        if self.is_loaded_test:
            return
        
        missing_fields = []
        
        if not self.txt_test_id.text().strip():
            missing_fields.append("ID")
        if not self.txt_test_name.text().strip():
            missing_fields.append("Name")
        if not self.txt_party_name.text().strip():
            missing_fields.append("Party Name")
        if not self.txt_batch_number.text().strip():
            missing_fields.append("Batch Number")
        if not self.txt_width.text().strip():
            missing_fields.append("Width")
        if not self.txt_thickness.text().strip():
            missing_fields.append("Thickness")
        if not self.txt_sample_length.text().strip():
            missing_fields.append("Length")
        if not self.txt_depth_notch.text().strip():
            missing_fields.append("Depth of Notch")
        if not self.txt_error_mc.text().strip():
            missing_fields.append("Error of M/C")
        if not self.txt_scale_hammer.text().strip():
            missing_fields.append("Scale / Hammer")
        
        if missing_fields:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Missing Fields")
            msg.setText("Please fill in all required fields before starting the test.")
            msg.setInformativeText("Missing fields:\n" + "\n".join(f"• {field}" for field in missing_fields))
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            return
        
        if hasattr(self, "graph_widget"):
            self.graph_widget.clear()
        
        self.test_in_progress = True
        self.current_test_id = self.txt_test_id.text()
        self._lock_controls()
        
        cmd = commands.start_command()
        for _ in range(5):
            self._send_command(cmd)

    def _on_get(self):
        self._send_command(commands.get_param_command())

    def _on_set(self):
        def _f(edit: QLineEdit) -> float:
            try:
                return float(edit.text().strip())
            except Exception:
                return 0.0

        cmd = commands.set_param_command(
            width_mm=_f(self.txt_width),
            thickness_mm=_f(self.txt_thickness),
            sample_length_mm=_f(self.txt_sample_length),
            depth_of_notch=_f(self.txt_depth_notch),
            error_of_mc=_f(self.txt_error_mc),
            scale_hammer=_f(self.txt_scale_hammer),
        )
        try:
            parts = cmd.split("$")
            if len(parts) >= 7:
                expected = parts[1:7]
                expected[-1] = expected[-1].replace("#", "")
                self._pending_set_expected_parts = expected
                self._pending_set_cmd = cmd
                self._pending_set_retries_left = 200
        except Exception:
            self._pending_set_expected_parts = None
            self._pending_set_cmd = None
            self._pending_set_retries_left = 0

        for _ in range(5):
            self._send_command(cmd)
        if self._set_retry_timer is not None and self._pending_set_cmd is not None:
            self._set_retry_timer.start()
    
    def _lock_controls(self):
        for control in self.editable_controls:
            if isinstance(control, QLineEdit):
                control.setReadOnly(True)
            elif isinstance(control, (QPushButton, QComboBox)):
                control.setEnabled(False)
        
        if hasattr(self, 'btn_start'):
            self.btn_start.setEnabled(False)
    
    def _unlock_controls(self):
        for control in self.editable_controls:
            if isinstance(control, QLineEdit):
                control.setReadOnly(False)
            elif isinstance(control, (QPushButton, QComboBox)):
                control.setEnabled(True)
        
        if hasattr(self, 'btn_start'):
            self.btn_start.setEnabled(True)
    
    def _on_new_test(self):
        self.is_loaded_test = False
        self.test_in_progress = False
        self.test_completed = False
        self.current_test_id = None
        
        self.txt_test_id.setText(self._generate_test_id())
        self.txt_test_name.clear()
        self.comb_test_type.setCurrentIndex(0)
        self.txt_party_name.clear()
        self.comb_sample_type.setCurrentIndex(0)
        self.txt_batch_number.clear()
        self.txt_width.clear()
        self.txt_thickness.clear()
        self.txt_sample_length.clear()
        self.txt_depth_notch.clear()
        self.txt_error_mc.clear()
        self.txt_scale_hammer.clear()
        self.txt_impact_strength.clear()
        
        if hasattr(self, 'lbl_degree_value'):
            self.lbl_degree_value.setText("0.00")
        if hasattr(self, 'lbl_pressure_value'):
            self.lbl_pressure_value.setText("0.00")
        if hasattr(self, 'lbl_impact_value'):
            self.lbl_impact_value.setText("0.00")
        
        if hasattr(self, 'graph_widget'):
            self.graph_widget.clear()

        self._unlock_controls()
        self._update_export_button_state()

    def _save_test(self):
        if not self.current_test_id or not hasattr(self, 'graph_widget'):
            return
        
        def _f(edit: QLineEdit) -> float:
            try:
                return float(edit.text().strip())
            except Exception:
                return 0.0
        
        graph_degrees = self.graph_widget._degrees
        graph_joules = self.graph_widget._joules
        
        if len(graph_degrees) == 0 or len(graph_joules) == 0:
            return
        
        test_data = {
            "test_id": self.current_test_id,
            "test_name": self.txt_test_name.text().strip(),
            "test_type": self.comb_test_type.currentText(),
            "standard": self.comb_standard.currentText(),
            "party_name": self.txt_party_name.text().strip(),
            "sample_type": self.comb_sample_type.currentText(),
            "batch_number": self.txt_batch_number.text().strip(),
            "width": _f(self.txt_width),
            "thickness": _f(self.txt_thickness),
            "sample_length": _f(self.txt_sample_length),
            "depth_notch": _f(self.txt_depth_notch),
            "error_mc": _f(self.txt_error_mc),
            "scale_hammer": _f(self.txt_scale_hammer),
            "impact_strength": _f(self.txt_impact_strength),
            "graph_degrees": graph_degrees,
            "graph_joules": graph_joules,
            "final_energy": graph_joules[-1] if graph_joules else 0.0,
            "final_angle": graph_degrees[-1] if graph_degrees else 0.0,
        }
        
        try:
            date_str, time_str = self.db.save_test(test_data)
        except Exception as e:
            pass

        self.test_completed = True
        self._update_export_button_state()

    def _update_export_button_state(self):
        enabled = self.is_loaded_test or self.test_completed
        if hasattr(self, 'btn_export'):
            self.btn_export.setEnabled(enabled)

    def _on_load_data(self):
        dialog = LoadTestDialog(self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_test_id = dialog.selected_test_id
            if selected_test_id:
                self._load_test(selected_test_id)
    
    def _load_test(self, test_id):
        test_data = self.db.get_test_by_id(test_id)
        if not test_data:
            return

        self.is_loaded_test = True
        self.current_test_id = test_data["test_id"]
        
        self.txt_test_id.setText(test_data["test_id"])
        self.txt_test_name.setText(test_data.get("test_name", ""))
        
        test_type = test_data.get("test_type", "Izod")
        idx = self.comb_test_type.findText(test_type)
        if idx >= 0:
            self.comb_test_type.setCurrentIndex(idx)
        
        standard = test_data.get("standard", "")
        if standard:
            idx = self.comb_standard.findText(standard)
            if idx >= 0:
                self.comb_standard.setCurrentIndex(idx)
        
        self.txt_party_name.setText(test_data.get("party_name", ""))
        
        sample_type = test_data.get("sample_type", "Unnotched")
        idx = self.comb_sample_type.findText(sample_type)
        if idx >= 0:
            self.comb_sample_type.setCurrentIndex(idx)
        
        self.txt_batch_number.setText(test_data.get("batch_number", ""))
        self.txt_width.setText(f"{test_data.get('width', 0.0):.2f}")
        self.txt_thickness.setText(f"{test_data.get('thickness', 0.0):.2f}")
        self.txt_sample_length.setText(f"{test_data.get('sample_length', 0.0):.2f}")
        self.txt_depth_notch.setText(f"{test_data.get('depth_notch', 0.0):.2f}")
        self.txt_error_mc.setText(f"{test_data.get('error_mc', 0.0):.2f}")
        self.txt_scale_hammer.setText(f"{test_data.get('scale_hammer', 0.0):.2f}")
        self.txt_impact_strength.setText(f"{test_data.get('impact_strength', 0.0):.2f}")
        
        if hasattr(self, 'lbl_degree_value'):
            self.lbl_degree_value.setText(f"{test_data.get('final_angle', 0.0):.0f}")
        if hasattr(self, 'lbl_pressure_value'):
            self.lbl_pressure_value.setText(f"{test_data.get('final_energy', 0.0):.2f}")
        if hasattr(self, 'lbl_impact_value'):
            self.lbl_impact_value.setText(f"{test_data.get('impact_strength', 0.0):.2f}")
        
        if hasattr(self, 'graph_widget'):
            self.graph_widget.clear()
            self.graph_widget._degrees = test_data.get("graph_degrees", [])
            self.graph_widget._joules = test_data.get("graph_joules", [])
            self.graph_widget.update()

        self._lock_controls()
        self._update_export_button_state()

    def _create_graph_panel(self):
        panel = QFrame()
        panel.setObjectName("rightPanel")
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.graph_widget = GraphWidget(self)
        self.graph_widget.set_graph_mode(self._graph_mode)
        layout.addWidget(self.graph_widget, 1)

        overlay = QWidget(panel)
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        overlay.setStyleSheet("background: transparent;")
        overlay.raise_()

        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(8, 4, 8, 50)

        top_row = QHBoxLayout()
        top_row.addStretch()

        metrics = QHBoxLayout()
        metrics.setSpacing(18)

        self._metric_title_color = "#9CA3AF"

        self.lbl_pressure_title = QLabel("CURRENT ENERGY")
        self.lbl_pressure_title.setObjectName("metricTitle")
        self.lbl_pressure_value = QLabel("0.00")
        self.lbl_pressure_value.setObjectName("metricValue")

        self.lbl_degree_title = QLabel("CURRENT ANGLE")
        self.lbl_degree_title.setObjectName("metricTitle")
        self.lbl_degree_value = QLabel("0.00")
        self.lbl_degree_value.setObjectName("metricValue")

        self.lbl_impact_title = QLabel("IMPACT STRENGTH")
        self.lbl_impact_title.setObjectName("metricTitle")
        self.lbl_impact_value = QLabel("0.00")
        self.lbl_impact_value.setObjectName("metricValue")

        def wrap(title: QLabel, value: QLabel) -> QWidget:
            w = QWidget()
            v = QVBoxLayout(w)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(0)
            v.addWidget(title, alignment=Qt.AlignmentFlag.AlignRight)
            v.addWidget(value, alignment=Qt.AlignmentFlag.AlignRight)
            return w

        metrics.addWidget(wrap(self.lbl_pressure_title, self.lbl_pressure_value))
        metrics.addWidget(wrap(self.lbl_degree_title, self.lbl_degree_value))
        metrics.addWidget(wrap(self.lbl_impact_title, self.lbl_impact_value))

        metrics_widget = QWidget()
        metrics_widget.setLayout(metrics)
        metrics_widget.setStyleSheet("background: transparent;")

        top_row.addWidget(metrics_widget, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        overlay_layout.addLayout(top_row)
        overlay_layout.addStretch()

        def resize_overlay(event):
            overlay.setGeometry(panel.contentsRect())
            QWidget.resizeEvent(panel, event)

        panel.resizeEvent = resize_overlay

        return panel

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_header()

    def _apply_responsive_header(self):
        if not hasattr(self, 'header_buttons'):
            return

        w = self.width()

        text_map_full = {
            "+": "+",
            "Comparison": "Comparison",
            "Load Data": "Load Data",
            "Export": "Export",
        }
        text_map_medium = {
            "+": "+",
            "Comparison": "Compare",
            "Load Data": "Load",
            "Export": "Export",
        }
        text_map_small = {
            "+": "+",
            "Comparison": "Cmp",
            "Load Data": "Load",
            "Export": "Exp",
        }

        mapping = text_map_full
        if w < 1050:
            mapping = text_map_medium
        if w < 900:
            mapping = text_map_small

        for btn in self.header_buttons:
            if not isinstance(btn, QPushButton):
                continue
            txt = btn.text()
            if txt in mapping:
                btn.setText(mapping[txt])

    def _on_theme_toggle(self, dark: bool):
        self.is_dark_theme = dark
        if dark:
            self._apply_dark_theme()
        else:
            self._apply_light_theme()
        self.theme_toggle.set_state(dark)

    def _apply_dark_theme(self):
        self.centralWidget().setStyleSheet(f"background-color: {DARK_BG};")

        self.title_bar.setStyleSheet(f"background-color: {DARK_BG};")
        self.header_frame.setStyleSheet("background-color: #1e1e1e; border: none;")
        self.logo_widget.load(resource_path("hexaplast_logo_white.svg"))

        self.graph_widget.set_theme(True)
        if hasattr(self, "comparison_graph") and self.comparison_graph is not None:
            self.comparison_graph.set_theme(True)

        self._apply_panel_styles(is_dark=True)

    def _apply_light_theme(self):
        self.centralWidget().setStyleSheet(f"background-color: {LIGHT_BG};")

        self.title_bar.setStyleSheet(f"background-color: {LIGHT_BG};")
        self.header_frame.setStyleSheet("background-color: #ffffff; border: none;")
        self.logo_widget.load(resource_path("hexaplast_logo_gray.svg"))

        self.graph_widget.set_theme(False)
        if hasattr(self, "comparison_graph") and self.comparison_graph is not None:
            self.comparison_graph.set_theme(False)

        self._apply_panel_styles(is_dark=False)

    def _apply_panel_styles(self, is_dark: bool):
        panel_bg = DARK_PANEL if is_dark else LIGHT_PANEL
        panel_border = "rgba(255,255,255,0.1)" if is_dark else "rgba(0,0,0,0.1)"
        text = DARK_TEXT if is_dark else LIGHT_TEXT

        self.findChild(QFrame, "leftPanel").setStyleSheet(
            f"QFrame#leftPanel {{ background-color: transparent; border: none; }}"
        )

        self.findChild(QFrame, "rightPanel").setStyleSheet(
            f"QFrame#rightPanel {{ background-color: transparent; border: none; }}"
        )

        comparison_panel = self.findChild(QFrame, "comparisonPanel")
        if comparison_panel is not None:
            comparison_panel.setStyleSheet(
                f"QFrame#comparisonPanel {{ background-color: transparent; border: none; }}"
            )

        cmp_title = self.findChild(QLabel, "comparisonTitle")
        if cmp_title is not None:
            cmp_title.setStyleSheet(f"color: {text}; font-size: 20px; font-weight: 900;")
        cmp_hint = self.findChild(QLabel, "comparisonHint")
        if cmp_hint is not None:
            muted = "#d1d5db" if is_dark else "#374151"
            cmp_hint.setStyleSheet(f"color: {muted}; font-size: 13px; font-weight: 600;")

        if hasattr(self, 'graph_widget') and self.graph_widget is not None:
            self.graph_widget.setStyleSheet("border: none;")

        header_scroll = self.findChild(QScrollArea, "headerControlsScroll")
        if header_scroll is not None:
            header_scroll.setStyleSheet("background: transparent;")

        left_scroll = self.findChild(QScrollArea, "leftScroll")
        if left_scroll is not None:
            left_scroll.setStyleSheet("background: transparent;")

        divider = self.findChild(QFrame, "mainDivider")
        if divider is not None:
            divider_color = "rgba(255,255,255,0.10)" if is_dark else "rgba(0,0,0,0.10)"
            divider.setStyleSheet(f"background-color: {divider_color};")

        status_bg = "#1a1a1a" if is_dark else LIGHT_PANEL
        status_widget = self.findChild(QFrame, "statusBar")
        if status_widget is not None:
            status_widget.setStyleSheet(f"background-color: {status_bg}; border: none;")

        if hasattr(self, 'fishing_label'):
            self.fishing_label.setStyleSheet(f"color: {text}; font-size: 12px;")
        if hasattr(self, 'version_label'):
            self.version_label.setStyleSheet(f"color: {text}; font-size: 12px;")
        if hasattr(self, 'datetime_label'):
            self.datetime_label.setStyleSheet(f"color: {text}; font-size: 12px;")

        sep_lbl = self.findChild(QLabel, "appSep")
        if sep_lbl is not None:
            sep_lbl.setStyleSheet(f"color: {text}; font-size: 20px; font-weight: 600;")
        title_lbl = self.findChild(QLabel, "appTitle")
        if title_lbl is not None:
            title_lbl.setStyleSheet(f"color: {text}; font-size: 20px; font-weight: 800; letter-spacing: 1.2px;")

        if hasattr(self, 'header_buttons'):
            for btn in self.header_buttons:
                if isinstance(btn, QPushButton) and btn.text() == "+":
                    btn.setFixedHeight(32)
                    btn.setStyleSheet(self._get_header_button_style(is_dark, accent=True))
                elif isinstance(btn, QPushButton) and btn.icon().isNull() is False and btn.text() == "":
                    btn.setFixedHeight(32)
                    btn.setStyleSheet(self._get_header_button_style(is_dark))
                elif isinstance(btn, QPushButton):
                    btn.setFixedHeight(32)
                    btn.setStyleSheet(self._get_header_button_style(is_dark))

        box_bg = "transparent"
        self.connection_box.setStyleSheet(
            f"QWidget#connectionBox {{ background-color: {box_bg}; border: none; }}"
        )

        section_header = self.findChild(QLabel, "SectionHeader")
        if section_header is not None:
            section_header.setStyleSheet(
                f"color: {text}; font-size: 16px; font-weight: 800; letter-spacing: 0.8px; padding-left: 2px;"
            )

        combo_bg = "#171718" if is_dark else "#ffffff"
        combo_text = "#ffffff" if is_dark else "#111827"
        combo_border = "1px solid rgba(255,255,255,0.08)" if is_dark else "1px solid rgba(0,0,0,0.08)"
        for combo in self.findChildren(QComboBox, "Combo"):
            combo.setStyleSheet(
                "\n".join(
                    [
                        "QComboBox {",
                        f"  background-color: {combo_bg};",
                        f"  color: {combo_text};",
                        f"  border: {combo_border};",
                        "  border-radius: 12px;",
                        "  padding: 8px 12px;",
                        "  padding-right: 38px;",
                        "  font-size: 14pt;",
                        "}",
                        "QComboBox::drop-down {",
                        "  width: 34px;",
                        "  border-left: 0px solid transparent;",
                        "}",
                        "QComboBox QAbstractItemView {",
                        f"  background-color: {combo_bg};",
                        f"  color: {combo_text};",
                        "  selection-background-color: rgba(0,189,202,0.25);",
                        "  border: 0px solid transparent;",
                        "  outline: 0;",
                        "}",
                    ]
                )
            )

        refresh_bg = "#2a2b33" if is_dark else "#e5e7eb"
        refresh_text = "#ffffff" if is_dark else "#111827"

        if hasattr(self, "btn_comparison_add"):
            self.btn_comparison_add.setStyleSheet(
                "\n".join(
                    [
                        "QPushButton {",
                        f"  background-color: {refresh_bg};",
                        f"  color: {refresh_text};",
                        "  border: none;",
                        "  border-radius: 12px;",
                        "  font-size: 14pt;",
                        "  font-weight: 700;",
                        "}",
                        "QPushButton:hover {",
                        "  background-color: rgba(255,255,255,0.12);",
                        "}",
                    ]
                )
            )

        if hasattr(self, "btn_comparison_print"):
            self.btn_comparison_print.setStyleSheet(
                "\n".join(
                    [
                        "QPushButton {",
                        f"  background-color: {ACCENT};",
                        "  color: #000000;",
                        "  border: none;",
                        "  border-radius: 12px;",
                        "  font-size: 12pt;",
                        "  font-weight: 600;",
                        "  padding: 0px 10px;",
                        "}",
                        "QPushButton:hover {",
                        "  background-color: #00a8b5;",
                        "}",
                    ]
                )
            )

        cmp_left_title = self.findChild(QLabel, "comparisonLeftTitle")
        if cmp_left_title is not None:
            cmp_left_title.setStyleSheet(f"color: {text}; font-size: 16px; font-weight: 900;")

        for card in self.findChildren(QFrame, "comparisonInfoCard"):
            card_bg = "rgba(255,255,255,0.04)" if is_dark else "rgba(0,0,0,0.03)"
            card_border = "1px solid rgba(255,255,255,0.08)" if is_dark else "1px solid rgba(0,0,0,0.06)"
            card.setStyleSheet(f"background-color: {card_bg}; border: {card_border}; border-radius: 10px;")
            for lbl in card.findChildren(QLabel, "cmpCardDetail"):
                muted = "#9CA3AF" if is_dark else "#6B7280"
                lbl.setStyleSheet(f"color: {muted}; font-size: 10px; font-weight: 500;")

        if hasattr(self, 'btn_connect'):
            self.btn_connect.setStyleSheet(
                "\n".join(
                    [
                        "QPushButton {",
                        f"  background-color: {ACCENT};",
                        "  color: #000000;",
                        "  border: none;",
                        "  border-radius: 12px;",
                        "  font-size: 11pt;",
                        "  font-weight: 400;",
                        "  padding: 0px 10px;",
                        "}",
                        "QPushButton:hover {",
                        "  background-color: #00a8b5;",
                        "}",
                    ]
                )
            )

        if hasattr(self, 'btn_start'):
            self.btn_start.setStyleSheet(
                "\n".join(
                    [
                        "QPushButton {",
                        f"  background-color: {ACCENT};",
                        "  color: #000000;",
                        "  border: none;",
                        "  border-radius: 12px;",
                        "  font-size: 12pt;",
                        "  font-weight: 600;",
                        "  padding: 0px 10px;",
                        "}",
                        "QPushButton:hover {",
                        "  background-color: #00a8b5;",
                        "}",
                    ]
                )
            )

        if hasattr(self, 'btn_set'):
            self.btn_set.setStyleSheet(
                "\n".join(
                    [
                        "QPushButton {",
                        f"  background-color: {ACCENT};",
                        "  color: #000000;",
                        "  border: none;",
                        "  border-radius: 12px;",
                        "  font-size: 12pt;",
                        "  font-weight: 600;",
                        "  padding: 0px 10px;",
                        "}",
                        "QPushButton:hover {",
                        "  background-color: #00a8b5;",
                        "}",
                    ]
                )
            )

        disconnect_bg = "#2a2b33" if is_dark else "#e5e7eb"
        disconnect_text = "#ffffff" if is_dark else "#111827"
        if hasattr(self, 'btn_disconnect'):
            self.btn_disconnect.setStyleSheet(
                "\n".join(
                    [
                        "QPushButton {",
                        f"  background-color: {disconnect_bg};",
                        f"  color: {disconnect_text};",
                        "  border: none;",
                        "  border-radius: 12px;",
                        "  font-size: 11pt;",
                        "  font-weight: 400;",
                        "  padding: 0px 10px;",
                        "}",
                        "QPushButton:hover {",
                        "  background-color: rgba(255,255,255,0.12);",
                        "}",
                    ]
                )
            )

        if hasattr(self, 'btn_get'):
            self.btn_get.setStyleSheet(
                "\n".join(
                    [
                        "QPushButton {",
                        f"  background-color: {disconnect_bg};",
                        f"  color: {disconnect_text};",
                        "  border: none;",
                        "  border-radius: 12px;",
                        "  font-size: 12pt;",
                        "  font-weight: 600;",
                        "  padding: 0px 10px;",
                        "}",
                        "QPushButton:hover {",
                        "  background-color: rgba(255,255,255,0.12);",
                        "}",
                    ]
                )
            )

        refresh_bg = "#2a2b33" if is_dark else "#e5e7eb"
        refresh_text = "#ffffff" if is_dark else "#111827"
        if hasattr(self, 'btn_refresh'):
            self.btn_refresh.setStyleSheet(
                "\n".join(
                    [
                        "QPushButton {",
                        f"  background-color: {refresh_bg};",
                        f"  color: {refresh_text};",
                        "  border: none;",
                        "  border-radius: 12px;",
                        "  font-size: 14pt;",
                        "  font-weight: 700;",
                        "}",
                        "QPushButton:hover {",
                        "  background-color: rgba(255,255,255,0.12);",
                        "}",
                    ]
                )
            )

        input_bg = "#171718" if is_dark else "#ffffff"
        input_text = "#ffffff" if is_dark else "#111827"
        input_border = "1px solid rgba(255,255,255,0.08)" if is_dark else "1px solid rgba(0,0,0,0.10)"
        for edit in self.findChildren(QLineEdit, "LineEdit"):
            edit.setFixedHeight(34)
            edit.setStyleSheet(
                "\n".join(
                    [
                        "QLineEdit {",
                        f"  background-color: {input_bg};",
                        f"  color: {input_text};",
                        f"  border: {input_border};",
                        "  border-radius: 10px;",
                        "  padding: 0px 10px;",
                        "  font-size: 11pt;",
                        "}",
                        "QLineEdit:focus {",
                        f"  border: 1px solid {ACCENT};",
                        "}",
                    ]
                )
            )

        field_label = self.findChildren(QLabel, "FieldLabel")
        for lbl in field_label:
            lbl.setStyleSheet(f"color: {text}; font-size: 12px; font-weight: 700;")

        for hdr in self.findChildren(QToolButton, "CollapsibleHeader"):
            hdr.setStyleSheet(
                "\n".join(
                    [
                        "QToolButton {",
                        f"  color: {text};",
                        "  border: none;",
                        "  font-size: 14px;",
                        "  font-weight: 800;",
                        "  padding: 4px 0px;",
                        "}",
                    ]
                )
            )

        metric_title = "#9CA3AF" if is_dark else "#6B7280"
        self.lbl_pressure_title.setStyleSheet(
            f"font-size: 10px; color: {metric_title}; font-weight: bold; letter-spacing: 0.5px;"
        )
        self.lbl_degree_title.setStyleSheet(
            f"font-size: 10px; color: {metric_title}; font-weight: bold; letter-spacing: 0.5px;"
        )
        self.lbl_impact_title.setStyleSheet(
            f"font-size: 10px; color: {metric_title}; font-weight: bold; letter-spacing: 0.5px;"
        )

        self.lbl_pressure_value.setStyleSheet(
            "font-size: 24px; font-weight: 800; color: #00bdca; padding-left: 10px;"
        )
        self.lbl_degree_value.setStyleSheet(
            "font-size: 24px; font-weight: 800; color: #00bdca; padding-left: 10px;"
        )
        self.lbl_impact_value.setStyleSheet(
            "font-size: 24px; font-weight: 800; color: #00bdca; padding-left: 10px;"
        )

    def _get_header_button_style(self, is_dark: bool, accent: bool = False) -> str:
        if accent:
            return (
                "QPushButton {"
                f" background-color: {ACCENT};"
                " color: #000000;"
                " border: none;"
                " border-radius: 6px;"
                " padding: 10px 16px;"
                " font-size: 13px;"
                " font-weight: 600;"
                "}"
                "QPushButton:hover { background-color: #00a8b5; }"
            )

        bg_color = "#2d2d2d" if is_dark else "#E5E7EB"
        text_color = "#ffffff" if is_dark else "#374151"
        hover_bg = "#3d3d3d" if is_dark else "#D1D5DB"
        border = "1px solid rgba(255,255,255,0.1)" if is_dark else "1px solid rgba(0,0,0,0.1)"
        disabled_bg = "#232323" if is_dark else "#F3F4F6"
        disabled_text = "rgba(255,255,255,0.25)" if is_dark else "rgba(0,0,0,0.25)"
        return (
            "QPushButton {"
            f" background-color: {bg_color};"
            f" color: {text_color};"
            f" border: {border};"
            " border-radius: 6px;"
            " padding: 10px 16px;"
            " font-size: 13px;"
            " font-weight: 600;"
            "}"
            f"QPushButton:hover {{ background-color: {hover_bg}; }}"
            "QPushButton:disabled {"
            f" background-color: {disabled_bg};"
            f" color: {disabled_text};"
            " border: none;"
            "}"
        )


def main():
    import traceback

    # In a frozen windowed exe (console=False) sys.stdout/stderr are None;
    # any print() call would raise AttributeError and crash silently.
    # Redirect them to devnull so the rest of the code is safe.
    if getattr(sys, "frozen", False):
        import io
        _nul = open(os.devnull, "w")
        if sys.stdout is None or not hasattr(sys.stdout, "write"):
            sys.stdout = _nul
        if sys.stderr is None or not hasattr(sys.stderr, "write"):
            sys.stderr = _nul

    # Write any fatal startup error to a log file next to the exe
    _log_path = data_path("izod_error.log")

    try:
        # High-DPI and rendering compatibility
        os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

        app = QApplication(sys.argv)
        app.setStyle("Fusion")

        try:
            app.setWindowIcon(QIcon(resource_path("hexa_logo.ico")))
        except Exception:
            pass

        window = IzodMainWindow()

        # Centre on primary screen
        screen = app.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            window.setGeometry(
                sg.x() + max(0, (sg.width() - 1600) // 2),
                sg.y() + max(0, (sg.height() - 900) // 2),
                1600,
                900,
            )

        window.show()
        window.raise_()
        window.activateWindow()

        sys.exit(app.exec())

    except Exception:
        tb = traceback.format_exc()
        try:
            with open(_log_path, "w", encoding="utf-8") as fh:
                fh.write(tb)
        except Exception:
            pass
        # Also show a message box so the user isn't left wondering
        try:
            _a = QApplication.instance() or QApplication(sys.argv)
            from PyQt6.QtWidgets import QMessageBox
            mb = QMessageBox()
            mb.setWindowTitle("Izod – Startup Error")
            mb.setIcon(QMessageBox.Icon.Critical)
            mb.setText("The application failed to start.")
            mb.setDetailedText(tb)
            mb.exec()
        except Exception:
            pass


if __name__ == "__main__":
    main()
