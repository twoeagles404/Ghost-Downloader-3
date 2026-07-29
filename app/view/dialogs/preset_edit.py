from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout
from qfluentwidgets import (
    BodyLabel, DropDownPushButton, FluentIcon, InfoBar, LineEdit,
    MessageBoxBase, SubtitleLabel, TeachingTip, TeachingTipTailPosition,
    TransparentToolButton,
)

from app.view.components.token_line_edit import TokenLineEdit


class PresetEditDialog(MessageBoxBase):

    def __init__(self, parent=None, *, preset: dict | None = None):
        super().__init__(parent)
        self._preset = preset
        self._profileValue = preset.get("clientProfile", "") if preset else ""

        self.titleLabel = SubtitleLabel(
            self.tr("Edit Identity Preset") if preset else self.tr("Add Identity Preset"), self
        )
        self.nameEdit = LineEdit(self)
        self.hostsEdit = TokenLineEdit(self)
        self.hostsHelpButton = TransparentToolButton(FluentIcon.QUESTION, self)
        self.hostsRow = QHBoxLayout()
        self.profileButton = DropDownPushButton(self)
        self.uaEdit = LineEdit(self)

        self._initWidget()
        self._initLayout()
        self._bind()
        self._populate()

    def _initWidget(self) -> None:
        self.widget.setMinimumWidth(480)
        self.yesButton.setText(self.tr("Save"))
        self.cancelButton.setText(self.tr("Cancel"))
        self.nameEdit.setPlaceholderText(self.tr("Preset Name"))
        self.uaEdit.setPlaceholderText(self.tr("Leave empty to auto-generate based on TLS fingerprint"))
        self.uaEdit.setClearButtonEnabled(True)

        from app.view.components.option_cards import buildProfileMenu
        self.profileButton.setMenu(
            buildProfileMenu(self, self._onProfilePick, includeAuto=False))

    def _initLayout(self) -> None:
        self.hostsRow.setContentsMargins(0, 0, 0, 0)
        self.hostsRow.setSpacing(4)
        self.hostsRow.addWidget(BodyLabel(self.tr("Match Host"), self))
        self.hostsRow.addWidget(self.hostsHelpButton)
        self.hostsRow.addStretch(1)

        self.viewLayout.setSpacing(8)
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(8)
        self.viewLayout.addWidget(BodyLabel(self.tr("Name"), self))
        self.viewLayout.addWidget(self.nameEdit)
        self.viewLayout.addLayout(self.hostsRow)
        self.viewLayout.addWidget(self.hostsEdit)
        self.viewLayout.addWidget(BodyLabel(self.tr("TLS Fingerprint"), self))
        self.viewLayout.addWidget(self.profileButton)
        self.viewLayout.addWidget(BodyLabel(self.tr("User-Agent"), self))
        self.viewLayout.addWidget(self.uaEdit)

    def _bind(self) -> None:
        self.hostsHelpButton.clicked.connect(self._onHostsHelpClicked)

    def _populate(self) -> None:
        self._refreshProfileLabel()
        if self._preset is None:
            return
        self.nameEdit.setText(self._preset.get("name", ""))
        self.hostsEdit.setTokens(self._preset.get("hosts", []))
        self.uaEdit.setText(self._preset.get("userAgent", ""))

    def _onHostsHelpClicked(self) -> None:
        TeachingTip.create(
            self.hostsHelpButton,
            self.tr("Host Pattern"),
            self.tr(
                "Enter a domain and press Enter to add; two formats are supported:\n\n"
                "Exact match: pcs.baidu.com\n"
                "Wildcard: *.pcs.baidu.com (matches all subdomains)"
            ),
            tailPosition=TeachingTipTailPosition.BOTTOM,
            isClosable=True,
            duration=-1,
            parent=self,
        )

    def _onProfilePick(self, value: str) -> None:
        self._profileValue = value
        self._refreshProfileLabel()

    def _refreshProfileLabel(self) -> None:
        from app.view.components.option_cards import toProfileLabel
        if self._profileValue:
            self.profileButton.setText(toProfileLabel(self._profileValue))
        else:
            self.profileButton.setText(self.tr("Follow Global Default"))

    def validate(self) -> bool:
        if self.hostsEdit.tokens():
            return True
        InfoBar.warning(
            self.tr("Please add a matching Host"),
            self.tr("A preset needs at least one Host to match requests"),
            parent=self,
        )
        return False

    def preset(self) -> dict:
        result = {
            "name": self.nameEdit.text().strip() or self.tr("Unnamed Preset"),
            "clientProfile": self._profileValue,
            "userAgent": self.uaEdit.text().strip(),
            "hosts": self.hostsEdit.tokens(),
            "isEnabled": True,
        }
        if self._preset is not None:
            result["isEnabled"] = self._preset.get("isEnabled", True)
        return result
