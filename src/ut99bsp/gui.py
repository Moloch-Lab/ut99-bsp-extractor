#!/usr/bin/env python3

import sys, os, threading, math

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QFileDialog,
    QFrame, QMessageBox, QGroupBox, QGridLayout, QPlainTextEdit,
    QListWidget, QComboBox, QListWidgetItem, QDialog,
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QPointF
from PySide6.QtGui import (
    QDragEnterEvent, QDropEvent, QFont, QPainter, QPen, QColor,
    QMouseEvent, QWheelEvent,
)

from ut99bsp import extract_map, ExtractionResult


STYLESHEET = """
QMainWindow { background-color: #1e1e2e; }
QLabel {
    color: #cdd6f4;
    font-size: 13px;
}
QPushButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    padding: 8px 18px;
    border-radius: 6px;
    font-weight: bold;
    font-size: 13px;
}
QPushButton:hover { background-color: #74c7ec; }
QPushButton:pressed { background-color: #89dceb; }
QPushButton:disabled { background-color: #45475a; color: #6c7086; }
QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    min-width: 100px;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    selection-background-color: #45475a;
}
QProgressBar {
    border: none;
    border-radius: 6px;
    background-color: #313244;
    height: 20px;
    text-align: center;
    color: #cdd6f4;
    font-size: 12px;
}
QProgressBar::chunk {
    background-color: #a6e3a1;
    border-radius: 6px;
}
QPlainTextEdit {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    font-family: "Cascadia Code", "JetBrains Mono", monospace;
    font-size: 12px;
    padding: 6px;
}
QDialog { background-color: #1e1e2e; }
QGroupBox {
    color: #cdd6f4;
    font-weight: bold;
    border: 1px solid #45475a;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QListWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    font-size: 12px;
}
QListWidget::item { padding: 4px 8px; }
QListWidget::item:selected { background-color: #45475a; }
QFrame#dropArea {
    background-color: #313244;
    border: 2px dashed #585b70;
    border-radius: 10px;
}
QFrame#dropArea:hover { border-color: #89b4fa; }
"""


class WorkerSignals(QObject):
    progress = Signal(str, int)
    map_done = Signal(str, object)
    finished = Signal()
    error = Signal(str)


class ExtractionWorker(threading.Thread):
    def __init__(self, map_paths, fmt="obj"):
        super().__init__()
        self.map_paths = map_paths
        self.fmt = fmt
        self.signals = WorkerSignals()

    def run(self):
        total = len(self.map_paths)
        for idx, mp in enumerate(self.map_paths):
            base_name = os.path.splitext(os.path.basename(mp))[0]
            self.signals.progress.emit(f"[{idx+1}/{total}] {base_name}...", 0)
            try:
                out_dir = os.path.join(os.path.dirname(mp), "bsp_export")
                os.makedirs(out_dir, exist_ok=True)
                ext = ".obj" if self.fmt in ("obj", "objmtl") else ".gltf"
                out_path = os.path.join(out_dir, base_name + ext)
                result = extract_map(mp, out_path, fmt=self.fmt)
                self.signals.map_done.emit(mp, result)
            except Exception as e:
                self.signals.error.emit(f"{base_name}: {e}")
        self.signals.finished.emit()


class DropArea(QFrame):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName("dropArea")
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        self.label = QLabel("Drag & drop .unr files here\nor click Browse")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #6c7086; font-size: 14px;")
        layout.addWidget(self.label)
        self.setLayout(layout)

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

        # Compute center and radius of the geometry
        all_pts = [p for t in triangles for p in t]
        if all_pts:
            xs = [p[0] for p in all_pts]
            ys = [p[1] for p in all_pts]
            zs = [p[2] for p in all_pts]
            cx = (min(xs) + max(xs)) / 2
            cy = (min(ys) + max(ys)) / 2
            cz = (min(zs) + max(zs)) / 2
            self.center = (cx, cy, cz)
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
        x -= cx
        y -= cy
        z -= cz
        rx = self.rot_x
        ry = self.rot_y
        cos_rx, sin_rx = math.cos(rx), math.sin(rx)
        cos_ry, sin_ry = math.cos(ry), math.sin(ry)
        y, z = y * cos_rx - z * sin_rx, y * sin_rx + z * cos_rx
        x, z = x * cos_ry + z * sin_ry, -x * sin_ry + z * cos_ry
        return (x, y, z)

    def _project(self, p, w, h):
        d = max(self.radius * 2.5, 1.0)
        s = min(w, h) * 0.4 * self.zoom
        x, y, z = p
        return QPointF(w / 2 + x * s / d, h / 2 - y * s / d)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#1e1e2e"))
        pen = QPen(QColor("#89b4fa"), 0.8)
        p.setPen(pen)

        w = self.width()
        h = self.height()

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
        delta = event.angleDelta().y()
        self.zoom *= 1.0 + delta * 0.001
        self.zoom = max(0.1, min(10.0, self.zoom))
        self.update()


class PreviewDialog(QDialog):
    def __init__(self, triangles, title="3D Preview", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 500)
        self.resize(800, 600)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.preview = PreviewWidget(triangles)
        layout.addWidget(self.preview)
        label = QLabel("Drag to rotate | Scroll to zoom")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #6c7086; padding: 4px;")
        layout.addWidget(label)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UT99 BSP Extractor")
        self.setMinimumSize(640, 600)
        self.setStyleSheet(STYLESHEET)

        self.map_paths = []
        self.running = False
        self.results = []

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Drop area
        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self._on_files_dropped)
        layout.addWidget(self.drop_area)

        # Browse row
        browse_row = QHBoxLayout()
        self.browse_btn = QPushButton("Browse Files...")
        self.browse_btn.clicked.connect(self._browse)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_queue)
        browse_row.addStretch()
        browse_row.addWidget(self.clear_btn)
        browse_row.addWidget(self.browse_btn)
        layout.addLayout(browse_row)

        # Map queue
        self.queue_list = QListWidget()
        self.queue_list.setMinimumHeight(100)
        self.queue_list.setMaximumHeight(180)
        layout.addWidget(QLabel("Map Queue:"))
        layout.addWidget(self.queue_list)

        # Format row + extract + preview
        ctrl_row = QHBoxLayout()
        ctrl_row.addWidget(QLabel("Format:"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["obj (raw)", "obj + mtl", "glTF"])
        self.fmt_combo.setCurrentIndex(1)
        ctrl_row.addWidget(self.fmt_combo)
        ctrl_row.addStretch()
        self.preview_btn = QPushButton("Preview")
        self.preview_btn.setEnabled(False)
        self.preview_btn.clicked.connect(self._open_preview)
        ctrl_row.addWidget(self.preview_btn)
        self.extract_btn = QPushButton("Extract All")
        self.extract_btn.setEnabled(False)
        self.extract_btn.clicked.connect(self._extract)
        ctrl_row.addWidget(self.extract_btn)
        layout.addLayout(ctrl_row)

        # Progress
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(self.status_label)

        # Log
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(300)
        layout.addWidget(self.log, stretch=1)

        self._log("Ready — drop .unr files or click Browse.")

    # ── helpers ─────────────────────────────────────────────────────

    def _log(self, msg):
        self.log.appendPlainText(msg)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _update_queue_ui(self):
        n = self.queue_list.count()
        if n == 0:
            self.drop_area.label.setText("Drag & drop .unr files here\nor click Browse")
            self.drop_area.label.setStyleSheet("color: #6c7086; font-size: 14px;")
            self.extract_btn.setEnabled(False)
        else:
            self.drop_area.label.setText(f"{n} map{'s' if n != 1 else ''} loaded")
            self.drop_area.label.setStyleSheet("color: #cdd6f4; font-size: 14px;")
            self.extract_btn.setEnabled(not self.running)

    def _add_paths(self, paths):
        added = 0
        for p in paths:
            absp = os.path.abspath(p)
            if absp not in self.map_paths:
                self.map_paths.append(absp)
                item = QListWidgetItem(os.path.basename(absp))
                item.setToolTip(absp)
                self.queue_list.addItem(item)
                added += 1
        if added:
            self._update_queue_ui()
            self._log(f"Added {added} map{'s' if added != 1 else ''}")

    def _on_files_dropped(self, paths):
        self._add_paths(paths)

    def _browse(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select UT99 Maps", "", "Unreal Maps (*.unr);;All Files (*)"
        )
        if paths:
            self._add_paths(paths)

    def _clear_queue(self):
        self.map_paths.clear()
        self.queue_list.clear()
        self._update_queue_ui()
        self._log("Queue cleared.")

    def _fmt_to_arg(self):
        idx = self.fmt_combo.currentIndex()
        return ["obj", "objmtl", "gltf"][idx]

    def _extract(self):
        if not self.map_paths or self.running:
            return

        self.running = True
        self.results.clear()
        self.preview_btn.setEnabled(False)
        self.extract_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.progress.setValue(0)
        self.status_label.setText("Starting batch...")
        self._log(f"── Batch extraction ({len(self.map_paths)} maps) ──")

        fmt = self._fmt_to_arg()
        self.worker = ExtractionWorker(list(self.map_paths), fmt=fmt)
        self.worker.signals.progress.connect(self._on_progress)
        self.worker.signals.map_done.connect(self._on_map_done)
        self.worker.signals.finished.connect(self._on_batch_done)
        self.worker.signals.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, msg, pct):
        if pct is not None:
            self.progress.setValue(pct)
        self.status_label.setText(msg)

    def _on_map_done(self, map_path, result: ExtractionResult):
        self._log(f"  ✔ {os.path.basename(map_path)}: {result.polygons} polys -> {result.output_path}")
        self.results.append(result)

    def _on_batch_done(self):
        self._log("── Batch complete ──")
        self.status_label.setText("All maps extracted.")
        self.progress.setValue(100)
        self.running = False
        self.extract_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        if self.results:
            self.preview_btn.setEnabled(True)
        self.worker = None

    def _on_error(self, msg):
        self._log(f"  ✖ Error: {msg}")

    def _open_preview(self):
        if not self.results:
            return
        r = self.results[-1]
        if not r.triangles:
            QMessageBox.information(self, "Preview", "No triangle data available.")
            return
        dlg = PreviewDialog(r.triangles, title=f"3D Preview — {r.map_name} ({r.polygons} polys)")
        dlg.exec()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("UT99 BSP Extractor")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())



