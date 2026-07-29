# File selection filters by a flag instead of adding/removing Steps

Multi-file tasks (HuggingFace repos, FTP directories, torrents, YouTube playlists, Bilibili multi-part)
once had five separate selection implementations, and the base-class approach was "unchecking deletes the
corresponding Step, re-checking rebuilds it." We changed to a single semantics:
**Steps are created in full during parsing/discovery and are never deleted because of selection; the `selected`
flag decides status aggregation, progress snapshots, and whether `pendingSteps()` skips it**
(`Task._isStepSelected`).

Reasons for dropping the add/remove selection model:

1. **No lost progress**. Deleting a Step and rebuilding it via `fromFile` resets the `downloadedBytes`
   resume point to zero; flipping the flag naturally preserves partial downloads.
2. **Runtime re-selection becomes safe**. Adding to or removing from the `steps` list while the run loop is
   iterating it has lifecycle risks; flipping a flag does not. This is the foundation of "change selection in
   any state" (`taskService.applySelection`).
3. **One file can map to multiple Steps**. On YouTube one video is a group of four steps (extract/video/audio/merge),
   and one Bilibili part is 3-4 steps; the protocol of `fromFile` returning a single Step cannot hold that.
   Flag filtering associates by `step.fileIndex`, so group size does not matter.

Costs and consequences:

- Steps for unselected files stay in the `steps` list and are serialized (negligible size).
- All four entry points for status aggregation (`updateStatus`/`setStatus`/`pendingSteps`/`currentSnapshot`)
  must filter out unselected Steps — missing `updateStatus` would cause the task to never complete.
- Step construction is a pack-private responsibility (the parser, or `__post_init__` rebuilding from an old
  archive); the base class no longer has the `stepType`/`fromFile` protocol.
- BT exception: selection maps to libtorrent file priorities (a single Step, no `fileIndex`), overriding
  `setSelection` autonomy.
- Output filenames for multi-part/playlists follow "total > 1" rather than "selected count," ensuring that
  changing the selection does not trigger a rename.
