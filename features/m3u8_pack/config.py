from __future__ import annotations

import platform
import sys
from pathlib import Path

from PySide6.QtCore import QT_TRANSLATE_NOOP as N
from qfluentwidgets import (
    BoolValidator,
    ConfigItem,
    FluentIcon,
    FolderValidator,
    OptionsConfigItem,
    OptionsValidator,
    RangeConfigItem,
    RangeValidator,
)

from app.config.paths import APP_DATA_DIR
from app.models.pack import BinaryRuntime, PackConfig
from app.models.task import Task
from app.platform.android import IS_ANDROID, nativeLibraryDir
from app.platform.filesystem import findExecutable

M3U8_REPO = "nilaoda/N_m3u8DL-RE"


class M3U8Config(PackConfig):
    installFolder = ConfigItem("M3U8", "InstallFolder", f"{APP_DATA_DIR}/M3U8DL", FolderValidator())
    associateFileTypes = ConfigItem("M3U8", "AssociateFileTypes", False, BoolValidator())
    outputFormat = OptionsConfigItem("M3U8", "OutputFormat", "mp4", OptionsValidator(["mp4", "mkv"]))
    threadCount = RangeConfigItem("M3U8", "ThreadCount", 8, RangeValidator(1, 64))
    retryCount = RangeConfigItem("M3U8", "RetryCount", 3, RangeValidator(0, 20))
    requestTimeout = RangeConfigItem("M3U8", "RequestTimeout", 100, RangeValidator(5, 600))
    shouldAutoSelect = ConfigItem("M3U8", "AutoSelect", True, BoolValidator())
    shouldConcurrentDownload = ConfigItem("M3U8", "ConcurrentDownload", True, BoolValidator())
    shouldAppendUrlParams = ConfigItem("M3U8", "AppendUrlParams", False, BoolValidator())
    shouldBinaryMerge = ConfigItem("M3U8", "BinaryMerge", False, BoolValidator())
    shouldCheckSegmentsCount = ConfigItem("M3U8", "CheckSegmentsCount", True, BoolValidator())
    shouldKeepLiveSegments = ConfigItem("M3U8", "LiveKeepSegments", False, BoolValidator())
    shouldUseLivePipeMux = ConfigItem("M3U8", "LivePipeMux", False, BoolValidator())
    shouldFixLiveVtt = ConfigItem("M3U8", "LiveFixVtt", False, BoolValidator())
    liveWaitTime = RangeConfigItem("M3U8", "LiveWaitTime", 0, RangeValidator(0, 100000))
    liveTakeCount = RangeConfigItem("M3U8", "LiveTakeCount", 0, RangeValidator(0, 1000))
    decryptionEngine = OptionsConfigItem(
        "M3U8", "DecryptionEngine", "FFmpeg",
        OptionsValidator(["FFmpeg", "MP4Decrypt", "Shaka Packager"]),
    )
    decryptionBinaryPath = ConfigItem("M3U8", "DecryptionBinaryPath", "")
    shouldUseMp4RealTimeDecryption = ConfigItem("M3U8", "MP4RealTimeDecryption", True, BoolValidator())
    maxSpeed = RangeConfigItem("M3U8", "MaxSpeed", -1, RangeValidator(-1, 1000000))
    speedUnit = OptionsConfigItem("M3U8", "SpeedUnit", "Mbps", OptionsValidator(["Mbps", "Kbps"]))
    adKeyword = ConfigItem("M3U8", "AdKeyword", "")
    subtitleFormat = OptionsConfigItem("M3U8", "SubtitleFormat", "SRT", OptionsValidator(["SRT", "VTT"]))
    shouldOmitDateInfo = ConfigItem("M3U8", "NoDateInfo", False, BoolValidator())
    shouldKeepImageSegments = ConfigItem("M3U8", "KeepImageSegments", False, BoolValidator())
    shouldDeleteTemp = ConfigItem("M3U8", "DelAfterDone", True, BoolValidator())
    customMuxAfterDone = ConfigItem("M3U8", "CustomMuxAfterDone", "")
    shouldSelectAllAudioSubtitle = ConfigItem("M3U8", "SelectAllAudioSubtitle", True, BoolValidator())

    def settingGroups(self, parent: QWidget) -> list[CollapsibleSettingCardGroup]:
        import sys
        from qfluentwidgets import ComboBoxSettingCard, FluentIcon, RangeSettingCard, SwitchSettingCard
        from app.view.components.setting_card_group import CollapsibleSettingCardGroup
        from app.view.components.setting_cards import (
            SelectFolderSettingCard, LineEditSettingCard, SelectFileCard, SpinBoxSettingCard,
        )

        m3u8Group = CollapsibleSettingCardGroup(self.tr("M3U8 Download"), "m3u8", parent)
        installFolderCard = SelectFolderSettingCard(
            self.installFolder, f"{APP_DATA_DIR}/M3U8DL",
            self.tr("N_m3u8DL-RE Install Location"),
            m3u8Group,
        )
        runtimeCard = self.createRuntimeCard(m3u8Runtime, m3u8Group)

        cards = [installFolderCard, runtimeCard]
        if sys.platform != "darwin":
            cards.append(SwitchSettingCard(
                FluentIcon.LINK, self.tr("Associate M3U8/MPD Files"),
                self.tr("Set Ghost Downloader as the default handler for .m3u8/.m3u/.mpd files"),
                self.associateFileTypes, m3u8Group,
            ))
        cards += [
            ComboBoxSettingCard(self.outputFormat, FluentIcon.VIDEO, self.tr("Output Container"),
                self.tr("After VOD download, prefer using FFmpeg to remux to specified container"), texts=["MP4", "MKV"], parent=m3u8Group),
            RangeSettingCard(self.threadCount, FluentIcon.CLOUD, self.tr("Chunk Threads"),
                self.tr("Download threads passed to N_m3u8DL-RE"), m3u8Group),
            RangeSettingCard(self.retryCount, FluentIcon.SYNC, self.tr("Chunk Retry Attempts"),
                self.tr("Maximum retries for failed chunks"), m3u8Group),
            SpinBoxSettingCard(FluentIcon.HISTORY, self.tr("Request Timeout"), self.tr("HTTP request timeout length"),
                " s", self.requestTimeout, m3u8Group, 5),
            SwitchSettingCard(FluentIcon.ACCEPT, self.tr("Auto Select Best Track"),
                self.tr("Default to best audio/video track"), self.shouldAutoSelect, m3u8Group),
            SwitchSettingCard(FluentIcon.PAUSE, self.tr("Simultaneous Audio/Video Download"),
                self.tr("Simultaneously download selected audio, video and subtitle tracks"), self.shouldConcurrentDownload, m3u8Group),
            SwitchSettingCard(FluentIcon.LINK, self.tr("Append URL Parameters"),
                self.tr("Append query parameters from input URL to chunk requests"), self.shouldAppendUrlParams, m3u8Group),
            SwitchSettingCard(FluentIcon.ALIGNMENT, self.tr("Binary Merge"),
                self.tr("Let N_m3u8DL-RE merge chunks in binary mode"), self.shouldBinaryMerge, m3u8Group),
            SwitchSettingCard(FluentIcon.SEARCH, self.tr("Verify Chunk Count"),
                self.tr("Verify chunk count is as expected after download completion"), self.shouldCheckSegmentsCount, m3u8Group),
            SwitchSettingCard(FluentIcon.SAVE, self.tr("Keep original segments for live streams"),
                self.tr("Keep downloaded segments when merging live recordings in real time"), self.shouldKeepLiveSegments, m3u8Group),
            SwitchSettingCard(FluentIcon.CODE, self.tr("Live Pipe Remux"),
                self.tr("Pipe to FFmpeg for real-time remuxing during recording"), self.shouldUseLivePipeMux, m3u8Group),
            SwitchSettingCard(FluentIcon.FONT, self.tr("Correct VTT subtitles for live streams"),
                self.tr("Adjust VTT subtitle timeline based on audio start time"), self.shouldFixLiveVtt, m3u8Group),
            SpinBoxSettingCard(FluentIcon.STOP_WATCH, self.tr("Live refresh wait time"),
                self.tr("Seconds between live playlist fetches, 0 for auto"), " s", self.liveWaitTime, m3u8Group, 1),
            SpinBoxSettingCard(FluentIcon.DOWNLOAD, self.tr("Live segment fetch count"),
                self.tr("Max segments to fetch per refresh, 0 for auto"), "", self.liveTakeCount, m3u8Group, 1),
            ComboBoxSettingCard(self.decryptionEngine, FluentIcon.CERTIFICATE, self.tr("Decryption Engine"),
                self.tr("Third-party decryption program used"), texts=["FFmpeg", "MP4Decrypt", "Shaka Packager"], parent=m3u8Group),
            SelectFileCard(FluentIcon.COMMAND_PROMPT, self.tr("Decryption engine binary path"),
                self.tr("Path to MP4Decrypt / Shaka Packager executable; leave empty to use FFmpeg"),
                configItem=self.decryptionBinaryPath, parent=m3u8Group),
            SwitchSettingCard(FluentIcon.FINGERPRINT, self.tr("MP4 Real-time Decryption"),
                self.tr("Decrypt MP4 segments in real time during download"), self.shouldUseMp4RealTimeDecryption, m3u8Group),
            SpinBoxSettingCard(FluentIcon.SPEED_HIGH, self.tr("Speed Limit"),
                self.tr("Max download speed, -1 for unlimited"), "", self.maxSpeed, m3u8Group, 1),
            ComboBoxSettingCard(self.speedUnit, FluentIcon.TAG, self.tr("Speed Limit Unit"),
                self.tr("Unit for speed limit value"), texts=["Mbps", "Kbps"], parent=m3u8Group),
            LineEditSettingCard(FluentIcon.REMOVE, self.tr("Ad Filter"),
                self.tr("Regex matching ad segment URLs"), self.adKeyword, m3u8Group, placeholder=self.tr("Regular Expression")),
            ComboBoxSettingCard(self.subtitleFormat, FluentIcon.DICTIONARY, self.tr("Subtitle Format"),
                self.tr("Subtitle output format"), texts=["SRT", "VTT"], parent=m3u8Group),
            SwitchSettingCard(FluentIcon.DATE_TIME, self.tr("Do not write date info"),
                self.tr("Do not write date info during remux"), self.shouldOmitDateInfo, m3u8Group),
            SwitchSettingCard(FluentIcon.PHOTO, self.tr("Keep graphical segments"),
                self.tr("Keep original segments after converting graphical subtitles to images"), self.shouldKeepImageSegments, m3u8Group),
            SwitchSettingCard(FluentIcon.DELETE, self.tr("Delete temp files after completion"),
                self.tr("Delete segment temp directory after download"), self.shouldDeleteTemp, m3u8Group),
            SwitchSettingCard(FluentIcon.MUSIC, self.tr("Download all audio tracks and subtitles"),
                self.tr("Default to download all audio and subtitle tracks"), self.shouldSelectAllAudioSubtitle, m3u8Group),
            LineEditSettingCard(FluentIcon.VIDEO, self.tr("Custom Remux Arguments"),
                self.tr("Custom --mux-after-done; leave empty to auto-remux according to output container"),
                self.customMuxAfterDone, m3u8Group, placeholder="format=mp4"),
        ]
        m3u8Group.addSettingCards(cards)
        installFolderCard.pathChanged.connect(runtimeCard._onInstallFolderChanged)
        runtimeCard.refreshStatus()
        return [m3u8Group]


m3u8Config = M3U8Config()


class M3U8Runtime(BinaryRuntime):
    name = "N_m3u8DL-RE"
    canInstall = not IS_ANDROID
    title = N("BinaryRuntime", "M3U8 / Live download")
    description = N("BinaryRuntime", "Supports streaming protocols such as HLS and DASH, and can record live streams")
    icon = FluentIcon.MEDIA
    isRecommended = True

    def path(self) -> str:
        if IS_ANDROID:
            nativeDir = nativeLibraryDir()
            if not nativeDir:
                return ""
            binary = Path(nativeDir) / "libnm3u8dlre.so"
            return str(binary) if binary.exists() else ""
        return findExecutable(Path(m3u8Config.installFolder.value), "N_m3u8DL-RE")

    def isAppManaged(self) -> bool:
        p = self.path()
        return bool(p) and Path(p).is_relative_to(Path(m3u8Config.installFolder.value))

    async def fetchLatestVersion(self) -> str:
        from app.update import fetchGitHubLatestTag
        return await fetchGitHubLatestTag(M3U8_REPO)

    def delete(self) -> None:
        import shutil
        folder = Path(m3u8Config.installFolder.value)
        if folder.exists():
            shutil.rmtree(folder)

    async def installTask(self) -> Task:
        machine = platform.machine().lower()
        if sys.platform == "win32":
            if machine in {"amd64", "x86_64"}:
                target = "win-x64"
            elif machine in {"arm64", "aarch64"}:
                target = "win-arm64"
            else:
                target = "win-NT6.0-x86"
        elif sys.platform == "darwin":
            target = "osx-arm64" if machine in {"arm64", "aarch64"} else "osx-x64"
        elif sys.platform == "linux":
            target = "linux-arm64" if machine in {"arm64", "aarch64"} else "linux-x64"
        else:
            raise RuntimeError(f"One-click N_m3u8DL-RE installation is not supported on the current platform yet: {sys.platform}")

        url, tag = await self._fetchAssetUrl(target)

        from app.models.task import BinaryInstallOptions
        binaryName = "N_m3u8DL-RE.exe" if sys.platform == "win32" else "N_m3u8DL-RE"
        return await self.parse(BinaryInstallOptions(
            url=url,
            outputFolder=Path(m3u8Config.installFolder.value),
            name=f"N_m3u8DL-RE {tag} ({target})",
            executableNames=(binaryName,),
        ))

    async def _fetchAssetUrl(self, target: str) -> tuple[str, str]:
        from app.client import buildClient
        url = f"https://api.github.com/repos/{M3U8_REPO}/releases/latest"
        client = buildClient(headers={"accept": "application/vnd.github+json"}, timeout=15)
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = await resp.json()
        finally:
            client.close()

        tag = data.get("tag_name", "")
        extension = ".zip" if sys.platform == "win32" else ".tar.gz"
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if target in name and name.endswith(extension):
                return asset["browser_download_url"], tag
        raise RuntimeError(f"No match found for {target} N_m3u8DL-RE installer package")


m3u8Runtime = M3U8Runtime()
