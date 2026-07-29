# Ghost Downloader Browser Extension

A Chromium / Firefox browser extension. It captures downloadable resources on a page and sends them to the desktop app over a persistent connection.

Shares the definitions of **Resource** and **Task Options** with the desktop app (see the root CONTEXT.md).

## Language

### Upstream dependency

**cat-catch**:
An embedded third-party open-source extension that provides three capability surfaces:
DOM media discovery (the addMedia channel), media playback control (the getVideoState protocol), and a feature-script library (recorder, webrtc, etc.).
The MSE Probe is a standalone reimplementation modeled on cat-catch that only emits signals and never caches data.
_Avoid_: conflating cat-catch features with our own Page Media system

### Desktop connection

**Desktop Bridge**:
A persistent connection to the desktop Browser Service. Supports automatic reconnect on disconnect and offline queueing.
While offline, download requests are queued in the Task Queue and flushed automatically after reconnect.
_Avoid_: desktop connection, socket

**Pairing**:
The authorization flow before the Desktop Bridge establishes a connection. After the user confirms authorization on the desktop side, the extension receives a connection credential.

**Task Queue**:
The extension-side offline send queue. Caches download requests while the Desktop Bridge is unreachable, then sends them one by one after reconnect.
_Avoid_: confusing it with the desktop app's Task Queue — this is the extension-side offline buffer

**Connection State**:
The Desktop Bridge connection state: missing\_token, connecting, authenticating,
connected, unauthorized, disconnected. The popup UI shows a connection indicator based on this.

**Task Summary**:
A task summary pushed by the desktop. The extension does not own the Task, only the Task Summary as a read-only view of task state.

### Resource capture

**Resource Bridge**:
The resource capturer. Captures downloadable resources through two paths — network requests and page scripts (cat-catch) —
caches them in the Resource Cache, then converts them into Task Options the desktop can understand.
_Avoid_: resource manager

**Resource Cache**:
An in-memory cache of captured resources. It also keeps a Header Snapshot — a snapshot of the network request's headers —
so the desktop can reuse the browser's auth credentials to download resources that require login.
_Avoid_: resource store, resource map

### Page media

**Page Media**:
The content-script-side media detection and attribution system. Detects media playing on a page, attributes network URLs
to specific video elements, and offers the user a download button. It is made of four cooperating layers:
MSE Probe → Attribution Engine → Download Button, with a Resolution Strategy providing per-site resolution logic.
The same URL may exist simultaneously in the Resource Cache (as a Resource) and in the Attribution Engine
(as an attributed URL of a Video Session). The popup resource panel takes the Resource path; the Download Button takes the Page Media path.

**MSE Probe**:
Observes the browser's internal media-stream mechanics and reports events to the Attribution Engine via Attribution Signals.
Intercepts object-URL creation, buffer additions, data appends, and network requests
to establish the "which network request fed which player" association.

**Attribution Signal**:
The cross-execution-context communication channel between the MSE Probe and the Attribution Engine.
The two run in different script isolation environments, and the Signal is the only bridging mechanism.

**Attribution Engine**:
Attributes network URLs to playing video elements. Its core data model is the Video Session.
Uses the Attribution Tier to judge attribution confidence and the Attribution Ledger to arbitrate URL-ownership disputes.

**Video Session**:
A lifecycle-tracking unit for one video element inside the Attribution Engine.
States: inert → armed → ready → waiting → resolving → dispatched / failed / refused.
Tracks all URLs attributed to that video.
_Avoid_: video tracker, media session

**Attribution Tier**:
Attribution-confidence grading. Determines the priority of URL ownership — from highest confidence (buffer-append confirmed)
to lowest (unique-session fallback). A higher tier can seize URL ownership from a lower tier.

**Attribution Ledger**:
A cross-session ledger of URL ownership. Arbitrates cases where multiple Video Sessions contend for the same URL
(e.g. preload scenarios where several videos share the same CDN URL).

**Download Button**:
A download button floating over active media. On click it asks the Attribution Engine to resolve,
and once it has a Resolution it sends it to the Resource Bridge to forward to the desktop.

**Resolution Strategy**:
Per-site download resolution logic (YouTube, X, Douyin, Instagram, generic).
Pure functions that cannot call back into the Attribution Engine. They output a Resolution.

**Resolution**:
The output of a Resolution Strategy. Three outcomes:
selection (a download decision), pending (waiting for more information), refused (declined).

**Selection**:
The download decision within a Resolution. Four forms:
single (a single file), stream (streaming segments), merge (video + audio merge), external (handed to a desktop-side external tool).

### Media control

**Media Bridge**:
Media playback control. Gets video playback state and sends control commands through the cat-catch content script.
The Media Snapshot is the single source of truth.

**Media Snapshot**:
A snapshot of the current tab's media playback state. Includes the playlist, current index, and play/pause state.
Eliminates state fragmentation across multiple data sources.

### Feature toggles

**Feature Bridge**:
Per-tab feature-toggle management. Toggles come in two kinds: dynamically injected (effective immediately after switching)
and refresh-required (need a page reload after switching). Persisted to local storage; reconciled with the active tab list on load.

### Popup communication

**Popup Protocol**:
A typed communication protocol between the popup and the background.
Commands come in two kinds: StateCommand (query state) and ActionCommand (perform an action).
_Avoid_: popup API, popup bridge
