from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel, ComboBox, FluentIcon, LineEdit, MessageBoxBase,
    SubtitleLabel, ToolButton, ToolTipFilter,
)

from app.services.category_service import Category
from app.view.components.token_line_edit import TokenLineEdit


class CategoryEditDialog(MessageBoxBase):
    ICON_CHOICES = [
        "DOCUMENT", "MUSIC", "VIDEO", "ZIP_FOLDER", "APPLICATION",
        "LIBRARY", "ALBUM", "PHOTO", "MOVIE", "MEDIA",
        "GAME", "CODE", "EDUCATION", "LANGUAGE", "BRUSH",
        "FOLDER", "CHAT", "MAIL", "PRINT", "GLOBE",
        "CAMERA", "IMAGE_EXPORT", "MUSIC_FOLDER", "MARKET", "HELP",
    ]
    def __init__(self, parent=None, *, category: Category | None = None):
        super().__init__(parent)
        self._category = category

        self.titleLabel = SubtitleLabel(
            self.tr("Edit Category") if category else self.tr("Add"), self
        )
        self.nameEdit = LineEdit(self)
        self.iconCombo = ComboBox(self)
        self.extensionsEdit = TokenLineEdit(self)
        self.folderRow = QWidget(self)
        self.folderRowLayout = QHBoxLayout(self.folderRow)
        self.folderEdit = LineEdit(self.folderRow)
        self.folderBrowseButton = ToolButton(FluentIcon.FOLDER, self.folderRow)

        self._initWidget()
        self._initLayout()
        self._bind()
        self._populate()

    def _initWidget(self) -> None:
        self.widget.setMinimumWidth(480)
        self.yesButton.setText(self.tr("Save"))
        self.cancelButton.setText(self.tr("Cancel"))
        self.nameEdit.setPlaceholderText(self.tr("Category name"))
        self.extensionsEdit.setPlaceholderText(self.tr("Enter extension and press Enter to add"))
        self.folderEdit.setPlaceholderText(self.tr("Leave empty to use default download path; use {default} to represent the default download folder"))
        self.folderBrowseButton.setToolTip(self.tr("Select Folder"))
        self.folderBrowseButton.installEventFilter(ToolTipFilter(self.folderBrowseButton))

        for name in self.ICON_CHOICES:
            self.iconCombo.addItem(name, icon=getattr(FluentIcon, name, FluentIcon.DOCUMENT), userData=name)

    def _initLayout(self) -> None:
        self.folderRowLayout.setContentsMargins(0, 0, 0, 0)
        self.folderRowLayout.setSpacing(8)
        self.folderRowLayout.addWidget(self.folderEdit, stretch=1)
        self.folderRowLayout.addWidget(self.folderBrowseButton)

        self.viewLayout.setSpacing(8)
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(8)
        self.viewLayout.addWidget(BodyLabel(self.tr("Name"), self))
        self.viewLayout.addWidget(self.nameEdit)
        self.viewLayout.addWidget(BodyLabel(self.tr("Icon"), self))
        self.viewLayout.addWidget(self.iconCombo)
        self.viewLayout.addWidget(BodyLabel(self.tr("File Extension(s)"), self))
        self.viewLayout.addWidget(self.extensionsEdit)
        self.viewLayout.addWidget(BodyLabel(self.tr("Download Folder"), self))
        self.viewLayout.addWidget(self.folderRow)

    def _bind(self) -> None:
        self.folderBrowseButton.clicked.connect(self._onBrowseClicked)

    def _populate(self) -> None:
        if self._category is None:
            return
        self.nameEdit.setText(self._category.name)
        self.extensionsEdit.setTokens(self._category.extensions)
        self.folderEdit.setText(self._category.folder or "")
        index = self.iconCombo.findData(self._category.icon)
        self.iconCombo.setCurrentIndex(index if index >= 0 else 0)

    def _onBrowseClicked(self) -> None:
        start = self.folderEdit.text() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(self, self.tr("Choose Download Folder"), start)
        if selected:
            self.folderEdit.setText(selected)

    def category(self) -> Category:
        name = self.nameEdit.text().strip() or self.tr("Unnamed Category")
        extensions = [
            ext for token in self.extensionsEdit.tokens()
            if (ext := token.strip().lstrip(".").lower())
        ]
        folder = self.folderEdit.text().strip() or None
        icon = self.iconCombo.currentData() or "DOCUMENT"

        if self._category is None:
            return Category(name=name, icon=icon, extensions=extensions, folder=folder)
        return Category(
            categoryId=self._category.categoryId,
            name=name, icon=icon, extensions=extensions, folder=folder,
        )
