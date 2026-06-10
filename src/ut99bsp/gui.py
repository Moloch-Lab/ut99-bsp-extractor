import sys, os, threading, math, time

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QFileDialog, QFrame,
    QMessageBox, QPlainTextEdit, QListWidget, QComboBox,
    QListWidgetItem, QDialog, QMenu, QSplitter, QSizePolicy,
    QStatusBar, QToolBar,
)
from PySide6.QtCore import (
    Qt, Signal, QObject, QTimer, QPointF, QSettings, QSize,
)
from PySide6.QtGui import (
    QDragEnterEvent, QDropEvent, QFont, QPainter, QPen, QColor,
    QMouseEvent, QWheelEvent, QAction, QKeySequence, QIcon, QPixmap,
)

from ut99bsp import extract_map, ExtractionResult

MAG = "\U0001F4DD"
SETTINGS_GEO = "Settings"


SETTINGS_ORG = "MolochLab"
SETTINGS_APP = "UT99-BSP-Extractor"

STYLESHEET = """
QMainWindow {
    background-color: #11111b;
}
QToolBar {
    background-color: #181825;
    border: none;
    border-bottom: 1px solid #313244;
    spacing: 6px;
    padding: 4px 8px;
}
QToolBar QToolButton {
    background-color: transparent;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: bold;
}
QToolBar QToolButton:hover { background-color: #313244; }
QToolBar QToolButton:pressed { background-color: #45475a; }
QToolBar QToolButton:disabled { color: #585b70; }
QToolBar QLabel { color: #6c7086; font-size: 12px; }
QLabel {
    color: #cdd6f4;
    font-size: 13px;
}
QPushButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    padding: 8px 20px;
    border-radius: 8px;
    font-weight: bold;
    font-size: 13px;
}
QPushButton:hover { background-color: #74c7ec; }
QPushButton:pressed { background-color: #89dceb; }
QPushButton:disabled { background-color: #313244; color: #585b70; }
QPushButton#dangerBtn {
    background-color: #f38ba8;
}
QPushButton#dangerBtn:hover { background-color: #eba0ac; }
QPushButton#dangerBtn:disabled { background-color: #313244; color: #585b70; }
QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
    min-width: 120px;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #1e1e2e;
    color: #cdd6f4;
    selection-background-color: #45475a;
    border: 1px solid #45475a;
    border-radius: 4px;
    outline: none;
}
QProgressBar {
    border: none;
    border-radius: 8px;
    background-color: #313244;
    height: 22px;
    text-align: center;
    color: #cdd6f4;
    font-size: 12px;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: #a6e3a1;
    border-radius: 8px;
}
QPlainTextEdit {
    background-color: #11111b;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 8px;
    font-family: "Cascadia Code", "JetBrains Mono", monospace;
    font-size: 12px;
    padding: 8px;
    selection-background-color: #45475a;
}
QDialog {
    background-color: #1e1e2e;
}
QListWidget {
    background-color: #11111b;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 8px;
    font-size: 12px;
    outline: none;
}
QListWidget::item {
    padding: 6px 10px;
    border-radius: 4px;
    margin: 1px 4px;
}
QListWidget::item:selected {
    background-color: #45475a;
}
QListWidget::item:hover {
    background-color: #313244;
}
QFrame#dropArea {
    background-color: #181825;
    border: 2px dashed #45475a;
    border-radius: 12px;
}
QFrame#dropArea:hover { border-color: #89b4fa; background-color: #1e1e2e; }
QFrame#statCard {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 10px;
}
QStatusBar {
    background-color: #181825;
    border-top: 1px solid #313244;
    color: #6c7086;
    font-size: 12px;
}
QScrollBar:vertical {
    background-color: #11111b;
    width: 8px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 0; }
"""


class WorkerSignals(QObject):
    progress = Signal(str, int)
    map_done = Signal(str, object)
    finished = Signal()
    error = Signal(str)


class ExtractionWorker(threading.Thread):
    def __init__(self, map_paths, fmt="obj", output_dir=None, export_opts=None):
        super().__init__()
        self.map_paths = map_paths
        self.fmt = fmt
        self.output_dir = output_dir
        self.export_opts = export_opts or {}
        self.signals = WorkerSignals()
        self.start_time = 0

    def run(self):
        self.start_time = time.time()
        total = len(self.map_paths)
        for idx, mp in enumerate(self.map_paths):
            base_name = os.path.splitext(os.path.basename(mp))[0]
            self.signals.progress.emit(f"[{idx+1}/{total}] {base_name}", 0)
            try:
                out_dir = self.output_dir or os.path.join(os.path.dirname(mp), "bsp_export")
                os.makedirs(out_dir, exist_ok=True)
                ext = ".obj" if self.fmt in ("obj", "objmtl") else ".gltf"
                out_path = os.path.join(out_dir, base_name + ext)
                result = extract_map(mp, out_path, fmt=self.fmt, **self.export_opts)
                self.signals.map_done.emit(mp, result)
            except Exception as e:
                self.signals.error.emit(f"{base_name}: {e}")
        self.signals.finished.emit()


class StatCard(QFrame):
    def __init__(self, label, value="—", icon=""):
        super().__init__()
        self.setObjectName("statCard")
        self.setFixedHeight(72)
        self.setMinimumWidth(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        h = QHBoxLayout()
        h.setSpacing(6)
        if icon:
            ic = QLabel(icon)
            ic.setStyleSheet("font-size: 18px;")
            h.addWidget(ic)
        self.label_w = QLabel(label)
        self.label_w.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: bold; text-transform: uppercase;")
        h.addWidget(self.label_w)
        h.addStretch()
        layout.addLayout(h)

        self.value_w = QLabel(str(value))
        self.value_w.setStyleSheet("color: #cdd6f4; font-size: 22px; font-weight: bold;")
        layout.addWidget(self.value_w)

    def set_value(self, v):
        self.value_w.setText(str(v))


class DropArea(QFrame):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName("dropArea")
        self.setAcceptDrops(True)
        self.setMinimumHeight(110)
        self.setCursor(Qt.DragCopyCursor)

        l = QVBoxLayout()
        l.setAlignment(Qt.AlignCenter)
        l.setSpacing(6)

        self.icon = QLabel("\U0001F4C2")
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setStyleSheet("font-size: 32px;")
        l.addWidget(self.icon)

        self.label = QLabel("Drop .unr files here")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #6c7086; font-size: 14px;")
        l.addWidget(self.label)

        sub = QLabel("or click Browse below")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #45475a; font-size: 11px;")
        l.addWidget(sub)

        self.setLayout(l)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(
                "QFrame#dropArea { background-color: #1e1e2e; "
                "border: 2px solid #89b4fa; border-radius: 12px; }"
            )

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".unr"):
                paths.append(path)
        if paths:
            self.files_dropped.emit(paths)


class PreviewWidget(QWidget):
    def __init__(self, triangles, parent=None):
        super().__init__(parent)
        self.triangles = triangles
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)

        self.rot_x = 0.0
        self.rot_y = 0.0
        self.zoom = 1.0
        self.last_pos = None

        all_pts = [p for t in triangles for p in t]
        if all_pts:
            xs = [p[0] for p in all_pts]
            ys = [p[1] for p in all_pts]
            zs = [p[2] for p in all_pts]
            self.center = (
                (min(xs) + max(xs)) / 2,
                (min(ys) + max(ys)) / 2,
                (min(zs) + max(zs)) / 2,
            )
            r = math.sqrt(
                (max(xs) - min(xs)) ** 2
                + (max(ys) - min(ys)) ** 2
                + (max(zs) - min(zs)) ** 2
            )
            self.radius = r / 2 if r > 0 else 100
        else:
            self.center = (0, 0, 0)
            self.radius = 100

    def _rotate(self, p):
        x, y, z = p
        cx, cy, cz = self.center
        x -= cx; y -= cy; z -= cz
        rx, ry = self.rot_x, self.rot_y
        crx, srx = math.cos(rx), math.sin(rx)
        cry, sry = math.cos(ry), math.sin(ry)
        y, z = y * crx - z * srx, y * srx + z * crx
        x, z = x * cry + z * sry, -x * sry + z * cry
        return (x, y, z)

    def _project(self, p, w, h):
        d = max(self.radius * 2.5, 1.0)
        s = min(w, h) * 0.4 * self.zoom
        return QPointF(w / 2 + p[0] * s / d, h / 2 - p[1] * s / d)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#11111b"))

        w, h = self.width(), self.height()

        bg_pen = QPen(QColor("#181825"), 1.5)
        bg_pen.setCosmetic(True)
        p.setPen(bg_pen)
        cx, cy = w / 2, h / 2
        r = min(w, h) * 0.45
        for a in range(0, 360, 30):
            rad = math.radians(a)
            p.drawLine(
                QPointF(cx, cy),
                QPointF(cx + r * math.cos(rad), cy - r * math.sin(rad))
            )
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.drawEllipse(QPointF(cx, cy), r * 0.66, r * 0.66)
        p.drawEllipse(QPointF(cx, cy), r * 0.33, r * 0.33)

        pen = QPen(QColor("#89b4fa"), 1.2)
        pen.setCosmetic(True)
        p.setPen(pen)

        for t in self.triangles:
            pts = [self._project(self._rotate(v), w, h) for v in t]
            p.drawLine(pts[0], pts[1])
            p.drawLine(pts[1], pts[2])
            p.drawLine(pts[2], pts[0])

        p.end()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.last_pos is not None and event.buttons() & Qt.LeftButton:
            dx = event.position().x() - self.last_pos.x()
            dy = event.position().y() - self.last_pos.y()
            self.rot_y += dx * 0.01
            self.rot_x += dy * 0.01
            self.update()
        self.last_pos = event.position()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.last_pos = None

    def wheelEvent(self, event: QWheelEvent):
        self.zoom *= 1.0 + event.angleDelta().y() * 0.001
        self.zoom = max(0.1, min(10.0, self.zoom))
        self.update()


class PreviewDialog(QDialog):
    def __init__(self, triangles, title="3D Preview", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 500)
        self.resize(900, 650)
        l = QVBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(0)
        self.preview = PreviewWidget(triangles)
        l.addWidget(self.preview, stretch=1)

        bar = QFrame()
        bar.setStyleSheet("background-color: #181825; border-top: 1px solid #313244;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(12, 6, 12, 6)
        hint = QLabel("\U0001F5B2  Drag to rotate  ·  Scroll to zoom")
        hint.setStyleSheet("color: #6c7086; font-size: 12px;")
        bl.addWidget(hint)
        bl.addStretch()
        poly_count = QLabel(f"{len(triangles)} triangles")
        poly_count.setStyleSheet("color: #a6adc8; font-size: 12px;")
        bl.addWidget(poly_count)

        reset_btn = QPushButton("Reset View")
        reset_btn.setFixedHeight(28)
        reset_btn.setStyleSheet(
            "QPushButton { background-color: #313244; color: #cdd6f4; "
            "padding: 4px 14px; font-size: 11px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #45475a; }"
        )
        reset_btn.clicked.connect(lambda: (
            setattr(self.preview, 'rot_x', 0.0),
            setattr(self.preview, 'rot_y', 0.0),
            setattr(self.preview, 'zoom', 1.0),
            self.preview.update()
        ))
        bl.addWidget(reset_btn)
        l.addWidget(bar)


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Preferences")
        self.setFixedSize(380, 220)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; font-size: 13px; }
            QCheckBox {
                color: #cdd6f4; font-size: 13px; spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px; height: 18px; border-radius: 4px;
                border: 2px solid #45475a; background: #11111b;
            }
            QCheckBox::indicator:checked {
                background: #89b4fa; border-color: #89b4fa;
            }
            QPushButton {
                background-color: #89b4fa; color: #1e1e2e;
                border: none; padding: 6px 20px; border-radius: 6px;
                font-weight: bold; font-size: 12px;
            }
            QPushButton:hover { background-color: #74c7ec; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("What to export:")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #a6adc8;")
        layout.addWidget(title)

        self.geo_check = QCheckBox("Export map geometry")
        self.geo_check.setChecked(True)
        layout.addWidget(self.geo_check)

        self.tex_check = QCheckBox("Export textures (PNG from .utx packages)")
        self.tex_check.setChecked(False)
        layout.addWidget(self.tex_check)

        self.ref_check = QCheckBox("Include texture references in output")
        self.ref_check.setChecked(True)
        layout.addWidget(self.ref_check)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

        # Restore saved state
        parent = self.parent()
        if hasattr(parent, 'settings'):
            s = parent.settings
            self.geo_check.setChecked(s.value("export_geometry", True, type=bool))
            self.tex_check.setChecked(s.value("export_textures", False, type=bool))
            self.ref_check.setChecked(s.value("include_texture_refs", True, type=bool))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self.setWindowTitle("UT99 BSP Extractor")
        self.setMinimumSize(720, 680)
        self.setStyleSheet(STYLESHEET)
        self.setAcceptDrops(True)

        self.map_paths = []
        self.running = False
        self.results = []
        self.extract_start_time = 0
        self.output_dir = ""

        self._setup_ui()
        self._setup_shortcuts()
        self._restore_settings()

        self._log("Ready — drop .unr files or click Browse.")
        self._update_stats()

    # ── UI Setup ─────────────────────────────────────────────────

    def _setup_ui(self):
        self._build_toolbar()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(16, 12, 16, 12)

        root.addWidget(self._build_top_bar())
        root.addWidget(self._build_stats_row())
        root.addWidget(self._build_queue_section())
        root.addWidget(self._build_controls())
        root.addWidget(self._build_output_dir_row())
        root.addWidget(self._build_progress_section())
        root.addWidget(self._build_log(), stretch=1)

        self.statusBar().showMessage("Ready")

    def _build_toolbar(self):
        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(tb)

        self.add_act = QAction("\U0001F4C2  Add Files", self)
        self.add_act.triggered.connect(self._browse)
        tb.addAction(self.add_act)

        self.extract_act = QAction("\u25B6  Extract All", self)
        self.extract_act.triggered.connect(self._extract)
        self.extract_act.setEnabled(False)
        tb.addAction(self.extract_act)

        self.preview_act = QAction("\U0001F50D  Preview", self)
        self.preview_act.triggered.connect(self._open_preview)
        self.preview_act.setEnabled(False)
        tb.addAction(self.preview_act)

        tb.addSeparator()

        self.clear_act = QAction("\u2716  Clear", self)
        self.clear_act.triggered.connect(self._clear_queue)
        tb.addAction(self.clear_act)

        self.prefs_act = QAction("\u2699  Preferences", self)
        self.prefs_act.triggered.connect(self._open_prefs)
        tb.addAction(self.prefs_act)

        tb.addSeparator()

        fmt_lbl = QLabel("  Format:")
        tb.addWidget(fmt_lbl)
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["obj (raw)", "obj + mtl", "glTF"])
        self.fmt_combo.currentIndexChanged.connect(self._save_settings)
        tb.addWidget(self.fmt_combo)

    def _build_top_bar(self):
        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self._on_files_dropped)
        return self.drop_area

    def _build_stats_row(self):
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.stat_maps = StatCard("Maps", "0", "\U0001F4DD")
        self.stat_fmt = StatCard("Format", "obj + mtl", "\u2699")
        self.stat_polys = StatCard("Total Polys", "—", "\u25B3")
        self.stat_time = StatCard("Last Run", "—", "\u23F1")
        for s in [self.stat_maps, self.stat_fmt, self.stat_polys, self.stat_time]:
            row.addWidget(s)
        return w

    def _build_queue_section(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(4)

        hl = QHBoxLayout()
        hl.addWidget(QLabel("Map Queue"))
        hl.addStretch()
        self.queue_count_lbl = QLabel("0 files")
        self.queue_count_lbl.setStyleSheet("color: #6c7086; font-size: 11px;")
        hl.addWidget(self.queue_count_lbl)
        l.addLayout(hl)

        self.queue_list = QListWidget()
        self.queue_list.setMinimumHeight(80)
        self.queue_list.setMaximumHeight(160)
        self.queue_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.queue_list.customContextMenuRequested.connect(self._queue_context_menu)
        self.queue_list.itemDoubleClicked.connect(self._on_queue_double_click)
        l.addWidget(self.queue_list)
        return w

    def _build_controls(self):
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.browse_btn = QPushButton("\U0001F4C2  Browse Files...")
        self.browse_btn.clicked.connect(self._browse)
        row.addWidget(self.browse_btn)

        self.remove_btn = QPushButton("\u2716  Remove Selected")
        self.remove_btn.setObjectName("dangerBtn")
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self._remove_selected)
        row.addWidget(self.remove_btn)

        row.addStretch()

        self.extract_btn = QPushButton("\u25B6  Extract All")
        self.extract_btn.setEnabled(False)
        self.extract_btn.clicked.connect(self._extract)
        self.extract_btn.setFixedWidth(150)
        row.addWidget(self.extract_btn)
        return w

    def _build_output_dir_row(self):
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        lbl = QLabel("Output:")
        lbl.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        row.addWidget(lbl)
        self.output_dir_lbl = QLabel("Same as map files (bsp_export/)")
        self.output_dir_lbl.setStyleSheet("color: #a6adc8; font-size: 12px;")
        self.output_dir_lbl.setWordWrap(True)
        row.addWidget(self.output_dir_lbl, stretch=1)
        self.output_btn = QPushButton("Browse...")
        self.output_btn.setFixedHeight(26)
        self.output_btn.setStyleSheet(
            "QPushButton { background-color: #313244; color: #cdd6f4; "
            "padding: 4px 14px; font-size: 11px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #45475a; }"
        )
        self.output_btn.clicked.connect(self._browse_output_dir)
        row.addWidget(self.output_btn)
        self.output_reset_btn = QPushButton("Reset")
        self.output_reset_btn.setFixedHeight(26)
        self.output_reset_btn.setStyleSheet(
            "QPushButton { background-color: #313244; color: #cdd6f4; "
            "padding: 4px 14px; font-size: 11px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #45475a; }"
        )
        self.output_reset_btn.clicked.connect(self._reset_output_dir)
        row.addWidget(self.output_reset_btn)
        return w

    def _build_progress_section(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(4)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        l.addWidget(self.progress)

        hl = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        hl.addWidget(self.status_label)
        hl.addStretch()
        self.eta_label = QLabel("")
        self.eta_label.setStyleSheet("color: #585b70; font-size: 11px;")
        hl.addWidget(self.eta_label)
        l.addLayout(hl)
        return w

    def _build_log(self):
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(300)
        self.log.setPlaceholderText("Log output will appear here...")
        return self.log

    def _setup_shortcuts(self):
        a = QAction("Add Files", self, shortcut=QKeySequence.Open, triggered=self._browse)
        self.addAction(a)

        b = QAction("Extract All", self, shortcut=QKeySequence("Ctrl+E"), triggered=self._extract)
        self.addAction(b)

        c = QAction("Remove Selected", self, shortcut=QKeySequence.Delete, triggered=self._remove_selected)
        self.addAction(c)

        d = QAction("Preferences", self, shortcut=QKeySequence("Ctrl+P"), triggered=self._open_prefs)
        self.addAction(d)

    # ── Settings ──────────────────────────────────────────────────

    def _restore_settings(self):
        geom = self.settings.value("window_geometry")
        if geom:
            self.restoreGeometry(geom)
        else:
            self.resize(800, 700)

        fmt = self.settings.value("format", 1, type=int)
        if 0 <= fmt <= 2:
            self.fmt_combo.setCurrentIndex(fmt)

        out_dir = self.settings.value("output_dir", "")
        if out_dir and os.path.isdir(out_dir):
            self.output_dir = out_dir
            self._update_output_label()

    def _save_settings(self):
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.settings.setValue("format", self.fmt_combo.currentIndex())
        if self.output_dir:
            self.settings.setValue("output_dir", self.output_dir)

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)

    # ── Helpers ───────────────────────────────────────────────────

    def _log(self, msg):
        self.log.appendPlainText(msg)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _update_stats(self):
        n = len(self.map_paths)
        self.stat_maps.set_value(n)
        self.stat_fmt.set_value(self.fmt_combo.currentText())
        if self.results:
            total = sum(r.polygons for r in self.results)
            self.stat_polys.set_value(total)
        self.queue_count_lbl.setText(f"{n} file{'s' if n != 1 else ''}")
        self.remove_btn.setEnabled(bool(self.queue_list.selectedItems()))

    def _update_queue_ui(self):
        n = self.queue_list.count()
        can_run = n > 0 and not self.running
        if n == 0:
            self.drop_area.label.setText("Drop .unr files here")
            self.extract_btn.setEnabled(False)
            self.extract_act.setEnabled(False)
        else:
            self.drop_area.label.setText(f"{n} map{'s' if n != 1 else ''} loaded")
            self.extract_btn.setEnabled(can_run)
            self.extract_act.setEnabled(can_run)
        self._update_stats()

    def _add_paths(self, paths):
        added = 0
        for p in paths:
            absp = os.path.abspath(p)
            if absp not in self.map_paths:
                self.map_paths.append(absp)
                item = QListWidgetItem(os.path.basename(absp))
                item.setToolTip(absp)
                item.setData(Qt.UserRole, absp)
                self.queue_list.addItem(item)
                added += 1
        if added:
            self._update_queue_ui()
            self._log(f"Added {added} map{'s' if added != 1 else ''}")

    def _remove_selected(self):
        items = self.queue_list.selectedItems()
        if not items:
            return
        for item in items:
            path = item.data(Qt.UserRole)
            if path in self.map_paths:
                self.map_paths.remove(path)
            self.queue_list.takeItem(self.queue_list.row(item))
        self._update_queue_ui()
        self._log("Removed selected items.")

    def _queue_context_menu(self, pos):
        item = self.queue_list.itemAt(pos)
        menu = QMenu(self)
        if item:
            menu.addAction("Remove", self._remove_selected)
            menu.addAction("Clear All", self._clear_queue)
            menu.addSeparator()
            path = item.data(Qt.UserRole)
            if path:
                menu.addAction("\U0001F4C2  Show in Folder", lambda: self._show_in_folder(path))
        else:
            menu.addAction("Clear All", self._clear_queue)
        menu.exec(self.queue_list.mapToGlobal(pos))

    def _show_in_folder(self, path):
        import subprocess
        folder = os.path.dirname(path)
        try:
            subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass

    def _on_queue_double_click(self, item):
        path = item.data(Qt.UserRole)
        if path:
            self._log(f"Quick extract: {os.path.basename(path)}...")
            self._extract_single(path)

    def _extract_single(self, path):
        """Extract a single map without blocking the UI thread."""
        if self.running:
            return
        self.running = True
        self.extract_btn.setEnabled(False)
        self.add_act.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status_label.setText(f"Extracting {os.path.basename(path)}...")

        worker = ExtractionWorker([path], fmt=self._fmt_to_arg(), output_dir=self.output_dir or None,
                                   export_opts=self._export_opts())
        worker.signals.map_done.connect(lambda p, r: (
            self._log(f"  \u2714 {os.path.basename(p)}: {r.polygons} polys"),
            self.results.append(r),
            self.preview_act.setEnabled(True),
            self.stat_polys.set_value(sum(x.polygons for x in self.results)),
            self.stat_time.set_value(time.strftime("%H:%M")),
        ))
        worker.signals.finished.connect(lambda: (
            setattr(self, 'running', False),
            self.progress.setValue(100),
            self.status_label.setText("Done!"),
            self.extract_btn.setEnabled(True),
            self.add_act.setEnabled(True),
            self._update_queue_ui(),
        ))
        worker.signals.error.connect(lambda msg: (
            self._log(f"  \u2716 {msg}"),
        ))
        worker.start()

    # ── Events ────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".unr"):
                paths.append(path)
        if paths:
            self._add_paths(paths)

    def _on_files_dropped(self, paths):
        self._add_paths(paths)

    def _browse(self):
        last_dir = self.settings.value("last_dir", "")
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select UT99 Maps", last_dir, "Unreal Maps (*.unr);;All Files (*)"
        )
        if paths:
            self.settings.setValue("last_dir", os.path.dirname(paths[0]))
            self._add_paths(paths)

    def _browse_output_dir(self):
        last_dir = self.output_dir or self.settings.value("output_dir", "")
        d = QFileDialog.getExistingDirectory(self, "Select Output Directory", last_dir)
        if d:
            self.output_dir = d
            self.settings.setValue("output_dir", d)
            self._update_output_label()

    def _reset_output_dir(self):
        self.output_dir = ""
        self._update_output_label()

    def _update_output_label(self):
        if self.output_dir:
            self.output_dir_lbl.setText(self.output_dir)
        else:
            self.output_dir_lbl.setText("Same as map files (bsp_export/)")

    def _clear_queue(self):
        self.map_paths.clear()
        self.queue_list.clear()
        self._update_queue_ui()
        self._log("Queue cleared.")

    def _fmt_to_arg(self):
        return ["obj", "objmtl", "gltf"][self.fmt_combo.currentIndex()]

    def _open_prefs(self):
        dlg = PreferencesDialog(self)
        if dlg.exec():
            s = self.settings
            s.setValue("export_geometry", dlg.geo_check.isChecked())
            s.setValue("export_textures", dlg.tex_check.isChecked())
            s.setValue("include_texture_refs", dlg.ref_check.isChecked())

    def _export_opts(self):
        s = self.settings
        return {
            'export_geometry': s.value("export_geometry", True, type=bool),
            'export_textures': s.value("export_textures", False, type=bool),
            'include_texture_refs': s.value("include_texture_refs", True, type=bool),
        }

    def _extract(self):
        if not self.map_paths or self.running:
            return

        self.running = True
        self.results.clear()
        self.preview_act.setEnabled(False)
        self.extract_act.setEnabled(False)
        self.extract_btn.setEnabled(False)
        self.add_act.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.extract_start_time = time.time()

        n = len(self.map_paths)
        self.status_label.setText(f"Starting batch ({n} maps)...")
        self._log(f"\u2500\u2500 Batch extraction ({n} maps) \u2500\u2500")

        fmt = self._fmt_to_arg()
        self.worker = ExtractionWorker(list(self.map_paths), fmt=fmt, output_dir=self.output_dir or None,
                                        export_opts=self._export_opts())
        self.worker.signals.progress.connect(self._on_progress)
        self.worker.signals.map_done.connect(self._on_map_done)
        self.worker.signals.finished.connect(self._on_batch_done)
        self.worker.signals.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, msg, pct):
        if pct is not None:
            self.progress.setValue(pct)
        self.status_label.setText(msg)
        # Show ETA
        elapsed = time.time() - self.extract_start_time
        if pct > 0 and self.worker and self.worker.map_paths:
            total = len(self.worker.map_paths)
            done = self.queue_list.count() - len(self.worker.map_paths) + 1
            if done > 0:
                per_item = elapsed / done
                remaining = (total - done) * per_item
                if remaining > 0:
                    self.eta_label.setText(f"ETA: {remaining:.0f}s")

    def _on_map_done(self, map_path, result: ExtractionResult):
        msg = f"  \u2714 {os.path.basename(map_path)}: {result.polygons} polys -> {result.output_path}"
        if result.textures_extracted:
            msg += f", {result.textures_extracted} textures"
        self._log(msg)
        self.results.append(result)
        self.stat_polys.set_value(sum(r.polygons for r in self.results))

    def _on_batch_done(self):
        elapsed = time.time() - self.extract_start_time
        self._log(f"\u2500\u2500 Batch complete ({elapsed:.1f}s) \u2500\u2500")
        self.status_label.setText(f"All maps extracted ({elapsed:.1f}s)")
        self.progress.setValue(100)
        self.eta_label.setText("")
        self.stat_time.set_value(time.strftime("%H:%M"))
        self.running = False
        self.extract_act.setEnabled(True)
        self.extract_btn.setEnabled(True)
        self.add_act.setEnabled(True)
        self.browse_btn.setEnabled(True)
        if self.results:
            self.preview_act.setEnabled(True)
        self.worker = None
        self._update_queue_ui()

    def _on_error(self, msg):
        self._log(f"  \u2716 Error: {msg}")

    def _open_preview(self):
        if not self.results:
            return
        r = self.results[-1]
        if not r.triangles:
            QMessageBox.information(self, "Preview", "No triangle data available.")
            return
        dlg = PreviewDialog(
            r.triangles,
            title=f"3D Preview \u2014 {r.map_name} ({r.polygons} polys, {r.format})"
        )
        dlg.exec()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("UT99 BSP Extractor")
    app.setOrganizationName(SETTINGS_ORG)

    f = QFont()
    f.setFamilies(["Segoe UI", "SF Pro Display", "Helvetica Neue", "Arial"])
    f.setPointSize(10)
    app.setFont(f)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())
