from __future__ import annotations

import ast
import platform
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QT_TRANSLATE_NOOP as N, Qt
from PySide6.QtWidgets import QWidget
from qfluentwidgets import (
    BoolValidator, CaptionLabel, ConfigItem, FluentIcon, FolderValidator,
    PushButton, SettingCard, ToolButton, ToolTipFilter,
)

from app.config.paths import APP_DATA_DIR
from app.models.pack import BinaryRuntime, PackConfig
from app.platform.android import IS_ANDROID
from app.platform.filesystem import findExecutable

PYPI_API = "https://pypi.org/pypi/yt-dlp/json"
QJS_RELEASE_BASE = "https://github.com/quickjs-ng/quickjs/releases/latest/download"
COOKIE_DOMAIN = ".youtube.com"
AUTH_COOKIE_NAMES = ("LOGIN_INFO", "SAPISID", "__Secure-1PAPISID", "__Secure-3PAPISID")


def cookieFile() -> Path:
    return Path(APP_DATA_DIR) / "YtDlp" / "cookies.txt"


def hasCookieFile() -> bool:
    path = cookieFile()
    return path.is_file() and path.stat().st_size > 0


def saveCookies(cookieString: str) -> None:
    lines = ["# Netscape HTTP Cookie File"]
    for pair in cookieString.split(";"):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        name, _, value = pair.partition("=")
        lines.append(f"{COOKIE_DOMAIN}\tTRUE\t/\tTRUE\t0\t{name.strip()}\t{value.strip()}")
    path = cookieFile()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def saveCookiesIfBetter(cookieString: str) -> None:
    if any(name in cookieString for name in AUTH_COOKIE_NAMES):
        saveCookies(cookieString)


def loadCookieHeader() -> str:
    path = cookieFile()
    if not path.is_file():
        return ""
    pairs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            pairs.append(f"{parts[5]}={parts[6]}")
    return "; ".join(pairs)


def clearCookies() -> None:
    path = cookieFile()
    if path.is_file():
        path.unlink()


class YtDlpConfig(PackConfig):
    installFolder = ConfigItem("YtDlp", "InstallFolder", f"{APP_DATA_DIR}/YtDlp", FolderValidator())
    subtitleLanguages = ConfigItem("YtDlp", "SubtitleLanguages", "en")
    shouldPreferMp4 = ConfigItem("YtDlp", "PreferMp4", True, BoolValidator())
    shouldEmbedMetadata = ConfigItem("YtDlp", "EmbedMetadata", True, BoolValidator())
    shouldEmbedChapters = ConfigItem("YtDlp", "EmbedChapters", True, BoolValidator())

    def settingGroups(self, parent: QWidget) -> list:
        from qfluentwidgets import FluentIcon, SwitchSettingCard
        from app.view.components.setting_card_group import CollapsibleSettingCardGroup
        from app.view.components.setting_cards import SelectFolderSettingCard

        group = CollapsibleSettingCardGroup(self.tr("YouTube Download"), "ytdlp", parent)

        runtimeCard = self.createRuntimeCard(youTubeRuntime, group)
        cards = [runtimeCard]

        if not IS_ANDROID:
            installFolderCard = SelectFolderSettingCard(
                ytDlpConfig.installFolder, f"{APP_DATA_DIR}/YtDlp",
                self.tr("Runtime install directory"),
                group,
            )
            installFolderCard.pathChanged.connect(runtimeCard._onInstallFolderChanged)
            cards.insert(0, installFolderCard)

        cards.append(CookieSettingCard(group))

        cards.extend([
            SwitchSettingCard(
                FluentIcon.VIDEO,
                self.tr("Prefer MP4 Format"),
                self.tr("Prefer H.264/MP4 codec to avoid WebM/MKV output"),
                self.shouldPreferMp4,
                group,
            ),
            SwitchSettingCard(
                FluentIcon.INFO,
                self.tr("Embed Metadata"),
                self.tr("Embed metadata (title, author, etc.) into file after download"),
                self.shouldEmbedMetadata,
                group,
            ),
            SwitchSettingCard(
                FluentIcon.BOOK_SHELF,
                self.tr("Embed Chapters"),
                self.tr("Embed chapter markers into file after download"),
                self.shouldEmbedChapters,
                group,
            ),
        ])

        group.addSettingCards(cards)
        runtimeCard.refreshStatus()
        return [group]


ytDlpConfig = YtDlpConfig()


class YouTubeRuntime(BinaryRuntime):
    name = "YouTube runtime"
    canInstall = True
    title = N("BinaryRuntime", "YouTube Download")
    description = N("BinaryRuntime", "Supports hundreds of video sites such as YouTube and Twitter")
    icon = FluentIcon.GLOBE
    isRecommended = True

    def path(self) -> str:
        folder = Path(ytDlpConfig.installFolder.value)
        if not (folder / "yt_dlp" / "__init__.py").is_file():
            return ""
        return self.qjsPath()

    def isAppManaged(self) -> bool:
        folder = Path(ytDlpConfig.installFolder.value)
        return (folder / "yt_dlp" / "__init__.py").is_file()

    def ytDlpFolder(self) -> Path:
        return Path(ytDlpConfig.installFolder.value)

    def qjsPath(self) -> str:
        if IS_ANDROID:
            from app.platform.android import nativeLibraryDir
            binary = Path(nativeLibraryDir()) / "libqjs.so"
            return str(binary) if binary.is_file() else ""
        return findExecutable(Path(ytDlpConfig.installFolder.value), "qjs")

    async def probeVersion(self) -> str:
        ytDlpDir = Path(ytDlpConfig.installFolder.value) / "yt_dlp"
        versionFile = ytDlpDir / "version.py"
        if not versionFile.is_file():
            return ""

        ytDlpVersion = ""
        try:
            text = versionFile.read_text(encoding="utf-8")
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "__version__":
                            if isinstance(node.value, ast.Constant):
                                ytDlpVersion = str(node.value.value)
        except Exception:
            pass

        qjsPath = self.qjsPath()
        if qjsPath:
            import asyncio
            process = await asyncio.create_subprocess_exec(
                qjsPath, "--version",
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await process.communicate()
            isQjsOk = process.returncode == 0
        else:
            isQjsOk = False

        parts = []
        if ytDlpVersion:
            parts.append(f"yt-dlp {ytDlpVersion}")
        if isQjsOk:
            parts.append("QuickJS ✓")
        return " | ".join(parts) if parts else ""

    async def fetchLatestVersion(self) -> str:
        from app.client import buildClient
        client = buildClient(timeout=15)
        try:
            resp = await client.get(PYPI_API)
            resp.raise_for_status()
            data = await resp.json()
            return data.get("info", {}).get("version", "")
        finally:
            client.close()

    def isNewer(self, installed: str, latest: str) -> bool:
        if not installed or not latest:
            return False
        prefix = "yt-dlp "
        if prefix not in installed:
            return False
        from PySide6.QtCore import QVersionNumber
        current = installed.split(prefix, 1)[1].split(" ", 1)[0].split("|", 1)[0].strip()
        v1 = QVersionNumber.fromString(current)
        v2 = QVersionNumber.fromString(latest)
        return v2 > v1

    def delete(self) -> None:
        import shutil
        folder = Path(ytDlpConfig.installFolder.value)
        if folder.exists():
            shutil.rmtree(folder)

    async def installTask(self):
        from app.config.cfg import cfg, currentHeaders
        from disk_pack.task import ExtractStep, InstallTask
        from http_pack.task import HttpTaskStep

        whlUrl, whlSize = await self._fetchWhlAsset()

        installFolder = Path(ytDlpConfig.installFolder.value)
        installFolder.mkdir(parents=True, exist_ok=True)
        archiveName = "yt_dlp.zip"

        if IS_ANDROID:
            task = InstallTask(
                name="yt-dlp installation",
                url=whlUrl,
                packId="disk",
                fileSize=whlSize,
                outputFolder=installFolder,
                installFolder=str(installFolder),
            )
            task.addStep(HttpTaskStep(
                stepIndex=1,
                url=whlUrl,
                fileSize=whlSize,
                headers=currentHeaders(),
                subworkerCount=cfg.preBlockNum.value,
                canUseRangeRequests=True,
                outputFile=str(installFolder / archiveName),
            ))
            task.addStep(ExtractStep(
                stepIndex=2,
                archivePath=str(installFolder / archiveName),
                outputFolder=str(installFolder),
                archiveSize=whlSize,
            ))
            return task

        from disk_pack.task import BinaryInstallStep
        from app.models.task import TaskOptions

        qjsBinaryName = "qjs.exe" if sys.platform == "win32" else "qjs"
        qjsDownload = await self.parse(TaskOptions(
            url=f"{QJS_RELEASE_BASE}/{_qjsAssetName()}",
            outputFolder=installFolder,
        ))
        qjsStep = qjsDownload.steps[0]
        qjsStep.stepIndex = 2
        qjsStep.outputFile = str(installFolder / qjsBinaryName)

        task = InstallTask(
            name="YouTube runtime installation",
            url=whlUrl,
            packId="disk",
            fileSize=whlSize + max(0, qjsDownload.fileSize),
            outputFolder=installFolder,
            installFolder=str(installFolder),
        )
        task.addStep(HttpTaskStep(
            stepIndex=1,
            url=whlUrl,
            fileSize=whlSize,
            headers=currentHeaders(),
            subworkerCount=cfg.preBlockNum.value,
            canUseRangeRequests=True,
            outputFile=str(installFolder / archiveName),
        ))
        task.addStep(qjsStep)
        task.addStep(ExtractStep(
            stepIndex=3,
            archivePath=str(installFolder / archiveName),
            outputFolder=str(installFolder),
            archiveSize=whlSize,
        ))
        task.addStep(BinaryInstallStep(
            stepIndex=4,
            binaryPath=str(installFolder / qjsBinaryName),
        ))
        return task

    async def _fetchWhlAsset(self) -> tuple[str, int]:
        from app.client import buildClient

        client = buildClient(timeout=15)
        try:
            response = await client.get(PYPI_API)
            response.raise_for_status()
            data = await response.json()
        finally:
            client.close()

        urls = data.get("urls") or []
        for entry in urls:
            if entry.get("packagetype") == "bdist_wheel" and entry.get("filename", "").endswith(".whl"):
                return entry["url"], entry.get("size") or 0
        raise RuntimeError("yt-dlp wheel package not found")

def _qjsAssetName() -> str:
    machine = platform.machine().lower()
    if sys.platform == "win32":
        arch = "x86" if machine in {"x86", "i386", "i686"} else "x86_64"
        return f"qjs-windows-{arch}.exe"
    elif sys.platform == "darwin":
        return "qjs-darwin"
    else:
        arch = "aarch64" if machine in {"arm64", "aarch64"} else "x86_64"
        return f"qjs-linux-{arch}"


class CookieSettingCard(SettingCard):

    def __init__(self, parent=None):
        super().__init__(
            FluentIcon.CERTIFICATE,
            QCoreApplication.translate("YtDlpConfig", "YouTube Cookie"),
            self._statusText(),
            parent,
        )
        self._importButton = PushButton(
            QCoreApplication.translate("YtDlpConfig", "Import"),
            self,
        )
        self._clearButton = ToolButton(FluentIcon.DELETE, self)
        self._clearButton.setToolTip(
            QCoreApplication.translate("YtDlpConfig", "Clear Cookie")
        )
        self._clearButton.installEventFilter(ToolTipFilter(self._clearButton))
        self._clearButton.setVisible(hasCookieFile())

        self.hBoxLayout.addWidget(self._importButton, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(8)
        self.hBoxLayout.addWidget(self._clearButton, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self._importButton.clicked.connect(self._onImportClicked)
        self._clearButton.clicked.connect(self._onClearClicked)

    def _statusText(self) -> str:
        if hasCookieFile():
            return QCoreApplication.translate("YtDlpConfig", "Imported")
        return QCoreApplication.translate(
            "YtDlpConfig", "A cookie is required to download content that requires login. It is recommended to automatically import it using the browser extension."
        )

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        self.setContent(self._statusText())
        self._clearButton.setVisible(hasCookieFile())

    def _onImportClicked(self) -> None:
        from qfluentwidgets import MessageBoxBase, SubtitleLabel, PlainTextEdit

        dialog = MessageBoxBase(self.window())
        dialog.widget.setMinimumWidth(500)
        dialog.viewLayout.addWidget(SubtitleLabel(
            QCoreApplication.translate("YtDlpConfig", "Import YouTube Cookie"),
            dialog,
        ))

        label = CaptionLabel(
            QCoreApplication.translate(
                "YtDlpConfig",
                "After installing the browser extension, downloading YouTube videos automatically includes login info, no manual steps needed.\n"
                "To import manually: open YouTube and log in, press F12 to open DevTools, and in the Network tab"
                "Find any request, copy the value of its Cookie request header and paste it below.",
            ),
            dialog,
        )
        label.setWordWrap(True)
        dialog.viewLayout.addWidget(label)

        editor = PlainTextEdit(dialog)
        editor.setPlaceholderText("SID=xxx; HSID=xxx; ...")
        editor.setMinimumHeight(120)
        dialog.viewLayout.addWidget(editor)

        if dialog.exec():
            text = editor.toPlainText().strip()
            if text:
                saveCookies(text)
                self._refresh()

    def _onClearClicked(self) -> None:
        clearCookies()
        self._refresh()


youTubeRuntime = YouTubeRuntime()
