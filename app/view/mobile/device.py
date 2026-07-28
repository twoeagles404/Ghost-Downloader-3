from __future__ import annotations


def setupAccentColor() -> None:
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QApplication
    from qfluentwidgets import setThemeColor

    from app.config.cfg import cfg

    palette = QApplication.palette()
    for role in (QPalette.ColorRole.Accent, QPalette.ColorRole.Highlight):
        color = palette.color(role)
        if color.isValid() and cfg.themeColor.value != color:
            setThemeColor(color, save=False)
            return


def setupTheme() -> None:
    import darkdetect
    from qfluentwidgets import setTheme

    from app.config.cfg import cfg
    from app.platform.android import isSystemDark

    def themeName() -> str:
        return "Dark" if isSystemDark() else "Light"

    darkdetect.theme = themeName
    darkdetect.isDark = isSystemDark
    setTheme(cfg.themeMode.value, save=False)


def setupFont() -> None:
    from loguru import logger
    from PySide6.QtGui import QFontDatabase
    from qfluentwidgets import qconfig

    # Android's Qt platform font library registers all system fonts at startup, so just use them by name.
    # never addApplicationFont a system font: it's redundant and segfaults Qt on MIUI's MiSans variable font.
    known = set(QFontDatabase.families())
    preferred = ("MiSans VF", "MiSans", "OPPO Sans", "OplusSans", "HarmonyOS Sans SC", "vivo Sans")
    picked = next((name for name in preferred if name in known), None)

    logger.info("System font: {}", picked or "sans-serif (fallback)")
    qconfig.set(qconfig.fontFamilies, [picked, "sans-serif"] if picked else ["sans-serif"], save=False)


def setupTouchScrolling(window) -> None:
    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtWidgets import QAbstractScrollArea, QScroller, QScrollerProperties, QWidget
    from qfluentwidgets.components.settings.expand_setting_card import ExpandSettingCard

    class ScrollClickGuard(QObject):
        def __init__(self, parent):
            super().__init__(parent)
            self._pressPosition = None

        def eventFilter(self, obj, event) -> bool:
            eventType = event.type()
            if eventType == QEvent.Type.MouseButtonPress:
                self._pressPosition = event.globalPosition().toPoint()
            elif eventType == QEvent.Type.MouseButtonRelease and self._pressPosition is not None:
                moved = (event.globalPosition().toPoint() - self._pressPosition).manhattanLength()
                self._pressPosition = None
                if moved > 12:
                    return True
            return False

    guard = ScrollClickGuard(window)
    for scrollArea in window.findChildren(QAbstractScrollArea):
        if isinstance(scrollArea, ExpandSettingCard):
            continue
        QScroller.grabGesture(scrollArea.viewport(), QScroller.ScrollerGestureType.TouchGesture)
        scroller = QScroller.scroller(scrollArea.viewport())
        properties = scroller.scrollerProperties()
        noOvershoot = QScrollerProperties.OvershootPolicy.OvershootAlwaysOff
        properties.setScrollMetric(QScrollerProperties.ScrollMetric.VerticalOvershootPolicy, noOvershoot)
        properties.setScrollMetric(QScrollerProperties.ScrollMetric.HorizontalOvershootPolicy, noOvershoot)
        scroller.setScrollerProperties(properties)
        for child in scrollArea.findChildren(QWidget):
            child.installEventFilter(guard)
