import sys
from collections import deque

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QLinearGradient, QBrush, QPen,
    QPainterPath, QPolygonF, QFontMetrics,
)


# -- Color themes --
THEMES = {
    "default": {
        "fg":     "#00FF00",
        "bg":     "#000000",
        "accent": "#00FF00",
        "warn":   "#FFAA00",
        "crit":   "#FF0000",
    },
    "dark_blue": {
        "fg":     "#4FC3F7",
        "bg":     "#0A1929",
        "accent": "#4FC3F7",
        "warn":   "#FFB74D",
        "crit":   "#EF5350",
    },
    "cyberpunk": {
        "fg":     "#FF00FF",
        "bg":     "#1A002A",
        "accent": "#00FFFF",
        "warn":   "#FFD700",
        "crit":   "#FF1744",
    },
    "nordic": {
        "fg":     "#88C0D0",
        "bg":     "#2E3440",
        "accent": "#A3BE8C",
        "warn":   "#EBCB8B",
        "crit":   "#BF616A",
    },
    "solarized": {
        "fg":     "#93A1A1",
        "bg":     "#002B36",
        "accent": "#2AA198",
        "warn":   "#B58900",
        "crit":   "#DC322F",
    },
    "matrix": {
        "fg":     "#00FF41",
        "bg":     "#000000",
        "accent": "#00FF41",
        "warn":   "#88FF00",
        "crit":   "#FF0000",
    },
    "dracula": {
        "fg":     "#F8F8F2",
        "bg":     "#282A36",
        "accent": "#BD93F9",
        "warn":   "#FFB86C",
        "crit":   "#FF5555",
    },
    "synthwave": {
        "fg":     "#FF71CE",
        "bg":     "#1A1033",
        "accent": "#05FFA1",
        "warn":   "#FFFB96",
        "crit":   "#FF2A6D",
    },
    "amoled": {
        "fg":     "#FFFFFF",
        "bg":     "#000000",
        "accent": "#00E5FF",
        "warn":   "#FFC400",
        "crit":   "#FF3D00",
    },
    "inferno": {
        "fg":     "#FF9E00",
        "bg":     "#1A0500",
        "accent": "#FF6D00",
        "warn":   "#FFD000",
        "crit":   "#FF1744",
    },
    "ice": {
        "fg":     "#CDEEFF",
        "bg":     "#06131F",
        "accent": "#35D0FF",
        "warn":   "#FFD166",
        "crit":   "#FF5C7A",
    },
    "gold": {
        "fg":     "#FFE9A8",
        "bg":     "#1A1400",
        "accent": "#FFC300",
        "warn":   "#FF9F1C",
        "crit":   "#E63946",
    },
    "mint": {
        "fg":     "#C8FFF4",
        "bg":     "#05201B",
        "accent": "#2EE6A6",
        "warn":   "#FFE066",
        "crit":   "#FF6B6B",
    },
    "crimson": {
        "fg":     "#FFC2CC",
        "bg":     "#1A0008",
        "accent": "#FF244E",
        "warn":   "#FFB86C",
        "crit":   "#FF0033",
    },
    "purple_haze": {
        "fg":     "#D9B3FF",
        "bg":     "#12002E",
        "accent": "#9D4EDD",
        "warn":   "#FFD166",
        "crit":   "#FF5C8A",
    },
    "clean_light": {
        "fg":     "#1A1A1A",
        "bg":     "#F2F2F5",
        "accent": "#00A86B",
        "warn":   "#E8A400",
        "crit":   "#E63946",
    },
}


class OverlayWindow(QWidget):
    """Transparent gaming OSD overlay with a live FPS graph and stat bars."""

    HISTORY_LEN = 90

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._fps = 0
        self._fps_min = 0
        self._fps_max = 0
        self._fps_avg = 0
        self._fps_1low = 0
        self._fps_01low = 0
        self._frametime = 0.0
        self._metrics = {}
        self._settings = {}
        self._fps_history = deque(maxlen=self.HISTORY_LEN)

        # Defaults
        self._font_size = 14
        self._fg_color = QColor(0, 255, 0, 255)
        self._bg_color = QColor(0, 0, 0, 160)
        self._accent_color = QColor(0, 255, 0, 255)
        self._warn_color = QColor(255, 170, 0, 255)
        self._crit_color = QColor(255, 0, 0, 255)
        self._position = 0
        self._theme = "default"

        # Visibility flags
        self._show_fps = True
        self._show_cpu = True
        self._show_ram = True
        self._show_gpu = True
        self._show_cpu_temp = True
        self._show_gpu_temp = True
        self._show_mb_temp = True
        self._show_vrm_temp = True
        self._show_cpu_freq = True
        self._show_gpu_freq = True
        self._show_vram = True
        self._show_gpu_power = True
        self._show_gpu_voltage = True
        self._show_gpu_mem_freq = True
        self._show_1low = True
        self._show_01low = True
        self._show_frametime = True

        # Visual style
        self._border_radius = 12
        self._show_gradient = True
        self._show_border = True
        self._opacity = 1.0
        self._show_graph = True

        self._last_size = (0, 0)
        self.resize(300, 190)

    # ------------------------------------------------------------------ data
    def update_data(self, fps, fps_min, fps_max, fps_avg, metrics,
                    fps_1low=0, fps_01low=0, frametime=0.0, app_name=""):
        self._fps = fps
        self._fps_min = fps_min
        self._fps_max = fps_max
        self._fps_avg = fps_avg
        self._fps_1low = fps_1low
        self._fps_01low = fps_01low
        self._frametime = frametime
        self._metrics = metrics
        if fps and fps > 0:
            self._fps_history.append(fps)
        self.update()

    def apply_settings(self, settings: dict):
        self._settings = settings
        self._font_size = settings.get('overlay_font_size', 14)
        self._position = settings.get('overlay_position', 0)

        # Theme
        self._theme = settings.get('overlay_theme', 'default')
        theme = THEMES.get(self._theme, THEMES['default'])

        use_custom = settings.get('overlay_use_custom_colors', False)
        if use_custom:
            fg = settings.get('overlay_fg', '#00FF00')
            bg = settings.get('overlay_bg', '#000000')
        else:
            fg = theme['fg']
            bg = theme['bg']

        self._fg_color = QColor(fg)
        self._fg_color.setAlpha(255)
        self._bg_color = QColor(bg)
        self._bg_color.setAlpha(settings.get('overlay_bg_alpha', 160))
        self._accent_color = QColor(theme['accent'])
        self._warn_color = QColor(theme['warn'])
        self._crit_color = QColor(theme['crit'])

        # Visibility
        self._show_fps = settings.get('show_fps', True)
        self._show_cpu = settings.get('show_cpu', True)
        self._show_ram = settings.get('show_ram', True)
        self._show_gpu = settings.get('show_gpu', True)
        self._show_cpu_temp = settings.get('show_cpu_temp', True)
        self._show_gpu_temp = settings.get('show_gpu_temp', True)
        self._show_mb_temp = settings.get('show_mb_temp', True)
        self._show_vrm_temp = settings.get('show_vrm_temp', True)
        self._show_cpu_freq = settings.get('show_cpu_freq', True)
        self._show_gpu_freq = settings.get('show_gpu_freq', True)
        self._show_vram = settings.get('show_vram', True)
        self._show_gpu_power = settings.get('show_gpu_power', True)
        self._show_gpu_voltage = settings.get('show_gpu_voltage', True)
        self._show_gpu_mem_freq = settings.get('show_gpu_mem_freq', True)
        self._show_1low = settings.get('show_1low', True)
        self._show_01low = settings.get('show_01low', True)
        self._show_frametime = settings.get('show_frametime', True)

        # Visual
        self._border_radius = settings.get('overlay_border_radius', 12)
        self._show_gradient = settings.get('overlay_show_gradient', True)
        self._show_border = settings.get('overlay_show_border', True)
        self._opacity = settings.get('overlay_opacity', 1.0)
        self._show_graph = settings.get('overlay_show_graph', True)

        self._reposition()

    def showEvent(self, event):
        super().showEvent(event)
        self._enable_click_through()

    def _enable_click_through(self):
        """Windows: add WS_EX_TRANSPARENT|WS_EX_LAYERED so clicks pass to the
        game underneath even in fullscreen/borderless."""
        if not sys.platform.startswith("win"):
            return
        try:
            import ctypes
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_NOACTIVATE = 0x08000000

            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            get_l = user32.GetWindowLongPtrW if hasattr(user32, "GetWindowLongPtrW") else user32.GetWindowLongW
            set_l = user32.SetWindowLongPtrW if hasattr(user32, "SetWindowLongPtrW") else user32.SetWindowLongW
            style = get_l(hwnd, GWL_EXSTYLE)
            style |= (WS_EX_LAYERED | WS_EX_TRANSPARENT
                      | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
            set_l(hwnd, GWL_EXSTYLE, style)
        except Exception:
            pass

    def _reposition(self):
        screen = self.screen()
        if screen is None:
            return
        geom = screen.availableGeometry()
        w, h = self.width(), self.height()

        positions = {
            0: (10, 10),
            1: ((geom.width() - w) // 2, 10),
            2: (geom.width() - w - 10, 10),
            3: ((geom.width() - w) // 2, (geom.height() - h) // 2),
            4: (10, geom.height() - h - 10),
            5: ((geom.width() - w) // 2, geom.height() - h - 10),
            6: (geom.width() - w - 10, geom.height() - h - 10),
        }
        x, y = positions.get(self._position, (10, 10))
        self.move(geom.x() + x, geom.y() + y)

    # --------------------------------------------------------------- colors
    def _fps_color(self, fps):
        if fps <= 0:
            return self._fg_color
        if fps >= 60:
            return self._accent_color
        if fps >= 30:
            return self._warn_color
        return self._crit_color

    def _temp_color(self, temp, lo, mid, hi):
        if temp is None:
            return self._fg_color
        if temp < lo:
            return self._accent_color
        elif temp < mid:
            return self._warn_color
        else:
            return self._crit_color

    def _load_color(self, load):
        if load is None:
            return self._fg_color
        if load < 70:
            return self._accent_color
        elif load < 90:
            return self._warn_color
        return self._crit_color

    @staticmethod
    def _with_alpha(color, alpha):
        c = QColor(color)
        c.setAlpha(alpha)
        return c

    # --------------------------------------------------------------- pieces
    def _draw_bg(self, painter, w, h):
        r = self._border_radius
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)

        if self._bg_color.alpha() > 0:
            if self._show_gradient:
                grad = QLinearGradient(0, 0, 0, h)
                base = QColor(self._bg_color)
                top = QColor(base)
                top.setAlpha(int(base.alpha() * self._opacity))
                bot = QColor(base)
                bot.setAlpha(int(base.alpha() * self._opacity * 0.6))
                grad.setColorAt(0, top)
                grad.setColorAt(1, bot)
                painter.fillPath(path, QBrush(grad))
            else:
                bg = QColor(self._bg_color)
                bg.setAlpha(int(bg.alpha() * self._opacity))
                painter.fillPath(path, bg)

        if self._show_border:
            pen = QPen(self._with_alpha(self._accent_color, int(150 * self._opacity)))
            pen.setWidthF(1.4)
            painter.setPen(pen)
            painter.drawPath(path)

    def _draw_text(self, painter, x, y, text, color, font):
        """Text with a soft outline so it stays readable over any scene."""
        painter.setFont(font)
        outline = self._with_alpha(QColor(0, 0, 0), int(200 * self._opacity))
        painter.setPen(outline)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            painter.drawText(int(x + dx), int(y + dy), text)
        c = QColor(color)
        c.setAlpha(int(255 * self._opacity))
        painter.setPen(c)
        painter.drawText(int(x), int(y), text)

    def _draw_graph(self, painter, rect, color):
        hist = list(self._fps_history)
        # frame
        frame = QColor(color)
        frame.setAlpha(int(70 * self._opacity))
        pen = QPen(frame)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 3, 3)

        if len(hist) < 2:
            return

        hi = max(hist)
        lo = min(hist)
        span = max(hi - lo, 1)
        n = len(hist)
        pad = 2.0
        gx = rect.left() + pad
        gy = rect.top() + pad
        gw = rect.width() - pad * 2
        gh = rect.height() - pad * 2

        pts = []
        for i, v in enumerate(hist):
            px = gx + gw * (i / (n - 1))
            py = gy + gh * (1 - (v - lo) / span)
            pts.append(QPointF(px, py))

        # filled area under the curve
        area = QPolygonF(pts + [
            QPointF(gx + gw, gy + gh),
            QPointF(gx, gy + gh),
        ])
        grad = QLinearGradient(0, rect.top(), 0, rect.bottom())
        grad.setColorAt(0, self._with_alpha(color, int(110 * self._opacity)))
        grad.setColorAt(1, self._with_alpha(color, int(10 * self._opacity)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawPolygon(area)

        # curve
        line = QPen(self._with_alpha(color, int(230 * self._opacity)))
        line.setWidthF(1.6)
        painter.setPen(line)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolyline(QPolygonF(pts))

    def _draw_bar(self, painter, x, y, w, h, frac, color):
        frac = max(0.0, min(1.0, frac))
        bg = QRectF(x, y, w, h)
        track = self._with_alpha(self._fg_color, int(45 * self._opacity))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(bg, h / 2, h / 2)
        if frac > 0:
            fill = QRectF(x, y, w * frac, h)
            painter.setBrush(self._with_alpha(color, int(220 * self._opacity)))
            painter.drawRoundedRect(fill, h / 2, h / 2)

    # ---------------------------------------------------------------- paint
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        base = self._font_size
        font = QFont("Consolas", base)
        font.setBold(True)
        font_small = QFont("Consolas", max(8, int(base * 0.72)))
        font_small.setBold(True)
        font_big = QFont("Consolas", int(base * 2.15))
        font_big.setBold(True)
        font_unit = QFont("Consolas", max(9, int(base * 0.85)))
        font_unit.setBold(True)

        fm = QFontMetrics(font)
        fm_small = QFontMetrics(font_small)
        fm_big = QFontMetrics(font_big)
        fm_unit = QFontMetrics(font_unit)

        m = self._metrics
        pad = 12
        line_h = fm.height() + 4

        # --- build stat rows: (label, value_text, color, bar_frac|None) ---
        rows = []

        if self._show_cpu:
            cpu_label = self._settings.get('custom_cpu_name', '') or "CPU"
            cpu_load = m.get('cpu_percent_total')
            cpu_freq = m.get('cpu_freq')
            cpu_temp = m.get('cpu_temp')
            parts = []
            if cpu_load is not None:
                parts.append(f"{cpu_load:.0f}%")
            if self._show_cpu_freq and cpu_freq:
                parts.append(f"{cpu_freq:.0f}MHz")
            if self._show_cpu_temp and cpu_temp is not None:
                parts.append(f"{cpu_temp:.0f}°")
            if parts:
                col = (self._temp_color(cpu_temp, 70, 85, 100)
                       if (self._show_cpu_temp and cpu_temp is not None)
                       else self._load_color(cpu_load))
                frac = (cpu_load / 100.0) if cpu_load is not None else None
                rows.append((cpu_label, "  ".join(parts), col, frac))

        if self._show_gpu:
            gpu_label = self._settings.get('custom_gpu_name', '') or "GPU"
            gpu_load = m.get('gpu_load')
            gpu_freq = m.get('gpu_freq')
            gpu_temp = m.get('gpu_temp')
            parts = []
            if gpu_load is not None:
                parts.append(f"{gpu_load:.0f}%")
            if self._show_gpu_freq and gpu_freq:
                parts.append(f"{gpu_freq}MHz")
            if self._show_gpu_temp and gpu_temp is not None:
                parts.append(f"{gpu_temp:.0f}°")
            if parts:
                col = (self._temp_color(gpu_temp, 70, 85, 95)
                       if (self._show_gpu_temp and gpu_temp is not None)
                       else self._load_color(gpu_load))
                frac = (gpu_load / 100.0) if gpu_load is not None else None
                rows.append((gpu_label, "  ".join(parts), col, frac))

        if self._show_gpu:
            vram_used = m.get('gpu_mem_used')
            vram_total = m.get('gpu_mem_total')
            if self._show_vram and vram_used is not None:
                vt = f" / {vram_total}" if vram_total else ""
                frac = (vram_used / vram_total) if vram_total else None
                rows.append(("VRAM", f"{vram_used:.1f}{vt} GB", self._fg_color, frac))
            gpu_extra = []
            if self._show_gpu_power and m.get('gpu_power') is not None:
                limit = m.get('gpu_power_limit')
                pl = f"/{limit:.0f}" if limit else ""
                gpu_extra.append(f"{m['gpu_power']:.0f}{pl}W")
            if self._show_gpu_voltage and m.get('gpu_voltage') is not None:
                gpu_extra.append(f"{m['gpu_voltage']:.3f}V")
            if self._show_gpu_mem_freq and m.get('gpu_mem_freq') is not None:
                gpu_extra.append(f"{m['gpu_mem_freq']}MHz")
            if gpu_extra:
                rows.append(("PWR", "  ".join(gpu_extra), self._fg_color, None))

        if self._show_ram and m.get('ram_percent') is not None:
            frac = m['ram_percent'] / 100.0
            rows.append(("RAM",
                         f"{m['ram_percent']:.0f}%  {m.get('ram_used_gb', 0)}/{m.get('ram_total_gb', 0)}GB",
                         self._load_color(m['ram_percent']), frac))

        if self._show_mb_temp and m.get('motherboard_temp') is not None:
            t = m['motherboard_temp']
            rows.append(("MB", f"{t:.0f}°", self._temp_color(t, 50, 70, 80), None))
        if self._show_vrm_temp and m.get('vrm_temp') is not None:
            t = m['vrm_temp']
            rows.append(("VRM", f"{t:.0f}°", self._temp_color(t, 60, 90, 110), None))

        # --- header (big FPS) geometry ---
        show_header = self._show_fps
        header_h = 0
        big_txt = str(self._fps) if self._fps > 0 else "--"
        low_bits = []
        if self._show_1low:
            low_bits.append(f"1% {self._fps_1low}")
        if self._show_01low:
            low_bits.append(f".1% {self._fps_01low}")
        if self._show_frametime and self._fps > 0:
            low_bits.append(f"{self._frametime:.1f}ms")
        if show_header:
            # Layout is a vertical stack: big number, then AVG/MIN/MAX,
            # then (optional) lows/frametime. Height must be their SUM.
            sub_lines = 1 + (1 if low_bits else 0)
            header_h = fm_big.ascent() + sub_lines * (fm_small.height() + 2) + 10

        # --- widths ---
        graph_w = 96 if (show_header and self._show_graph) else 0
        # label column width
        label_font = font
        max_label = 0
        for lbl, _v, _c, _f in rows:
            max_label = max(max_label, fm.horizontalAdvance(lbl))
        label_col = max_label + 8 if rows else 0

        # value width
        max_val = 0
        for _lbl, val, _c, _f in rows:
            max_val = max(max_val, fm.horizontalAdvance(val))

        bar_w = 46
        any_bar = any(f is not None for *_, f in rows)
        val_col = max_val + (bar_w + 8 if any_bar else 0)

        body_w = label_col + val_col
        big_w = fm_big.horizontalAdvance(big_txt) + fm_unit.horizontalAdvance(" FPS") + 12
        # header sub text width
        sub1 = f"AVG {self._fps_avg}  MIN {self._fps_min}  MAX {self._fps_max}"
        header_text_w = max(big_w, fm_small.horizontalAdvance(sub1) + 4)
        header_w = header_text_w + graph_w + (10 if graph_w else 0)

        content_w = max(body_w, header_w if show_header else 0)
        total_w = int(content_w + pad * 2)

        rows_h = len(rows) * line_h
        sep_h = 8 if (show_header and rows) else 0
        total_h = int(pad * 2 + (header_h if show_header else 0) + sep_h + rows_h)
        total_h = max(total_h, 40)

        if (total_w, total_h) != self._last_size:
            self._last_size = (total_w, total_h)
            self.resize(total_w, total_h)
            self._reposition()

        # --- draw ---
        self._draw_bg(painter, total_w, total_h)

        # left health accent bar
        accent = self._fps_color(self._fps) if show_header else self._accent_color
        strip = QRectF(pad - 5, pad, 3.5, total_h - pad * 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._with_alpha(accent, int(230 * self._opacity)))
        painter.drawRoundedRect(strip, 1.6, 1.6)

        x0 = pad
        y = pad

        if show_header:
            # big FPS number
            fps_col = self._fps_color(self._fps)
            baseline = y + fm_big.ascent()
            self._draw_text(painter, x0, baseline, big_txt, fps_col, font_big)
            unit_x = x0 + fm_big.horizontalAdvance(big_txt) + 6
            self._draw_text(painter, unit_x, baseline, "FPS",
                            self._with_alpha(self._fg_color, 220), font_unit)

            # sub stats
            sy = baseline + fm_small.height()
            self._draw_text(painter, x0, sy, sub1, self._fg_color, font_small)
            if low_bits:
                sy += fm_small.height() + 2
                self._draw_text(painter, x0, sy, "  ".join(low_bits),
                                self._warn_color, font_small)

            # graph on the right
            if graph_w:
                gx = total_w - pad - graph_w
                gh = header_h - 10
                gy = y + 2
                self._draw_graph(painter,
                                 QRectF(gx, gy, graph_w, max(gh, 22)),
                                 fps_col)

            y += header_h

            if rows:
                # separator
                sepy = y + 3
                pen = QPen(self._with_alpha(self._fg_color, int(50 * self._opacity)))
                pen.setWidthF(1.0)
                painter.setPen(pen)
                painter.drawLine(int(x0), int(sepy), int(total_w - pad), int(sepy))
                y += sep_h

        # stat rows
        for lbl, val, col, frac in rows:
            baseline = y + fm.ascent()
            self._draw_text(painter, x0, baseline, lbl,
                            self._with_alpha(self._fg_color, 210), font)
            vx = x0 + label_col
            self._draw_text(painter, vx, baseline, val, col, font)
            if frac is not None:
                bx = total_w - pad - bar_w
                by = y + (line_h - 6) / 2
                self._draw_bar(painter, bx, by, bar_w, 6, frac, col)
            y += line_h

        painter.end()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
