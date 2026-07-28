from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QVBoxLayout, QWidget, QApplication
from qfluentwidgets import (
    ComboBoxSettingCard, FluentIcon, HyperlinkCard, HyperlinkButton, InfoBar,
    InfoBarPosition, MessageBox, PrimaryPushSettingCard, PushButton, PushSettingCard,
    RangeSettingCard, SwitchSettingCard, ToolButton, ToolTipFilter,
)

from app.view.components.scroll_area import ScrollArea

from app.config.cfg import cfg, LANGUAGE_TEXTS
from app.platform.android import IS_ANDROID
from app.config.constants import (
    AUTHOR, AUTHOR_URL, CHROME_WEBSTORE_URL, EDGE_ADDONS_URL,
    FEEDBACK_URL, FIREFOX_ADDONS_URL, VERSION, YEAR,
)
from app.view.components.category_settings import CategoryRulesCard
from app.view.components.setting_card_group import (
    CollapsibleSettingCard, CollapsibleSettingCardGroup, QWIDGETSIZE_MAX,
)
from app.view.components.setting_cards import (
    HeadersPresetSettingCard, IdentitySettingCard, LineEditSettingCard,
    PercentSpinBoxSettingCard, ProxySettingCard, SpinBoxSettingCard,
)
from app.view.components.editors import FolderPicker


class SettingPage(ScrollArea):

    def __init__(self, featureService, browserService, coroutineRunner, categoryService, parent=None):
        super().__init__(parent)
        self._featureService = featureService
        self._browserService = browserService
        self._coroutineRunner = coroutineRunner
        self._categoryService = categoryService
        self.container = QWidget()
        self.vBoxLayout = QVBoxLayout(self.container)
        self.vBoxLayout.addStretch(1)

        self.generalGroup = CollapsibleSettingCardGroup(self.tr("General Download Settings"), "general", self.container)
        self.categoryGroup = CollapsibleSettingCardGroup(self.tr("Download Categorization"), "category", self.container)
        self.browserGroup = CollapsibleSettingCardGroup(self.tr("Browser Extension"), "browser", self.container)
        self.aria2RpcGroup = CollapsibleSettingCardGroup(self.tr("Aria2 RPC Compatibility"), "aria2rpc", self.container)
        self.personalGroup = CollapsibleSettingCardGroup(self.tr("Personalization"), "personalization", self.container)
        self.softwareGroup = CollapsibleSettingCardGroup(self.tr("Application"), "software", self.container)
        self.aboutGroup = CollapsibleSettingCardGroup(self.tr("About"), "about", self.container)

        from app.view.pages.task_page import EmptyStatusWidget
        self.emptyStatusWidget = EmptyStatusWidget(FluentIcon.SEARCH_MIRROR, self.tr("No matching settings found"), self)
        self.emptyStatusWidget.hide()

        self._initWidget()
        self._initCards()
        self._initLayout()
        self._bind()

    def addSettingGroup(self, group: CollapsibleSettingCardGroup) -> None:
        self.vBoxLayout.insertWidget(self.vBoxLayout.count() - 1, group)

    def _initWidget(self) -> None:
        self.setWidget(self.container)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("SettingPage")
        self.enableTransparentBackground()
        self.setProperty("isStackedTransparent", False)

    def _initCards(self) -> None:
        self.speedLimitationCard = SpinBoxSettingCard(
            FluentIcon.SPEED_OFF, self.tr("Download Speed Limit"),
            self.tr("If the speed limit switch is enabled on the download tasks page, all tasks will be limited according to this value"),
            suffix=" KB/s", configItem=cfg.speedLimitation,
            singleStep=512, division=1 / 1024,
        )
        from qfluentwidgets import SettingCard
        self.downloadFolderCard = SettingCard(FluentIcon.FOLDER, self.tr("Download Path"), self.tr("Default file save location"))
        self.downloadFolderPicker = FolderPicker(self.downloadFolderCard)
        self.downloadRestoreButton = ToolButton(FluentIcon.CANCEL, self.downloadFolderCard)
        self.downloadRestoreButton.setToolTip(self.tr("Restore Default Path"))
        self.downloadRestoreButton.installEventFilter(ToolTipFilter(self.downloadRestoreButton))
        self.downloadFolderPicker.refreshHistory()
        self.downloadFolderPicker.setPath(cfg.downloadFolder.value)
        self.downloadFolderCard.hBoxLayout.addWidget(self.downloadFolderPicker, 0, Qt.AlignmentFlag.AlignRight)
        self.downloadFolderCard.hBoxLayout.addSpacing(8)
        self.downloadFolderCard.hBoxLayout.addWidget(self.downloadRestoreButton, 0, Qt.AlignmentFlag.AlignRight)
        self.downloadFolderCard.hBoxLayout.addSpacing(16)
        self.clientProfileCard = IdentitySettingCard()

        self.generalGroup.addSettingCards([
            RangeSettingCard(cfg.maxTaskNum, FluentIcon.TRAIN, self.tr("Maximum Concurrent Tasks"),
                             self.tr("Maximum number of simultaneous transfers")),
            RangeSettingCard(cfg.preBlockNum, FluentIcon.CLOUD, self.tr("Pre-allocated Threads"),
                             self.tr("More threads speed up downloads. Over 64 threads may trigger anti-scraping and corrupt files")),
            SwitchSettingCard(FluentIcon.SPEED_HIGH, self.tr("Auto Boost"),
                              self.tr("Monitor thread efficiencies with AI and auto-increase number of threads to boost download speed"),
                              cfg.autoSpeedUp),
            SpinBoxSettingCard(FluentIcon.LIBRARY, self.tr("Minimum Redistribution Size"),
                              self.tr("If threads' workload surpasses this value, redistribution will trigger when a thread completes or Auto Boost is enabled"),
                              " KB", cfg.maxReassignSize, singleStep=64),
            self.speedLimitationCard,
            SwitchSettingCard(FluentIcon.HISTORY, self.tr("Preserve file modification time"),
                              self.tr("Set file modification time to server's Last-Modified value after download"),
                              cfg.shouldPreserveLastModified),
            SwitchSettingCard(FluentIcon.DEVELOPER_TOOLS, self.tr("Verify SSL Certificates"),
                              self.tr("Try disabling if files fail to download"),
                              cfg.shouldVerifySsl),
            self.downloadFolderCard,
            ProxySettingCard(cfg.proxyServer, featureService=self._featureService),
            self.clientProfileCard,
            HeadersPresetSettingCard(),
        ])

        self.categoryRulesCard = CategoryRulesCard(self._categoryService)
        self.categoryGroup.addSettingCards([
            SwitchSettingCard(FluentIcon.TAG, self.tr("Enable Categorization"),
                              self.tr("Categorize downloads by file extensions for easier filtering and management"),
                              cfg.isCategoryEnabled),
            self.categoryRulesCard,
        ])

        self.browserPairTokenCard = PrimaryPushSettingCard(
            self.tr("Copy"), FluentIcon.COPY, self.tr("Pairing Token"),
            cfg.browserExtensionPairToken.value,
        )
        self.regenerateTokenButton = ToolButton(FluentIcon.SYNC, self.browserPairTokenCard)
        self.regenerateTokenButton.setToolTip(self.tr("Regenerate"))
        self.regenerateTokenButton.installEventFilter(ToolTipFilter(self.regenerateTokenButton))
        self.browserPairTokenCard.hBoxLayout.insertSpacing(6, 8)
        self.browserPairTokenCard.hBoxLayout.insertWidget(
            7, self.regenerateTokenButton, 0, Qt.AlignmentFlag.AlignRight,
        )

        self.storeInstallCard = HyperlinkCard(
            FIREFOX_ADDONS_URL, self.tr("Firefox Store"), FluentIcon.GLOBE,
            self.tr("Install extension from store"),
            self.tr("Store version requires review before receiving updates"),
        )
        edgeBtn = HyperlinkButton(self.storeInstallCard)
        edgeBtn.setText(self.tr("Edge Store"))
        edgeBtn.setUrl(EDGE_ADDONS_URL)
        self.storeInstallCard.hBoxLayout.insertWidget(
            5, edgeBtn, 0, Qt.AlignmentFlag.AlignRight,
        )
        self.storeInstallCard.hBoxLayout.insertSpacing(6, 16)

        chromeBtn = HyperlinkButton(self.storeInstallCard)
        chromeBtn.setText(self.tr("Chrome Store"))
        chromeBtn.setUrl(CHROME_WEBSTORE_URL)
        self.storeInstallCard.hBoxLayout.insertWidget(
            5, chromeBtn, 0, Qt.AlignmentFlag.AlignRight,
        )
        self.storeInstallCard.hBoxLayout.insertSpacing(6, 16)

        self.chromiumInstallCard = PrimaryPushSettingCard(
            self.tr("Install"), FluentIcon.DOWNLOAD,
            self.tr("Install to Chromium Browser"),
            self.tr("Auto-unpack extension and guide loading (Chrome/Brave etc.), extension auto-updates with the desktop client"),
        )
        self.exportExtensionButton = HyperlinkButton(self.chromiumInstallCard)
        self.exportExtensionButton.setText(self.tr("Export CRX"))
        self.chromiumInstallCard.hBoxLayout.insertWidget(
            5, self.exportExtensionButton, 0, Qt.AlignmentFlag.AlignRight,
        )
        self.chromiumInstallCard.hBoxLayout.insertSpacing(6, 16)

        self.browserPortCard = SpinBoxSettingCard(
            FluentIcon.COMMAND_PROMPT, self.tr("Service Port"),
            self.tr("Port used for browser extension connection"),
            configItem=cfg.browserExtensionPort, singleStep=1, division=1,
        )

        self.browserEnableCard = SwitchSettingCard(
            FluentIcon.CONNECT, self.tr("Enable Browser Extension"),
            self.tr("Receive downloads from browser - extension installation required"),
            cfg.isBrowserExtensionEnabled,
        )

        self.urlSchemeCard = SwitchSettingCard(
            FluentIcon.LINK, self.tr("Register URL Protocol"),
            self.tr("Register ghostdownloader:// protocol to allow browser extension to launch desktop client"),
            cfg.isUrlSchemeRegistered,
        ) if sys.platform != "darwin" else None

        browserCards = [
            self.browserEnableCard,
            SwitchSettingCard(FluentIcon.CHAT, self.tr("Enter draft mode when intercepting downloads"),
                              self.tr("Enter draft mode when automatically intercepting browser downloads to adjust download path and file name"),
                              cfg.shouldDraftTakenDownload),
            self.browserPairTokenCard,
            self.storeInstallCard,
            self.chromiumInstallCard,
            self.browserPortCard,
        ]
        if self.urlSchemeCard:
            browserCards.insert(2, self.urlSchemeCard)

        self.browserGroup.addSettingCards(browserCards)

        self.aria2RpcGroup.addSettingCards([
            SwitchSettingCard(
                FluentIcon.LINK, self.tr("Enable Aria2 RPC Compatibility"),
                self.tr("Compatible with Aria2 JSON-RPC protocol, able to receive download links from external tools"),
                cfg.isAria2RpcEnabled,
            ),
            SpinBoxSettingCard(
                FluentIcon.GLOBE, self.tr("Port"),
                self.tr("Default Aria2 RPC port is 16800"),
                configItem=cfg.aria2RpcPort, singleStep=1, division=1,
            ),
            LineEditSettingCard(
                FluentIcon.FINGERPRINT, self.tr("Token"),
                self.tr("If set, client must provide token to create tasks"),
                configItem=cfg.aria2RpcToken,
                placeholder=self.tr("Optional"),
                isPassword=True,
            ),
            SwitchSettingCard(
                FluentIcon.VPN, self.tr("Spoof Browser Fingerprint"),
                self.tr("Attach Browser TLS Fingerprint and Request Headers to tasks received via Aria2 RPC"),
                cfg.aria2RpcEmulateFingerprint,
            ),
        ])

        self.zoomCard = PercentSpinBoxSettingCard(
            FluentIcon.ZOOM, self.tr("UI Scaling"),
            self.tr("Adjust UI scaling (0% for auto)"),
            configItem=cfg.dpiScale,
        )

        personalCards = [
            ComboBoxSettingCard(cfg.themeMode, FluentIcon.BRUSH, self.tr("Application Theme"),
                                self.tr("Change application appearance"),
                                texts=[self.tr("Light"), self.tr("Dark"), self.tr("Follow System Settings")]),
        ]
        if sys.platform == "win32":
            personalCards.append(
                ComboBoxSettingCard(cfg.backgroundEffect, FluentIcon.TRANSPARENT,
                                    self.tr("Window Transparency"),
                                    self.tr("Set window transparency effect"),
                                    texts=["Acrylic", "Mica", "MicaAlt", "Aero", "None"]),
            )
        personalCards.append(self.zoomCard)
        if sys.platform == "darwin":
            self.showDockIconCard = SwitchSettingCard(
                FluentIcon.APPLICATION, self.tr("Show App Icon in Dock"),
                self.tr("If disabled, use the menu bar item to open this window"),
                cfg.shouldShowDockIcon,
            )
            self.showDockSpeedCard = SwitchSettingCard(
                FluentIcon.SPEED_HIGH, self.tr("Show real-time speed on Dock icon"),
                self.tr("Overlay current download speed on Dock icon"),
                cfg.shouldShowDockSpeed,
            )
            self.showDockSpeedCard.setEnabled(cfg.shouldShowDockIcon.value)
            personalCards.extend([
                self.showDockIconCard,
                self.showDockSpeedCard,
                SwitchSettingCard(FluentIcon.SPEED_HIGH, self.tr("Show real-time speed in menu bar"),
                                  self.tr("Show current download speed next to menu bar icon"),
                                  cfg.shouldShowMenuBarSpeed),
            ])
        personalCards.append(
            ComboBoxSettingCard(cfg.language, FluentIcon.LANGUAGE, self.tr("Language"),
                                self.tr("Set the preferred language for the interface"),
                                texts=[LANGUAGE_TEXTS.get(lang, self.tr("Use System Settings"))
                                       for lang in cfg.language.options]),
        )
        self.personalGroup.addSettingCards(personalCards)

        self.autoRunCard = SwitchSettingCard(
            FluentIcon.VPN, self.tr("Start on Boot"),
            self.tr("Run Ghost Downloader silently at system startup"),
            cfg.shouldRunAtLogin,
        )
        from app.config.paths import APP_DATA_DIR, isPortable
        if isPortable():
            self.migrateCard = PushSettingCard(
                self.tr("Switch to User Mode"), FluentIcon.SYNC,
                self.tr("Data Storage Mode"),
                self.tr("Currently in Portable mode, data stored next to app: {0}").format(APP_DATA_DIR),
            )
        else:
            self.migrateCard = PushSettingCard(
                self.tr("Switch to Portable Mode"), FluentIcon.SYNC,
                self.tr("Data Storage Mode"),
                self.tr("Currently in User mode, data stored at: {0}").format(APP_DATA_DIR),
            )

        softwareCards = [
            SwitchSettingCard(FluentIcon.UPDATE, self.tr("Check for updates on startup"),
                              self.tr("Get more features and improved stability with new versions"),
                              cfg.shouldCheckUpdateAtStartup),
            self.autoRunCard,
        ]
        if not IS_ANDROID:
            softwareCards.append(
                ComboBoxSettingCard(
                    cfg.closeMode, FluentIcon.POWER_BUTTON,
                    self.tr("When closing the main window"),
                    self.tr("Choose whether to continue running in background or exit when closing the main window"),
                    texts=[self.tr("Ask when closing"), self.tr("Continue running in background"), self.tr("Exit")],
                ),
            )
        softwareCards.append(
            SwitchSettingCard(FluentIcon.PASTE, self.tr("Monitor Clipboard"),
                              self.tr("Automatically detect links in clipboard and add download tasks"),
                              cfg.isClipboardListenerEnabled),
        )
        if not IS_ANDROID:
            softwareCards.append(self.migrateCard)
        self.softwareGroup.addSettingCards(softwareCards)

        self.feedbackCard = PrimaryPushSettingCard(
            self.tr("Provide Feedback"), FluentIcon.FEEDBACK,
            self.tr("Provide Feedback"),
            self.tr("Help improve Ghost Downloader by providing feedback, or view logs to troubleshoot issues"),
        )
        self.openLogButton = PushButton(self.tr("View Logs"), self.feedbackCard)
        self.feedbackCard.hBoxLayout.insertSpacing(6, 8)
        self.feedbackCard.hBoxLayout.insertWidget(
            7, self.openLogButton, 0, Qt.AlignmentFlag.AlignRight,
        )

        self.aboutCard = PrimaryPushSettingCard(
            self.tr("Check for Updates"), FluentIcon.INFO, self.tr("About"),
            f"© Copyright {YEAR}, {AUTHOR}. Version {VERSION}",
        )

        self.aboutGroup.addSettingCards([
            HyperlinkCard(AUTHOR_URL, self.tr("Open Author's Profile"), FluentIcon.PROJECTOR,
                          self.tr("About the Author"), self.tr("Discover more works by {}").format(AUTHOR)),
            self.feedbackCard,
            self.aboutCard,
        ])

    def _initLayout(self) -> None:
        self.addSettingGroup(self.generalGroup)
        self.addSettingGroup(self.categoryGroup)
        self.addSettingGroup(self.browserGroup)
        self.addSettingGroup(self.aria2RpcGroup)
        self.addSettingGroup(self.personalGroup)
        self.addSettingGroup(self.softwareGroup)
        for group in self._featureService.settingGroups(self.container):
            self.addSettingGroup(group)
        self.addSettingGroup(self.aboutGroup)

    def _bind(self) -> None:
        cfg.appRestartSig.connect(self._showRestartTooltip)
        cfg.browserExtensionPairToken.valueChanged.connect(self._refreshPairTokenCard)
        self._browserService.connectionChanged.connect(self._refreshBrowserStatus)
        if sys.platform == "darwin":
            cfg.shouldShowDockIcon.valueChanged.connect(self.showDockSpeedCard.setEnabled)

        self.downloadFolderPicker.pathChanged.connect(self._onDownloadFolderChanged)
        self.downloadRestoreButton.clicked.connect(
            lambda: (self.downloadFolderPicker.setPath(cfg.downloadFolder.defaultValue),
                     cfg.set(cfg.downloadFolder, cfg.downloadFolder.defaultValue))
        )

        self.browserPairTokenCard.clicked.connect(self._onCopyTokenClicked)
        self.regenerateTokenButton.clicked.connect(self._onRegenerateTokenClicked)
        self.chromiumInstallCard.clicked.connect(self._onChromiumInstallClicked)
        self.exportExtensionButton.clicked.connect(self._onExportExtensionClicked)
        if self.urlSchemeCard:
            self.urlSchemeCard.checkedChanged.connect(self._onUrlSchemeChanged)
        self.autoRunCard.checkedChanged.connect(self._onRunAtLoginChanged)
        self.aboutCard.clicked.connect(self._onAboutCardClicked)
        self.feedbackCard.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(FEEDBACK_URL)))
        self.openLogButton.clicked.connect(self._onOpenLogClicked)
        if not IS_ANDROID:
            self.migrateCard.clicked.connect(self._onMigrateClicked)

    def _onDownloadFolderChanged(self, path: str) -> None:
        cfg.set(cfg.downloadFolder, path)
        self.downloadFolderPicker.saveHistory(path)

    def _showRestartTooltip(self) -> None:
        InfoBar.success(self.tr("Configuration Saved"), self.tr("Restart required to take effect"), duration=1500, parent=self)

    def _refreshPairTokenCard(self) -> None:
        self.browserPairTokenCard.setContent(self._browserService.token)

    def _onCopyTokenClicked(self) -> None:
        token = self._browserService.token
        if not token:
            return
        QApplication.clipboard().setText(token)
        InfoBar.success(self.tr("Token Copied"), token,
                        duration=2000, position=InfoBarPosition.BOTTOM_RIGHT, parent=self.window())

    def _onRegenerateTokenClicked(self) -> None:
        token = self._browserService.regenerateToken()
        QApplication.clipboard().setText(token)
        InfoBar.success(self.tr("Token Regenerated"), self.tr("Copied new token to clipboard"),
                        duration=2000, position=InfoBarPosition.BOTTOM_RIGHT, parent=self.window())

    def _onChromiumInstallClicked(self) -> None:
        from app.services.browser_service import extractBrowserExtension, EXTENSION_UNPACK_DIR

        self._coroutineRunner.submit(
            extractBrowserExtension(),
            done=self._onExtensionExtractDone,
            failed=self._onExtensionExtractFailed,
        )

    def _onExtensionExtractDone(self, path) -> None:
        from app.view.dialogs.extension_install import ExtensionInstallDialog
        ExtensionInstallDialog(path, self.window()).exec()

    def _onExtensionExtractFailed(self, error: str) -> None:
        InfoBar.error(self.tr("Unpack failed"), error,
                      duration=3000, position=InfoBarPosition.BOTTOM_RIGHT, parent=self.window())

    def _refreshBrowserStatus(self) -> None:
        installType, version = self._browserService.connectionSummary
        port = self._browserService.boundPort
        if not installType:
            text = self.tr("Not Connected")
        elif installType == "development":
            text = self.tr("Connected v{} (Desktop-managed)").format(version)
        else:
            text = self.tr("Connected v{} (Store-installed)").format(version)
        self.browserEnableCard.setContent(text)

    def _onExportExtensionClicked(self) -> None:
        from PySide6.QtCore import QFile, QIODevice, QResource
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Select Export Path"),
                                              "./Extension.crx", "Chromium Extension(*.crx)")
        if path:
            f = QFile(path)
            if f.open(QIODevice.OpenModeFlag.WriteOnly):
                f.write(bytes(QResource(":/res/chrome_extension.crx").data()))
                f.close()

    def _onUrlSchemeChanged(self, enabled: bool) -> None:
        from app.platform.url_scheme import registerUrlScheme, unregisterUrlScheme
        if enabled:
            registerUrlScheme()
        else:
            unregisterUrlScheme()

    def _onRunAtLoginChanged(self, enabled: bool) -> None:
        from app.platform.run_at_login import setRunAtLogin
        setRunAtLogin(enabled)

    def _onMigrateClicked(self) -> None:
        from app.config.paths import isPortable, migrate, PORTABLE_PATH, USER_PATH

        target = USER_PATH if isPortable() else PORTABLE_PATH
        mode = self.tr("User Mode") if isPortable() else self.tr("Portable Mode")
        dialog = MessageBox(
            self.tr("Switch Data Storage Mode"),
            self.tr("Are you sure you want to switch to {0}?\n\nData will be copied to the new location, then the program will exit. Please reopen it manually.").format(mode),
            self.window(),
        )
        if not dialog.exec():
            return

        QApplication.instance().aboutToQuit.connect(lambda: migrate(target))
        QApplication.instance().quit()

    def _onAboutCardClicked(self) -> None:
        from app.update import fetchRelease

        InfoBar.info(self.tr("Check for Updates"), self.tr("Checking for updates..."),
                     duration=1500, position=InfoBarPosition.BOTTOM_RIGHT, parent=self.window())
        self._coroutineRunner.submit(
            fetchRelease(),
            done=self._onUpdateChecked, failed=self._onUpdateCheckFailed,
            owner=self,
        )

    def _onUpdateChecked(self, release) -> None:
        from app.config.constants import VERSION
        from app.update import isOutdated

        if not isOutdated(release):
            InfoBar.success(self.tr("You're running the latest version"),
                            self.tr("Current version {0}, latest version {1}").format(VERSION, release.version),
                            duration=3000, position=InfoBarPosition.BOTTOM_RIGHT, parent=self.window())
            return

        from app.update import showReleaseDialog
        showReleaseDialog(release, self.window())

    def _onUpdateCheckFailed(self, error: str) -> None:
        InfoBar.error(self.tr("Failed to check update"), self.tr("Unable to get the latest version information"),
                      duration=3000, position=InfoBarPosition.BOTTOM_RIGHT, parent=self.window())

    def _onOpenLogClicked(self) -> None:
        from app.config.paths import APP_DATA_DIR
        from app.platform.desktop import revealInFolder
        revealInFolder(f"{APP_DATA_DIR}/GhostDownloader.log")

    @property
    def searchPlaceholder(self) -> str:
        return self.tr("Search settings")

    def setSearchText(self, text: str) -> None:
        text = text.strip().lower()
        if not text:
            self._clearSearchFilter()
            return

        hasMatch = False
        for i in range(self.vBoxLayout.count()):
            group = self.vBoxLayout.itemAt(i).widget()
            if not isinstance(group, CollapsibleSettingCardGroup):
                continue
            groupHasMatch = False
            for j in range(group.cardLayout.count()):
                card = group.cardLayout.itemAt(j).widget()
                if card is None:
                    continue
                if self._isSearchMatch(card, text):
                    card.show()
                    groupHasMatch = True
                else:
                    card.hide()
            if groupHasMatch:
                group.show()
                group.cardContainer.setMaximumHeight(QWIDGETSIZE_MAX)
                hasMatch = True
            else:
                group.hide()

        self.emptyStatusWidget.setVisible(not hasMatch)
        if not hasMatch:
            self.emptyStatusWidget.adjustSize()
            self._refreshEmptyWidgetGeometry()

    def _isSearchMatch(self, widget, text: str) -> bool:
        if isinstance(widget, CollapsibleSettingCard):
            widget = widget.card
        title = widget.titleLabel.text().lower()
        content = widget.contentLabel.text().lower()
        return text in title or text in content

    def _clearSearchFilter(self) -> None:
        for i in range(self.vBoxLayout.count()):
            group = self.vBoxLayout.itemAt(i).widget()
            if not isinstance(group, CollapsibleSettingCardGroup):
                continue
            group.show()
            for j in range(group.cardLayout.count()):
                card = group.cardLayout.itemAt(j).widget()
                if card is not None:
                    card.show()
            group.cardContainer.setMaximumHeight(
                0 if group._collapsed else QWIDGETSIZE_MAX
            )
        self.emptyStatusWidget.hide()

    def _refreshEmptyWidgetGeometry(self) -> None:
        self.emptyStatusWidget.move(
            (self.width() - self.emptyStatusWidget.width()) // 2,
            (self.height() - self.emptyStatusWidget.height()) // 2,
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.emptyStatusWidget.isVisible():
            self._refreshEmptyWidgetGeometry()

    def showEvent(self, event) -> None:
        self._restoreOrder()
        super().showEvent(event)

    def _restoreOrder(self) -> None:
        groups = [
            self.vBoxLayout.itemAt(i).widget()
            for i in range(self.vBoxLayout.count())
            if self.vBoxLayout.itemAt(i).widget()
        ]
        keyToWidget = {g.objectName(): g for g in groups}
        order = [k for k in cfg.settingGroupOrder.value if k in keyToWidget]
        rest = [k for k in keyToWidget if k not in order]
        aboutKey = self.aboutGroup.objectName()
        if aboutKey in rest:
            rest.remove(aboutKey)
            rest.append(aboutKey)
        order += rest
        for idx, key in enumerate(order):
            self.vBoxLayout.insertWidget(idx, keyToWidget[key])
        for g in groups:
            if isinstance(g, CollapsibleSettingCardGroup):
                g.updateArrows()
