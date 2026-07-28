from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout
from qfluentwidgets import InfoBar, LineEdit, MessageBoxBase

from app.config.cfg import BASE_HEADERS
from app.view.components.headers_editor import HeadersEditor
from app.view.components.scroll_area import ScrollArea


class HeadersPresetEditDialog(MessageBoxBase):

    def __init__(self, parent=None, *, preset: dict):
        super().__init__(parent)
        self.nameEdit = LineEdit(self)
        self.editor = HeadersEditor(self, defaults=BASE_HEADERS)
        self.scrollArea = ScrollArea(self.widget)
        self.titleRow = QHBoxLayout()

        self._initWidget(preset)
        self._initLayout()

    def _initWidget(self, preset: dict) -> None:
        self.widget.setMinimumWidth(500)
        self.yesButton.setText(self.tr("Save"))
        self.cancelButton.setText(self.tr("Cancel"))
        self.nameEdit.setPlaceholderText(self.tr("Preset Name"))
        self.nameEdit.setText(preset["name"])
        self.editor.setHeaders(preset["headers"])

    def _initLayout(self) -> None:
        self.titleRow.addWidget(self.nameEdit, 1)
        self.titleRow.addSpacing(8)
        self.titleRow.addWidget(self.editor.toolbar)
        self.viewLayout.addLayout(self.titleRow)

        self.scrollArea.setWidget(self.editor)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.enableTransparentBackground()
        self.viewLayout.addWidget(self.scrollArea)

    def validate(self) -> bool:
        if self.nameEdit.text().strip():
            return True
        InfoBar.warning(
            self.tr("Enter preset name"),
            self.tr("Preset name cannot be empty"),
            parent=self,
        )
        return False

    def preset(self) -> dict:
        return {
            "name": self.nameEdit.text().strip() or self.tr("Unnamed Preset"),
            "headers": self.editor.headers(),
        }
