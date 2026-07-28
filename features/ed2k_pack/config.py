from __future__ import annotations

import platform
import sys
from pathlib import Path

from app.config.paths import APP_DATA_DIR
from app.models.pack import BinaryRuntime, PackConfig
from app.platform.filesystem import findExecutable, toPosixPath
from PySide6.QtCore import QT_TRANSLATE_NOOP as N
from qfluentwidgets import ConfigItem, BoolValidator, FluentIcon, RangeConfigItem, RangeValidator

RELEASE_BASE = "https://github.com/XiaoYouChR/Python-eD2k/releases/latest/download"


class ED2kConfig(PackConfig):
    installFolder = ConfigItem("ED2k", "InstallFolder", f"{APP_DATA_DIR}/goed2kd")
    enableDht = ConfigItem("ED2k", "EnableDHT", True, BoolValidator())
    enableUpnp = ConfigItem("ED2k", "EnableUPnP", True, BoolValidator())
    listenPort = RangeConfigItem("ED2k", "ListenPort", 0, RangeValidator(0, 65535))
    serverMetSource = ConfigItem("ED2k", "ServerMetSource", "http://upd.emule-security.org/server.met")
    nodesDatSource = ConfigItem("ED2k", "NodesDatSource", "http://upd.emule-security.org/nodes.dat")

    def settingGroups(self, parent: QWidget) -> list[CollapsibleSettingCardGroup]:
        from qfluentwidgets import FluentIcon, SwitchSettingCard
        from app.view.components.setting_card_group import CollapsibleSettingCardGroup
        from app.view.components.setting_cards import (
            LineEditSettingCard, SelectFolderSettingCard, SpinBoxSettingCard,
        )

        group = CollapsibleSettingCardGroup(self.tr("eD2k Download"), "ed2k", parent)
        installFolderCard = SelectFolderSettingCard(
            ed2kConfig.installFolder, f"{APP_DATA_DIR}/goed2kd",
            self.tr("goed2kd Install Location"),
            group,
        )
        runtimeCard = self.createRuntimeCard(ed2kRuntime, group)

        installFolderCard.pathChanged.connect(runtimeCard._onInstallFolderChanged)
        group.addSettingCards([
            installFolderCard,
            runtimeCard,
            LineEditSettingCard(
                FluentIcon.GLOBE, self.tr("Server List Source"),
                self.tr("URL of the eD2k server.met file; leave empty to skip bootstrapping"),
                self.serverMetSource, group,
            ),
            LineEditSettingCard(
                FluentIcon.GLOBE, self.tr("DHT Node Source"),
                self.tr("URL of the KAD nodes.dat file; leave empty to skip bootstrapping"),
                self.nodesDatSource, group,
            ),
            SwitchSettingCard(
                FluentIcon.WIFI, self.tr("Enable DHT"),
                self.tr("Discover peers via DHT network; when disabled, only eD2k servers are used"),
                self.enableDht, group,
            ),
            SwitchSettingCard(
                FluentIcon.GLOBE, self.tr("Enable UPnP"),
                self.tr("Automatically configure router port forwarding"),
                self.enableUpnp, group,
            ),
            SpinBoxSettingCard(
                FluentIcon.LINK, self.tr("Port"),
                self.tr("0 for system assigned port"), "",
                self.listenPort, group, 1,
            ),
        ])
        runtimeCard.refreshStatus()
        return [group]


ed2kConfig = ED2kConfig()


class ED2kRuntime(BinaryRuntime):
    name = "goed2kd"
    canInstall = True
    title = N("BinaryRuntime", "eD2k / eMule")
    description = N("BinaryRuntime", "Supports the eD2k protocol, suitable for downloading classic resources")
    icon = FluentIcon.BOOK_SHELF
    isRecommended = False

    def path(self) -> str:
        return findExecutable(Path(ed2kConfig.installFolder.value), "goed2kd")

    def isAppManaged(self) -> bool:
        p = self.path()
        return bool(p) and Path(p).is_relative_to(Path(ed2kConfig.installFolder.value))

    async def fetchLatestVersion(self) -> str:
        from app.update import fetchGitHubLatestTag
        return await fetchGitHubLatestTag("XiaoYouChR/Python-eD2k")

    def delete(self) -> None:
        import shutil
        folder = Path(ed2kConfig.installFolder.value)
        if folder.exists():
            shutil.rmtree(folder)

    async def installTask(self):
        from app.models.task import TaskOptions
        from disk_pack.task import InstallTask
        from .task import ED2kInstallStep

        assetName = _assetName()
        url = f"{RELEASE_BASE}/{assetName}"
        installFolder = Path(ed2kConfig.installFolder.value)
        binaryName = "goed2kd.exe" if sys.platform == "win32" else "goed2kd"
        binaryPath = toPosixPath(installFolder / binaryName)

        download = await self.parse(
            TaskOptions(url=url, outputFolder=installFolder)
        )
        downloadStep = download.steps[0]
        downloadStep.stepIndex = 1
        downloadStep.outputFile = binaryPath

        task = InstallTask(
            name=f"goed2kd installation ({assetName})",
            url=url,
            packId="ed2k",
            fileSize=download.fileSize,
            outputFolder=installFolder,
            installFolder=str(installFolder),
        )
        task.addStep(downloadStep)
        task.addStep(ED2kInstallStep(stepIndex=2, binaryPath=binaryPath))
        return task


def _assetName() -> str:
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "amd64"
    if sys.platform == "win32":
        return f"goed2kd-windows-{arch}.exe"
    elif sys.platform == "darwin":
        return f"goed2kd-darwin-{arch}"
    else:
        return f"goed2kd-linux-{arch}"


ed2kRuntime = ED2kRuntime()
