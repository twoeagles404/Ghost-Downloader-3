from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QMovie
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, MessageBoxBase, SubtitleLabel, isDarkTheme, themeColor

from app.view.components.scroll_area import ScrollArea

from app.platform.desktop import openChromiumUrl, revealInFolder

PREVIEW_SIZE = QSize(720, 405)
PREVIEW_GIF = ":/res/install_chrome_extension_guidance.webp"


class ExtensionInstallDialog(MessageBoxBase):
    def __init__(self, path: Path, parent=None):
        super().__init__(parent)
        self._path = path

        self.previewLabel = QLabel(self)
        self.titleLabel = SubtitleLabel(self.tr("Extension unpacked, install as follows:"), self)
        self.stepsWidget = QWidget(self)

        self._initWidget()
        self._initLayout()
        self._bind()

    def _initWidget(self) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.widget.setMinimumWidth(PREVIEW_SIZE.width() + 48)  # + 24px left/right margins for scrollLayout
        # viewLayout margins 48 + spacers/spacing 60 + title 28 + steps 168 + buttonGroup 81
        self.widget.setMaximumHeight(PREVIEW_SIZE.height() + 385)
        self._hBoxLayout.setContentsMargins(40, 40, 40, 40)
        self._hBoxLayout.setAlignment(self.widget, Qt.AlignmentFlag.AlignHCenter)
        self.yesButton.setText(self.tr("Open extensions page and navigate to directory"))
        self.cancelButton.setText(self.tr("Close"))
        self._initPreview()
        self._initSteps()

    def _initPreview(self) -> None:
        self.previewLabel.setFixedSize(PREVIEW_SIZE)
        self.previewLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        movie = QMovie(PREVIEW_GIF, parent=self)
        if movie.isValid():
            movie.setScaledSize(PREVIEW_SIZE)
            self.previewLabel.setMovie(movie)
            movie.start()
            return

        self.previewLabel.setText(self.tr("Demo animation coming soon"))
        if isDarkTheme():
            background, color = "rgba(255, 255, 255, 0.06)", "rgba(255, 255, 255, 0.5)"
        else:
            background, color = "rgba(0, 0, 0, 0.04)", "rgba(0, 0, 0, 0.4)"
        self.previewLabel.setStyleSheet(
            f"QLabel {{ background: {background}; color: {color}; border-radius: 8px; }}"
        )

    def _initSteps(self) -> None:
        chipBg = "rgba(255, 255, 255, 0.1)" if isDarkTheme() else "rgba(0, 0, 0, 0.06)"

        def chip(text: str, mono: bool = False) -> str:
            family = " font-family: 'Cascadia Code', Consolas, monospace;" if mono else ""
            return f"<span style=\"background-color: {chipBg};{family}\">&nbsp;{text}&nbsp;</span>"

        steps = [
            self.tr("Open {} in Browser").format(chip("chrome://extensions", mono=True)),
            self.tr("Enable {}").format(chip(self.tr("Developer Mode"))),
            self.tr("Drag {} into browser window").format(chip(self.tr("Extension Folder"))),
            self.tr("Enable Extension"),
            self.tr("Open {}, click {}").format(chip(self.tr("Extension Popup")), chip(self.tr("Auto Pair"))),
        ]
        accent = themeColor().name()
        layout = QVBoxLayout(self.stepsWidget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        for index, text in enumerate(steps, 1):
            badge = QLabel(str(index), self.stepsWidget)
            badge.setFixedSize(24, 24)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                f"background: {accent}; color: white; border-radius: 12px; font-weight: bold;"
            )
            stepLabel = BodyLabel(self.stepsWidget)
            stepLabel.setTextFormat(Qt.TextFormat.RichText)
            stepLabel.setText(text)
            row = QHBoxLayout()
            row.setSpacing(12)
            row.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(stepLabel, 1, Qt.AlignmentFlag.AlignVCenter)
            layout.addLayout(row)

    def _initLayout(self) -> None:
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        scrollArea = ScrollArea(self.widget)
        scrollArea.setWidgetResizable(True)
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scrollWidget = QWidget()
        scrollLayout = QVBoxLayout(scrollWidget)
        scrollLayout.setSpacing(12)
        scrollLayout.setContentsMargins(24, 24, 24, 24)
        scrollLayout.addWidget(self.previewLabel)
        scrollLayout.addSpacing(8)
        scrollLayout.addWidget(self.titleLabel)
        scrollLayout.addSpacing(4)
        scrollLayout.addWidget(self.stepsWidget)

        scrollArea.setWidget(scrollWidget)
        scrollArea.enableTransparentBackground()
        self.viewLayout.addWidget(scrollArea)

    def _bind(self) -> None:
        self.yesButton.clicked.disconnect()
        self.yesButton.clicked.connect(self._onInstall)

    def _onInstall(self) -> None:
        from qfluentwidgets import InfoBar, InfoBarPosition

        revealInFolder(str(self._path))
        if not openChromiumUrl("chrome://extensions"):
            QApplication.clipboard().setText("chrome://extensions")
            InfoBar.info(
                self.tr("Please manually open your browser"),
                self.tr("chrome://extensions copied to clipboard, please paste into address bar"),
                duration=5000, position=InfoBarPosition.TOP, parent=self,
            )
