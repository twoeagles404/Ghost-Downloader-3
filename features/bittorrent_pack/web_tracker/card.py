from qfluentwidgets import (
    FluentIcon,
    PrimaryPushButton,
    SettingCard,
    StateToolTip,
    ToolButton,
    ToolTipFilter,
)

from ..config import bittorrentConfig
from .service import trackerService


class WebTrackerCard(SettingCard):
    def __init__(self, submit, parent=None):
        super().__init__(FluentIcon.GLOBE, self.tr("Web Tracker"), "", parent)
        self._submit = submit
        self.manageButton = PrimaryPushButton(self.tr("Manage"), self)
        self.refreshButton = ToolButton(FluentIcon.SYNC, self)
        self._stateToolTip: StateToolTip | None = None

        self._initWidget()
        self._initLayout()
        self._bind()

    def _initWidget(self):
        self.refreshButton.setToolTip(self.tr("Refresh Cache"))
        self.refreshButton.installEventFilter(ToolTipFilter(self.refreshButton))
        self.refreshContent()

    def _initLayout(self):
        self.hBoxLayout.addWidget(self.manageButton, 0)
        self.hBoxLayout.addSpacing(8)
        self.hBoxLayout.addWidget(self.refreshButton, 0)
        self.hBoxLayout.addSpacing(16)

    def _bind(self):
        self.manageButton.clicked.connect(self._onManageClicked)
        self.refreshButton.clicked.connect(self._onRefreshClicked)

    def refreshContent(self):
        sourceCount = len(list(bittorrentConfig.webTrackerSources.value))
        cachedTotal = len(trackerService.mergedTrackers())
        self.setContent(self.tr("{0} source(s), {1} trackers cached").format(sourceCount, cachedTotal))

    def _onManageClicked(self):
        from .dialog import WebTrackerDialog
        dialog = WebTrackerDialog(self.window())
        try:
            if dialog.exec():
                self._onRefreshClicked()
        finally:
            dialog.deleteLater()

    def _onRefreshClicked(self):
        urls = list(bittorrentConfig.webTrackerSources.value)
        if not urls:
            return
        self.refreshButton.setEnabled(False)
        self._stateToolTip = StateToolTip(
            self.tr("Refreshing Trackers"),
            self.tr("Downloading from {0} source(s)").format(len(urls)),
            self.window(),
        )
        self._stateToolTip.move(self._stateToolTip.getSuitablePos())
        self._stateToolTip.show()

        self._submit(
            trackerService.refresh(),
            done=self._onRefreshDone, failed=self._onRefreshFailed,
            owner=self,
        )

    def _onRefreshDone(self, result):
        self.refreshButton.setEnabled(True)
        if self._stateToolTip is None:
            return
        success, total = result
        cachedTotal = len(trackerService.mergedTrackers())
        self._stateToolTip.setContent(
            self.tr("Refreshed {0}/{1} sources, {2} trackers total").format(success, total, cachedTotal)
        )
        self._stateToolTip.setState(True)
        self._stateToolTip = None
        self.refreshContent()

    def _onRefreshFailed(self, error):
        self.refreshButton.setEnabled(True)
        if self._stateToolTip is None:
            return
        self._stateToolTip.setContent(self.tr("Refresh Failed: {0}").format(str(error)))
        self._stateToolTip.setState(True)
        self._stateToolTip = None
