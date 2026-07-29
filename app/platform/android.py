from __future__ import annotations

import re
import sys
from functools import lru_cache

IS_ANDROID = hasattr(sys, "getandroidapilevel")


@lru_cache(maxsize=1)
def nativeLibraryDir() -> str:
    from jnius import autoclass
    activity = autoclass("org.kivy.android.PythonActivity").mActivity
    return activity.getApplicationInfo().nativeLibraryDir


def isSystemDark() -> bool:
    from jnius import autoclass
    Configuration = autoclass("android.content.res.Configuration")
    activity = autoclass("org.kivy.android.PythonActivity").mActivity
    uiMode = activity.getResources().getConfiguration().uiMode
    return (uiMode & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES


WRITE_EXTERNAL_STORAGE = "android.permission.WRITE_EXTERNAL_STORAGE"


def isStorageGranted() -> bool:
    from jnius import autoclass
    # API30+ scoped storage: downloading to any public dir needs All Files Access; API<30 (Android 9/10) falls back to runtime WRITE permission
    # (On Android 10, the manifest's requestLegacyExternalStorage still lets WRITE freely write to external storage).
    if autoclass("android.os.Build$VERSION").SDK_INT >= 30:
        return autoclass("android.os.Environment").isExternalStorageManager()
    PackageManager = autoclass("android.content.pm.PackageManager")
    activity = autoclass("org.kivy.android.PythonActivity").mActivity
    return activity.checkSelfPermission(WRITE_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED


def requestStoragePermission() -> None:
    from jnius import autoclass
    activity = autoclass("org.kivy.android.PythonActivity").mActivity
    if autoclass("android.os.Build$VERSION").SDK_INT >= 30:
        Settings = autoclass("android.provider.Settings")
        Uri = autoclass("android.net.Uri")
        Intent = autoclass("android.content.Intent")
        intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
        intent.setData(Uri.parse("package:" + activity.getPackageName()))
        activity.startActivity(intent)
        return
    # <30 shows the runtime permission dialog; the result is re-checked for the banner by MainWindow's applicationStateChanged, no callback needed.
    activity.requestPermissions([WRITE_EXTERNAL_STORAGE], 0)


_fileUriPolicyRelaxed = False


def _relaxFileUriPolicy() -> None:
    # On Android 24+, using Uri.fromFile to launch an external app throws FileUriExposedException, so relax StrictMode
    global _fileUriPolicyRelaxed
    if _fileUriPolicyRelaxed:
        return
    from jnius import autoclass
    StrictMode = autoclass("android.os.StrictMode")
    VmPolicyBuilder = autoclass("android.os.StrictMode$VmPolicy$Builder")
    StrictMode.setVmPolicy(VmPolicyBuilder().build())
    _fileUriPolicyRelaxed = True


def _launchView(path: str, mimeType: str) -> None:
    from jnius import autoclass
    _relaxFileUriPolicy()
    Uri = autoclass("android.net.Uri")
    File = autoclass("java.io.File")
    Intent = autoclass("android.content.Intent")
    activity = autoclass("org.kivy.android.PythonActivity").mActivity
    intent = Intent(Intent.ACTION_VIEW)
    intent.setDataAndType(Uri.fromFile(File(path)), mimeType)
    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    try:
        activity.startActivity(intent)
    except Exception as error:
        from loguru import logger
        logger.opt(exception=error).info("Failed to open, giving up: {} ({})", path, mimeType)


def openFile(filePath) -> None:
    from jnius import autoclass
    text = str(filePath)
    extension = text.rsplit(".", 1)[-1].lower() if "." in text else ""
    mimeType = autoclass("android.webkit.MimeTypeMap").getSingleton().getMimeTypeFromExtension(extension) or "*/*"
    _launchView(text, mimeType)


def openFolder(folder) -> None:
    _launchView(str(folder), "vnd.android.document/directory")


def toTaskUrls(text: str) -> list[str]:
    matches = re.findall(r'(?i)(?:https?|ftp)://[^\s"\'<>，。！？、；：）》】」]+', text)
    return [url.rstrip(".,!?;:)]}>") for url in matches]


def sharedText() -> str | None:
    from jnius import autoclass
    Intent = autoclass("android.content.Intent")
    activity = autoclass("org.kivy.android.PythonActivity").mActivity
    intent = activity.getIntent()
    if intent is None or intent.getAction() != Intent.ACTION_SEND:
        return None
    text = intent.getCharSequenceExtra(Intent.EXTRA_TEXT)  # use the CharSequence version: getStringExtra returns null for styled text
    if text is None:
        return ""
    return text if isinstance(text, str) else text.toString()  # pyjnius converts String to str; a styled CharSequence is the wrapper object


def clearShare() -> None:
    from jnius import autoclass
    Intent = autoclass("android.content.Intent")
    activity = autoclass("org.kivy.android.PythonActivity").mActivity
    intent = activity.getIntent()
    if intent is not None:
        intent.setAction(Intent.ACTION_MAIN)  # share already taken; prevent re-adding the same share when returning to foreground
