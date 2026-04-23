from __future__ import annotations

from collections.abc import Callable
from functools import partial

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from numbers_model import NumbersModel, NumbersSnapshot


class MainWindow(QMainWindow):
    def __init__(self, model: NumbersModel | None = None) -> None:
        super().__init__()
        self._model = model or NumbersModel()
        self._unsubscribe: Callable[[], None] | None = None
        self._sliders: dict[str, QSlider] = {}

        self.setWindowTitle("A<B<C")
        self.resize(900, 170)

        central = QWidget(self)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self._add_named_slider(layout, "A", "a")
        self._add_separator(layout)
        self._add_named_slider(layout, "B", "b")
        self._add_separator(layout)
        self._add_named_slider(layout, "C", "c")

        self.setCentralWidget(central)

        self._unsubscribe = self._model.subscribe(self._on_model_changed)
        self._model.load()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._model.save()
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        super().closeEvent(event)

    def _add_named_slider(self, layout: QHBoxLayout, label_text: str, name: str) -> None:
        block = QWidget(self)
        block_layout = QVBoxLayout(block)
        block_layout.setContentsMargins(0, 0, 0, 0)
        block_layout.setSpacing(6)

        label = QLabel(label_text, block)
        label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        block_layout.addWidget(label)

        slider = QSlider(Qt.Orientation.Horizontal, block)
        slider.setRange(self._model.minimum, self._model.maximum)
        slider.setSingleStep(1)
        slider.setPageStep(10)
        slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        slider.valueChanged.connect(partial(self._on_slider_changed, name))
        self._sliders[name] = slider
        block_layout.addWidget(slider)

        block.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(block, 1)

    def _add_separator(self, layout: QHBoxLayout) -> None:
        sep = QLabel("<", self)
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sep.setFixedWidth(14)
        layout.addWidget(sep)

    def _on_slider_changed(self, name: str, value: int) -> None:
        previous_notification_count = self._model.notification_count

        if name == "a":
            self._model.set_a(value)
        elif name == "b":
            self._model.set_b(value)
        else:
            self._model.set_c(value)

        if self._model.notification_count == previous_notification_count:
            self._render_snapshot(self._model.snapshot)

    def _on_model_changed(self, snapshot: NumbersSnapshot) -> None:
        self._render_snapshot(snapshot)

    def _render_snapshot(self, snapshot: NumbersSnapshot) -> None:
        self._sync_slider(self._sliders["a"], snapshot.a, snapshot.minimum, snapshot.maximum)
        self._sync_slider(self._sliders["b"], snapshot.b, snapshot.minimum, snapshot.maximum)
        self._sync_slider(self._sliders["c"], snapshot.c, snapshot.minimum, snapshot.maximum)

    @staticmethod
    def _sync_slider(slider: QSlider, value: int, minimum: int, maximum: int) -> None:
        blocker = QSignalBlocker(slider)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        del blocker
