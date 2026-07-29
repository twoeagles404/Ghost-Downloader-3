<h4 align="right">
  English
</h4>

<div align="center">

![Banner](.github/assets/banner.webp)

### Cross-platform multithreaded downloader

[![Release][release-shield]][release-url]
[![Downloads][downloads-shield]][release-url]
[![License][license-shield]][license-url]

[Report a Bug](https://github.com/twoeagles404/Ghost-Downloader-3/issues/new?template=bug_report.yml) · [Request a Feature](https://github.com/twoeagles404/Ghost-Downloader-3/issues/new?template=feature_request.yml)

</div>

## Features

* IDM-style intelligent chunking⚡ without requiring file merging, plus smart acceleration 🚀
* Frees UI resources when minimized to tray🍃 — minimal memory footprint in the background
* Supports HTTP, Magnet / BT, FTP, M3U8, MPEG-DASH, eD2k and more 🌐
* Emulates real-browser TLS fingerprints🥷 so downloads are less likely to be blocked by anti-bot checks
* Parses YouTube▶️ and Bilibili videos — playlists, up to 4K/HDR, subtitles and login supported
* Dedicated parsers for GitHub🐙 releases and HuggingFace🤗 models with mirror acceleration
* Records M3U8 live streams📺 with real-time decryption🔓, fully supported on Android as well
* A companion browser extension🦊 sniffs page media, takes over browser downloads, and controls tasks without leaving the browser
* aria2-compatible RPC interface🔌 — third-party tools can push tasks directly
* Tasks can be paused, edited✏️ (URL, headers, proxy) and resumed without losing progress
* A complete Android version📱 with background downloading and completion notifications 🔔

## Supported platforms

|    Platform    | Required Version |  Architectures   | Compatible |
|:--------------:|:----------------:|:----------------:|:----------:|
|  🐧 **Linux**  |  `glibc 2.35+`   | `x86_64`/`arm64` |     ✅      |
| 🪟 **Windows** |      `10+`       | `x86_64`/`arm64` |     ✅      |
|  🍎 **macOS**  |     `13.0+`      | `x86_64`/`arm64` |     ✅      |
| 🤖 **Android** |     `10.0+`      |   `arm64-v8a`    |     ✅      |

> [!WARNING]
> Qt `6.6+` no longer supports CPUs without the `AVX` instruction set.

## Building from source

This is a Python project managed with [uv](https://github.com/astral-sh/uv).

```bash
# Install dependencies
uv sync

# Run from source
uv run python Ghost-Downloader-3.py

# Build a standalone app bundle (Nuitka)
uv run scripts/deploy.py
```

Multi-platform installers are produced by the **Build / Release** GitHub Actions workflow.

## Roadmap

- ❌ Make the plugin API public
- ❌ Enhanced task editing (e.g. binding multiple sessions to one task)

Visit the [open issues](https://github.com/twoeagles404/Ghost-Downloader-3/issues) to see requested features and known issues.

## Contributing

Contributions are welcome. If you have a suggestion, fork the repo and open a pull request, or open an issue with the "Enhancement" tag.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a pull request

## Built with

* [aioftp](https://github.com/aio-libs/aioftp) — FTP client/server for asyncio
* [cat-catch](https://github.com/xifangczy/cat-catch) — browser resource-sniffing extension
* [desktop-notifier](https://github.com/samschott/desktop-notifier) — cross-platform desktop notifications
* [FFmpeg](https://ffmpeg.org/) — record, convert and stream audio and video
* [goed2k](https://github.com/monkeyWie/goed2k) — the eD2k download daemon
* [libtorrent](https://github.com/arvidn/libtorrent) — C++ BitTorrent implementation
* [loguru](https://github.com/Delgan/loguru) — Python logging
* [m3u8](https://github.com/globocom/m3u8) — Python m3u8 parser
* [mpegdash](https://github.com/sangoma/mpegdash) — MPEG-DASH MPD parser
* [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE) — DASH/HLS/MSS download tool
* [Nuitka](https://github.com/Nuitka/Nuitka) — the Python compiler
* [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) — Fluent Design widget library
* [PySide6](https://github.com/PySide/pyside-setup) — the official Python Qt bindings
* [QuickJS-NG](https://github.com/quickjs-ng/quickjs) — small embeddable JavaScript engine
* [uvloop](https://github.com/MagicStack/uvloop) — ultra-fast asyncio event loop
* [winloop](https://github.com/Vizonex/Winloop) — uvloop alternative for Windows
* [wreq](https://github.com/0x676e67/wreq-python) — HTTP client with TLS fingerprint emulation
* [yt-dlp](https://github.com/yt-dlp/yt-dlp) — feature-rich audio/video downloader

## License

Distributed under the GPL v3.0 License. See `LICENSE` for details.

Copyright © 2024-2026 XiaoYouChR. Fork maintained by [@twoeagles404](https://github.com/twoeagles404).

## Credits

Based on the upstream **Ghost-Downloader-3** project by XiaoYouChR. Credit for the original application design and implementation belongs to the upstream authors and contributors, as required by the GPL v3.0 license.

[release-shield]: https://img.shields.io/github/v/release/twoeagles404/Ghost-Downloader-3?style=for-the-badge
[release-url]: https://github.com/twoeagles404/Ghost-Downloader-3/releases/latest
[downloads-shield]: https://img.shields.io/github/downloads/twoeagles404/Ghost-Downloader-3/total?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/twoeagles404/Ghost-Downloader-3?style=for-the-badge
[license-url]: https://github.com/twoeagles404/Ghost-Downloader-3/blob/main/LICENSE
