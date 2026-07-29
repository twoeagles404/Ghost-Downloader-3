# Ghost Downloader

A multi-protocol downloader built on PySide6. The desktop (Windows, macOS, Linux) and Android share the same business engine; the browser extension captures resources and sends them to the desktop app.

## Language

### Tasks

**Task**:
A user-visible download item. Owns a Name (the base name of the finished file) and an Output Folder (the download target directory).
For a single-file task the final path is Output Folder / Name; for a multi-file task it is a directory containing the individual files.
Five states: WAITING (queued), RUNNING (downloading), PAUSED (user paused), COMPLETED (finished), FAILED (failed).
Persisted as a Task Record; the Task Records loaded from the previous run at app startup are called Saved Tasks.
_Avoid_: download, job; Name is not called title or filename; Output Folder is not called directory

**Task Files**:
The download files and temporary segment files a Task produces.
_Avoid_: confusing with Selectable File

**Pausable**:
A Task's pausability, a derived property. Depends on whether the currently running Step can resume from a checkpoint
(for transfer-type Steps, on whether the server supports byte-range).

**Task Error**:
A known failure during task execution — server error, insufficient disk space, runtime not installed, etc.
Carries a user-visible message template (which also serves as an i18n key) and formatting parameters. A Task has a single error boundary.
After a failure, a Step Error (message + params) is recorded on the Step; it exists only at runtime and is not persisted.

### File selection

**Selectable File**:
A checkable download unit inside a multi-file Task — a repository file, a playlist video, a multi-part page, or a torrent file.
Identified by a stable index that does not change with selection. Changing the selection does not create or destroy Steps and is allowed in any Task state;
unselected files keep their partial progress.
_Avoid_: confusing with Task Files

**Revive**:
A completed Task returning to the downloading state because newly selected files have pending download work.
Clears the completion timestamp and automatically starts the Task. Only applies to Tasks in the COMPLETED state.

### Task creation

**Task Options**:
Application-layer options used to parse, create, or edit a Task.
Four sources: browser Resource, page media, merge request, binary installation.
_Avoid_: payload (used only at the raw-transfer seam)

**Task Parser**:
A capability provided by a FeaturePack that turns Task Options into a Task.
Declares a priority and matching rules; higher-priority Parsers are checked first.

**Task Draft**:
The unconfirmed task state before the user confirms. Contains one or more Draft Items, each tracking one URL,
in one of three states: Parsing, Resolved (parsed successfully, holds a Task), or Failed (parse failed).
An item still parsing when the user confirms will wait in the background and auto-submit once parsing completes (deferred confirmation).
The Task Service does not understand draft states.
_Avoid_: pending task, unconfirmed task

**Resource**:
A downloadable item captured by the browser extension. Received by the Browser Service and converted into Task Options to enter the task-creation flow.
_Avoid_: confusing with the generic sense of "resource"

### Task execution

**Task Run**:
A Task's current execution in the download loop. A Task has at most zero or one active Task Run at a time.
The Task Run iterates the Task Steps in the order of the Steps still to complete.
_Avoid_: execution, session

**Task Step**:
An executable step inside a Task. A Task may have one or more Steps.
_Avoid_: stage, phase, action

**Subworker**:
A segment-transfer unit inside an HTTP or FTP Step, responsible for one byte-range interval.
_Avoid_: worker, thread, chunk

### Application actors

**Task Service**:
The single public entry point owning the user-visible task workflow: add, start, pause, delete,
redownload, edit, setCategory, applySelection, resumeSaved, stop.
_Avoid_: directly manipulating a Task's state transitions

**Feature Service**:
Owns pack discovery, parser priority routing, and the pack lifecycle.
Routes Task Options to the matching Parser. If no parser matches, it fails;
this failure happens before Task creation and is not a Task Error.

**FeaturePack**:
A plugin package. May provide a task parser, card, file type, binary runtime, page, or setting group.
_Avoid_: module, extension

**Binary Runtime**:
A family of external executables that a FeaturePack can probe for or provide install tasks for.

**Browser Service**:
The protocol adapter for the browser extension: receives extension messages, translates them into Task Service verbs, and returns results.

**Clipboard Listener**:
The clipboard listener. Monitors clipboard changes, filters out URLs, and emits a notification.

**Category**:
Download categorization and target-directory rules. Matches file extensions to a category and resolves the download directory.
_Avoid_: group, tag, type

**Coroutine Runner**:
The application actor that runs async work and bridges results back to the UI thread. Knows nothing about Tasks.

**Speed Meter**:
The global download-speed monitor. The download engine feeds it byte counts, and it aggregates them and emits a speed-change notification every second.
It also provides a global rate-limit gate.

**Signal Bus**:
A process-level event bus. Carries only cross-module application-level events, not task or business signals — those live on their respective Services.

**Client**:
An HTTP client with optional TLS-fingerprint spoofing.

**Plan**:
A "do X after all tasks complete" intent: shut down, restart, sleep, or open a file.

**Settings**:
Application-level user configuration.
_Avoid_: options (options are per-Task input, not application configuration)

## Example dialogue

> **Dev:** "When the user presses pause, do we delete the Task?"
> **Domain expert:** "No. Pause stops the Task Run. The Task Record and Task Files are kept."

> **Dev:** "When the user presses redownload, do we create a new Task?"
> **Domain expert:** "No. Redownload stops the Task Run, deletes the Task Files, resets the same Task, and starts a new Task Run."
