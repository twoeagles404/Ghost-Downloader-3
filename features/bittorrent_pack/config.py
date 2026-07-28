from __future__ import annotations

from app.config.cfg import ConfigItem
from app.models.pack import PackConfig
from qfluentwidgets import (
    BoolValidator,
    OptionsConfigItem,
    OptionsValidator,
    RangeConfigItem,
    RangeValidator,
)

from .web_tracker.schema import (
    DEFAULT_WEB_TRACKER_SOURCES,
    SourceCacheSerializer,
    SourceCacheValidator,
)


class StringListValidator:
    def validate(self, value) -> bool:
        return isinstance(value, list) and all(isinstance(i, str) for i in value)

    def correct(self, value) -> list:
        if not isinstance(value, list):
            return []
        return [i for i in value if isinstance(i, str)]


class BitTorrentConfig(PackConfig):
    enableDht = ConfigItem("BitTorrent", "EnableDHT", True, BoolValidator())
    enableLsd = ConfigItem("BitTorrent", "EnableLSD", True, BoolValidator())
    enableWebTrackers = ConfigItem("BitTorrent", "EnableWebTrackers", True, BoolValidator())
    autoRefreshWebTrackers = ConfigItem("BitTorrent", "AutoRefreshWebTrackers", True, BoolValidator())
    saveMagnetFile = ConfigItem("BitTorrent", "SaveMagnetTorrentFile", False, BoolValidator())
    seedingRatioLimit = RangeConfigItem("BitTorrent", "SeedRatioLimitPercent", 0, RangeValidator(0, 10000))
    seedingTimeLimit = RangeConfigItem("BitTorrent", "SeedTimeLimitMinutes", 0, RangeValidator(0, 43200))
    maxConnections = RangeConfigItem("BitTorrent", "ConnectionsLimit", 500, RangeValidator(20, 2000))
    maxUploadSpeed = RangeConfigItem("BitTorrent", "UploadRateLimit", 0, RangeValidator(0, 1024 * 1024 * 100))
    listenPort = RangeConfigItem("BitTorrent", "ListenPort", 0, RangeValidator(0, 65535))
    metadataTimeout = RangeConfigItem("BitTorrent", "MetadataTimeout", 30, RangeValidator(5, 300))
    enableSequentialDownload = ConfigItem("BitTorrent", "SequentialDownload", False, BoolValidator())
    storageMode = OptionsConfigItem(
        "BitTorrent", "StorageMode", "sparse", OptionsValidator(["sparse", "allocate"]),
    )
    associateFileTypes = ConfigItem("BitTorrent", "AssociateFileTypes", False, BoolValidator())
    webTrackerSources = ConfigItem(
        "BitTorrent", "WebTrackerSources", DEFAULT_WEB_TRACKER_SOURCES, StringListValidator(),
    )
    webTrackerSourceCache = ConfigItem(
        "BitTorrent", "WebTrackerSourceCache", {}, SourceCacheValidator(), SourceCacheSerializer(),
    )
    webTrackerCustomList = ConfigItem("BitTorrent", "WebTrackerCustomList", "")

    def settingGroups(self, parent: QWidget) -> list[CollapsibleSettingCardGroup]:
        import sys
        from qfluentwidgets import ComboBoxSettingCard, FluentIcon, RangeSettingCard, SwitchSettingCard
        from app.view.components.setting_card_group import CollapsibleSettingCardGroup
        from app.view.components.setting_cards import SpinBoxSettingCard
        from .web_tracker.card import WebTrackerCard

        btGroup = CollapsibleSettingCardGroup(self.tr("BitTorrent Download"), "bittorrent", parent)

        cards = []
        if sys.platform != "darwin":
            cards.append(SwitchSettingCard(
                FluentIcon.LINK, self.tr("Associate Torrent Files"),
                self.tr("Set Ghost Downloader as the default handler for .torrent files"),
                self.associateFileTypes, btGroup,
            ))
        cards += [
            SpinBoxSettingCard(FluentIcon.GLOBE, self.tr("Port"),
                self.tr("0 for system assigned port"), "", self.listenPort, btGroup, 1),
            SpinBoxSettingCard(FluentIcon.HISTORY, self.tr("Metadata Timeout"),
                self.tr("Maximum loading time for metadata when parsing magnet links"), " s", self.metadataTimeout, btGroup, 5),
            RangeSettingCard(self.maxConnections, FluentIcon.PEOPLE, self.tr("Maximum Connections"),
                self.tr("Maximum connections per BT task session"), btGroup),
            SpinBoxSettingCard(FluentIcon.SHARE, self.tr("Upload Speed Limit"),
                self.tr("0 for unlimited, in KB/s per session"), " KB/s",
                self.maxUploadSpeed, btGroup, 64, 1 / 1024),
            SpinBoxSettingCard(FluentIcon.SHARE, self.tr("Auto Seeding Ratio Limit"),
                self.tr("0 means no seed ratio limit, 100% means a seed ratio of 1.0"), " %",
                self.seedingRatioLimit, btGroup, 50),
            SpinBoxSettingCard(FluentIcon.STOP_WATCH, self.tr("Auto Seeding Time Limit"),
                self.tr("0 means no seeding time limit"), " min",
                self.seedingTimeLimit, btGroup, 10),
            ComboBoxSettingCard(self.storageMode, FluentIcon.SAVE, self.tr("File Allocation Method"),
                self.tr("Sparse allocation minimizes disk writes; Pre-allocation allocates spaces in advance"),
                texts=[self.tr("Sparse allocation"), self.tr("Pre-allocation")], parent=btGroup),
            SwitchSettingCard(FluentIcon.SAVE, self.tr("Save Magnet Torrent File"),
                self.tr("Additionally save .torrent file when downloading magnet links"), self.saveMagnetFile, btGroup),
            SwitchSettingCard(FluentIcon.LIBRARY, self.tr("Sequential Download"),
                self.tr("Download files sequentially, suitable for watching while downloading but may reduce overall efficiency"),
                self.enableSequentialDownload, btGroup),
            SwitchSettingCard(FluentIcon.GLOBE, self.tr("Enable DHT"),
                self.tr("Allow peer discovery via DHT network"), self.enableDht, btGroup),
            SwitchSettingCard(FluentIcon.HOME, self.tr("Enable LSD"),
                self.tr("Broadcast and discover peers on local network for the same torrent"), self.enableLsd, btGroup),
            SwitchSettingCard(FluentIcon.LINK, self.tr("Enable Web Tracker"),
                self.tr("Merge configured extra Trackers into new BT tasks"),
                self.enableWebTrackers, btGroup),
            SwitchSettingCard(FluentIcon.SYNC, self.tr("Refresh Web Tracker on New Task Creation"),
                self.tr("Refresh trackers from tracker sources when creating new BitTorrent tasks"),
                self.autoRefreshWebTrackers, btGroup),
            WebTrackerCard(self.submit, btGroup),
        ]
        btGroup.addSettingCards(cards)
        return [btGroup]


bittorrentConfig = BitTorrentConfig()
