# CLAUDE.md

## Philosophy (the constitution — when a scenario isn't covered by the rules below, come back here to decide)

- **Simple is better than complex.** (Zen)
- **Flat is better than nested.** (Zen) — functions over classes, inlining over jumping around, three lines of repetition over premature abstraction
- **Explicit is better than implicit.** (Zen) — pass dependencies explicitly, inject configuration explicitly, don't create implicit coupling through module-level global state
- **Readability counts.** (Zen) — code is read more than it is written. Name things from the business domain, avoid obscure words; "comments only explain Why" assumes the code itself already explains What
- **Signal-driven actors.** — a Service owns private state and communicates outward only through signals; a Service does not hold a View reference (a View holding a Service reference to connect signals is allowed)
- **YAGNI — trust internals, validate at boundaries.** — don't write hypothetical defenses, delete rather than comment out, don't keep backward-compatibility aliases
- **If the implementation is hard to explain, it's a bad idea.** (Zen) — a design that's convoluted to explain is probably wrong

## Naming

- Class names PascalCase, functions and variables camelCase
- Function names use a verb prefix (PowerShell style): `taskService.add()`, `featureService.parse()`
- Choose short, common words that a first-time reader can understand
- When the class name provides context, drop the redundant noun: `taskService.add()`, not `addTask()`
- Lock nouns to CONTEXT.md, don't use synonyms: `task` not `download`, `name` not `title`
- Don't use a `_` prefix to mark module-internal functions — the module boundary is itself the encapsulation
- Name an Actor after the business concept it owns; ban manager, controller, coordinator, provider, repository, facade, pipeline, context
- Booleans use an `is*` / `has*` / `can*` / `should*` prefix
- Signals `{noun}{PastParticiple}` (`taskAdded`, `speedChanged`); when the class name already provides context you may use just `{PastParticiple}`. Slots `_on{Noun}{PastParticiple}`
- Noun lookups use the noun form: `taskById(id)`, `categoryById(id)`. `find*` is reserved for disk/PATH searches
- Filesystem words: `folder` (definitely a directory), `file` (definitely a file), `path` (could be a file or a directory)

## Verb table

A closed vocabulary — function names may only pick a verb from here. If none fits, the responsibility is unclear or the seam is wrong.

| Verb | Meaning |
|---|---|
| `load` | Read local persisted data or resources. Not fetch |
| `save` | Persist application state |
| `fetch` | Get data with a single network request. Not load |
| `probe` | Query a capability or metadata, without creating a task |
| `parse` | Turn text/protocol output into application objects |
| `match` | Judge whether a candidate satisfies a rule |
| `find` | Search the local disk or PATH |
| `build` | Purely construct from known data, no side effects. Not create |
| `create` | Create a real resource (spawn, allocate, connect). Not build |
| `to*` | Convert a representation: `toSafeFilename`, `toPosixPath` |
| `set` | Assign local state, caller provides the final value. Not update |
| `update` | Recompute state from caller input. Not refresh |
| `refresh` | Re-query on its own, no caller input. Not update |
| `add` | Add a business object |
| `start` / `pause` / `stop` | Begin execution / user-visible pause / stop the current execution |
| `resume` | Start recovery |
| `remove` | Detach from memory/model/UI, doesn't delete on disk. Not delete |
| `delete` | Destructively delete from disk or a persistent record. Not remove |
| `clear` | Empty a collection, input, selection, or cache |
| `mount` / `unmount` | Create/reclaim lazily-managed widgets entering/leaving the viewport |
| `flush` | Write buffered state to disk |
| `cancel` | Abandon async work, doesn't delete records |
| `open` / `close` | Open/close a file, URL, socket, dialog |
| `reveal` | Show in the file manager |
| `run` | Execute a workflow step owned by the current actor |
| `supervise` | The worker's internal supervisor: sample progress, store recovery data |
| `install` | Place a runtime or binary on disk |
| `send` | Push data to another system, one-way with no response |
| `request` | Ask another actor to perform an action |
| `on*` | Qt slot, signal reaction, event reaction |

## Four-phase `__init__`

QWidget / QDialog subclasses uniformly use four-phase initialization:

```python
def __init__(self, parent=None):
    super().__init__(parent)
    self._initWidget()   # create and configure child widgets, don't connect signals
    self._initLayout()   # assemble layout: margins, spacing, addWidget
    self._bind()         # connect signals to slots, all widgets already exist
```

## Anti-patterns (fix them on sight)

**Violating "Flat is better than nested":**
- A wrapper function that only does if/elif dispatch → let the caller call the corresponding function directly
- A class nested inside a method without using a closure → hoist it to module level
- A function name repeating a noun the class name already provides → drop the noun

**Violating "Explicit is better than implicit":**
- Module-level `global` mutable state disguised as a singleton → hoist to a class, or inject explicitly as a frozen dataclass
- Passing structured data as a dict → use a dataclass
- Passing a whole object but using only one of its methods → pass a callable, keep the dependency narrowest

**Violating YAGNI:**
- The same fact described in multiple docs → one fact in one place, link to it elsewhere

**Violating "Simple is better than complex":**
- Mixing in logic that isn't this module's responsibility because it was "convenient" → keep a single responsibility

**Violating "Readability counts":**
- A comment or doc restating what the code already says → delete it, the code says the What itself
