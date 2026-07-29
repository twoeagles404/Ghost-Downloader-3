from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import FluentIcon, PrimaryToolButton, ToolButton

from app.models.task import Task
from app.view.cards.task_cards import TaskCard
from app.view.mobile.cards import MobileTaskCardBase
from app.view.pages.task_page import TaskPage


class MobileTaskPage(TaskPage):
    selectionModeChanged = Signal(bool)

    def __init__(self, taskService, featureService, categoryService, speedMeter, parent=None):
        self._mobileCardTypes: dict[type, type] = {}
        super().__init__(taskService, featureService, categoryService, speedMeter, parent=parent)

    def setSelectionMode(self, enter: bool) -> None:
        super().setSelectionMode(enter)
        self.selectionModeChanged.emit(enter)

    def _bind(self) -> None:
        super()._bind()
        self._bandSelector.setEnabled(False)

    def _initWidget(self) -> None:
        super()._initWidget()
        # desktop text buttons are too wide on narrow screens, switch to icon buttons; change selection to long-press, hide selectButton
        for old in (self.startAllButton, self.pauseAllButton):
            old.hide()
            old.deleteLater()
        self.startAllButton = PrimaryToolButton(FluentIcon.PLAY, self.toolBar)
        self.pauseAllButton = ToolButton(FluentIcon.PAUSE, self.toolBar)
        self.startAllButton.setToolTip(self.tr("Start All"))
        self.pauseAllButton.setToolTip(self.tr("Pause All"))
        self.selectButton.hide()

        self.filterToolBar = QWidget(self)

    def _initLayout(self) -> None:
        toolBarLayout = QHBoxLayout(self.toolBar)
        toolBarLayout.setContentsMargins(10, 4, 10, 0)
        toolBarLayout.setSpacing(6)
        toolBarLayout.addWidget(self.startAllButton)
        toolBarLayout.addWidget(self.pauseAllButton)
        toolBarLayout.addWidget(self.speedBadge)
        toolBarLayout.addStretch(1)
        toolBarLayout.addWidget(self.rateLimitButton)
        toolBarLayout.addWidget(self.planButton)

        filterToolBarLayout = QHBoxLayout(self.filterToolBar)
        filterToolBarLayout.setContentsMargins(10, 0, 10, 4)
        filterToolBarLayout.setSpacing(6)
        filterToolBarLayout.addWidget(self.filterSegment)
        filterToolBarLayout.addStretch(1)
        filterToolBarLayout.addWidget(self.sortButton)
        filterToolBarLayout.addWidget(self.categoryFilterButton)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.toolBar)
        layout.addWidget(self.filterToolBar)
        layout.addWidget(self.scrollArea)

    def _createCard(self, task: Task) -> TaskCard | None:
        card = super()._createCard(task)
        if card is None:  # the pack this task belongs to is not bundled (e.g. ed2k excluded on Android)
            return None
        baseType = type(card)
        mobileType = self._mobileCardTypes.get(baseType)
        if mobileType is None:
            mobileType = type(f"Mobile{baseType.__name__}", (MobileTaskCardBase, baseType), {})
            self._mobileCardTypes[baseType] = mobileType
        card.__class__ = mobileType  # apply the movable mixin: same C++ type, only changes the Python MRO
        card.setupMobile()
        return card

    def resizeEvent(self, event) -> None:
        self._fitCommandView()
        super().resizeEvent(event)

    def _fitCommandView(self) -> None:
        # a narrow screen cannot fit the whole command bar, so narrow it to fold the overflow actions into the "More" button
        bar = self.commandView.bar
        margin = 12
        widthLimit = max(self.width() - 24 - margin, bar.moreButton.width())
        width = min(bar.suitableWidth(), widthLimit)
        bar.setFixedWidth(width)
        self.commandView.setFixedWidth(width + margin)
