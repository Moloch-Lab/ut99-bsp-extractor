#!/usr/bin/env python3
"""
UT99 BSP Extractor — GUI frontend for rip_unr.py
"""

import sys
import os
import threading

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QTextEdit, QFileDialog,
    QFrame, QMessageBox, QGroupBox, QGridLayout,
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont

from rip_unr import extract_map, ExtractionResult


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
QTextEdit {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    font-family: "Cascadia Code", "JetBrains Mono", monospace;
    font-size: 12px;
    padding: 6px;
}
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
QFrame#dropArea {
    background-color: #313244;
    border: 2px dashed #585b70;
    border-radius: 10px;
}
QFrame#dropArea:hover { border-color: #89b4fa; }
"""


class WorkerSignals(QObject):
    progress = Signal(str, int)
    finished = Signal(object)
    error = Signal(str)


class ExtractionWorker(threading.Thread):
    def __init__(self, map_path, output_path):
        super().__init__()
        self.map_path = map_path
        self.output_path = output_path
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = extract_map(
                self.map_path,
                self.output_path,
                progress_callback=self.signals.progress.emit,
            )
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))


class DropArea(QFrame):
    file_dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("dropArea")
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        self.label = QLabel("Drag & Drop a .unr map here\nor click Browse")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #6c7086; font-size: 14px;")
        layout.addWidget(self.label)
        self.setLayout(layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".unr"):
                self.file_dropped.emit(path)
                return

    def set_hover(self, active: bool):
        if active:
            self.setStyleSheet(
                "QFrame#dropArea { background-color: #45475a; border: 2px dashed #89b4fa; }"
            )
        else:
            self.setStyleSheet("")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UT99 BSP Extractor")
        self.setMinimumSize(600, 520)
        self.setStyleSheet(STYLESHEET)

        self.map_path = None
        self.worker = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Drop area
        self.drop_area = DropArea()
        self.drop_area.file_dropped.connect(self._on_file_dropped)
        layout.addWidget(self.drop_area)

        # Browse row
        browse_row = QHBoxLayout()
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse)
        browse_row.addStretch()
        browse_row.addWidget(self.browse_btn)
        layout.addLayout(browse_row)

        # File info
        self.info_group = QGroupBox("Map Info")
        info_layout = QGridLayout()
        self.info_labels = {}
        for i, key in enumerate(["File", "Version", "Names", "Exports",
                                  "Model", "Vectors", "Nodes", "Surfaces"]):
            k = QLabel(key + ":")
            k.setStyleSheet("color: #a6adc8; font-weight: bold;")
            v = QLabel("—")
            self.info_labels[key] = v
            info_layout.addWidget(k, i // 4, (i % 4) * 2)
            info_layout.addWidget(v, i // 4, (i % 4) * 2 + 1)
        self.info_group.setLayout(info_layout)
        self.info_group.setVisible(False)
        layout.addWidget(self.info_group)

        # Extract button
        self.extract_btn = QPushButton("Extract OBJ")
        self.extract_btn.setEnabled(False)
        self.extract_btn.clicked.connect(self._extract)
        layout.addWidget(self.extract_btn)

        # Progress
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(self.status_label)

        # Log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(200)
        layout.addWidget(self.log, stretch=1)

        self._log("Ready — drop a .unr file or click Browse.")

    # ── helpers ─────────────────────────────────────────────────────

    def _log(self, msg):
        self.log.append(msg)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _set_file(self, path):
        self.map_path = path
        base = os.path.basename(path)
        self.drop_area.label.setText(base)
        self.drop_area.label.setStyleSheet("color: #cdd6f4; font-size: 14px;")
        self.info_labels["File"].setText(base)
        self.extract_btn.setEnabled(True)

    def _on_file_dropped(self, path):
        self._set_file(path)
        self._log(f"Dropped: {path}")
        self._show_info(path)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select UT99 Map", "", "Unreal Maps (*.unr);;All Files (*)"
        )
        if path:
            self._set_file(path)
            self._log(f"Selected: {path}")
            self._show_info(path)

    def _show_info(self, path):
        try:
            from rip_unr import PackageReader
            pkg = PackageReader(path)
            self.info_labels["Version"].setText(str(pkg.version))
            self.info_labels["Names"].setText(str(pkg.name_count))
            self.info_labels["Exports"].setText(str(pkg.export_count))

            model_name = "—"
            for idx, exp in enumerate(pkg.exports):
                if pkg.resolve_object_name(exp['class_idx']) == "Level":
                    self.info_labels["Model"].setText("(scanning...)")
                    QTimer.singleShot(10, lambda p=pkg, i=idx: self._find_model_info(p, i))
                    break
            self.info_group.setVisible(True)
        except Exception as e:
            self._log(f"Error reading map info: {e}")

    def _find_model_info(self, pkg, level_idx):
        try:
            data = pkg.get_export_data(level_idx)
            if data is None:
                return
            from rip_unr import skip_properties, read_compact_index
            off = skip_properties(data, 0, pkg.resolve_name)
            ac = data[off:off+4]
            off += 8
            for _ in range(int.from_bytes(ac, 'little')):
                v, off = read_compact_index(data, off)
            def ss(d, o):
                if o >= len(d):
                    return o, ""
                sz = d[o]
                return o + 1 + sz, d[o+1:o+1+sz].decode('windows-1252', errors='replace').rstrip('\0')
            off, _ = ss(data, off)
            off, _ = ss(data, off)
            off, _ = ss(data, off)
            oc, off = read_compact_index(data, off)
            for _ in range(oc):
                off, _ = ss(data, off)
            off, _ = ss(data, off)
            off += 8
            mr, _ = read_compact_index(data, off)
            if mr > 0:
                mi = mr - 1
                mn = pkg.resolve_name(pkg.exports[mi]['name_idx'])
                self.info_labels["Model"].setText(mn)
                md = pkg.get_export_data(mi)
                if md:
                    from rip_unr import ModelReader
                    mo = skip_properties(md, 0, pkg.resolve_name)
                    reader = ModelReader(md, mo, pkg.version)
                    model = reader.read_model()
                    self.info_labels["Vectors"].setText(str(len(model['vectors'])))
                    self.info_labels["Nodes"].setText(str(len(model['nodes'])))
                    self.info_labels["Surfaces"].setText(str(len(model['surfaces'])))
        except Exception as e:
            self._log(f"  (model info: {e})")

    def _extract(self):
        if not self.map_path:
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save OBJ", os.path.splitext(os.path.basename(self.map_path))[0] + ".obj",
            "Wavefront OBJ (*.obj);;All Files (*)"
        )
        if not output_path:
            return

        self.extract_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.progress.setValue(0)
        self.status_label.setText("Starting...")
        self._log("── Extraction started ──")

        self.worker = ExtractionWorker(self.map_path, output_path)
        self.worker.signals.progress.connect(self._on_progress)
        self.worker.signals.finished.connect(self._on_finished)
        self.worker.signals.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, msg, pct):
        if pct is not None:
            self.progress.setValue(pct)
        self.status_label.setText(msg)
        self._log(f"  {msg}")

    def _on_finished(self, result: ExtractionResult):
        self._log(f"✔ Done — {result.polygons} polygons written to {result.output_path}")
        self.status_label.setText(f"Done! {result.polygons} polygons.")
        self.progress.setValue(100)
        self.extract_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.worker = None

    def _on_error(self, msg):
        self._log(f"✖ Error: {msg}")
        self.status_label.setText("Error — see log")
        self.progress.setValue(0)
        self.extract_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        QMessageBox.critical(self, "Extraction Failed", msg)
        self.worker = None


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("UT99 BSP Extractor")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
