from __future__ import annotations

from shlex import split as splitShellTokens
from typing import Final

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence, QValidator
from PySide6.QtWidgets import (
    QApplication, QCompleter, QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget,
)
from qfluentwidgets import (
    FluentIcon, LineEdit, TeachingTip, TeachingTipTailPosition, ToolTipFilter,
    TransparentToolButton,
)

from app.view.components.editors import AutoSizingEdit


CURL_HEADER_FLAGS: Final[frozenset[str]] = frozenset({"-H", "--header"})
COMMAND_SEPARATORS: Final[frozenset[str]] = frozenset({";", "&", "&&", "|", "||"})
CURL_VALUE_FLAGS: Final[dict[str, str]] = {
    "-b": "cookie", "--cookie": "cookie",
    "-A": "user-agent", "--user-agent": "user-agent",
    "-e": "referer", "--referer": "referer",
}


def toLogicalLines(text: str) -> list[str]:
    merged = text.replace("\r\n", "\n").replace("\\\n", " ").replace("^\n", " ")
    return [line.strip() for line in merged.splitlines() if line.strip()]


def parseHeaderLine(line: str) -> tuple[str, str] | None:
    name, separator, value = line.partition(":")
    name = name.strip()
    # an empty name is an HTTP/2 pseudo-header, whitespace is the request line - neither is a header, and sending as-is would break the request
    if not separator or not name or any(char.isspace() for char in name):
        return None
    return name, value.strip()


def parseCurl(line: str) -> list[tuple[str, str]]:
    try:
        tokens = splitShellTokens(line.replace("$'", "'"))
    except ValueError:
        return []

    rows: list[tuple[str, str]] = []
    index = 1
    while index < len(tokens) - 1:
        token = tokens[index]
        # Windows' "Copy all as cURL" joins multiple commands with & on one line; stop here
        if token in COMMAND_SEPARATORS:
            break
        if token in CURL_HEADER_FLAGS:
            row = parseHeaderLine(tokens[index + 1])
            if row:
                rows.append(row)
        elif token in CURL_VALUE_FLAGS:
            rows.append((CURL_VALUE_FLAGS[token], tokens[index + 1].strip()))
        else:
            index += 1
            continue
        index += 2
    return rows


def parseHeaders(text: str) -> list[tuple[str, str]]:
    # dispatch line by line rather than an all-or-nothing block, otherwise a bare line added after cURL would be silently swallowed
    rows: list[tuple[str, str]] = []
    hasCurl = False
    for line in toLogicalLines(text):
        if line[:5].lower() == "curl ":
            # One set of headers belongs to one request. "Copy all as cURL" is multiple requests,
            # the header set produced by mixing them corresponds to no real request, so only the first is accepted.
            if hasCurl:
                continue
            hasCurl = True
            rows.extend(parseCurl(line))
            continue
        row = parseHeaderLine(line)
        if row:
            rows.append(row)
    return rows


def toHeadersText(rows: list[tuple[str, str]]) -> str:
    return "\n".join(f"{name}: {value}" if value else name for name, value in rows)


def toHeaderRows(text: str) -> list[tuple[str, str]]:
    # literal splitting, zero discard - view switching must be lossless; cleaning only happens on paste
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        name, separator, value = line.partition(":")
        rows.append((name.strip(), value.strip()) if separator else (line.strip(), ""))
    return rows


class HeaderNameValidator(QValidator):

    # a colon splits a row whose "Key contains a colon" into two on view round-trips; whitespace is an illegal header name
    def validate(self, text: str, pos: int):
        if ":" in text or any(char.isspace() for char in text):
            return QValidator.State.Invalid, text, pos
        return QValidator.State.Acceptable, text, pos


class HeaderCellEdit(LineEdit):

    def __init__(self, parent=None, *, isName: bool, onPaste):
        super().__init__(parent)
        self.isName = isName
        self._onPaste = onPaste

    # QLineEdit's Ctrl+V does not go through paste(); the right-click menu does - both paths converge here
    def paste(self) -> None:
        if self._onPaste(self, QApplication.clipboard().text()):
            return
        super().paste()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.matches(QKeySequence.StandardKey.Paste):
            self.paste()
            return
        super().keyPressEvent(event)


HEADER_SUGGESTIONS: Final[list[str]] = [
    "accept", "accept-encoding", "accept-language", "authorization",
    "cache-control", "cookie", "origin", "range", "referer", "user-agent",
]


class HeaderRow(QWidget):

    def __init__(self, parent=None, *, name: str = "", value: str = "",
                 onPaste, onEdited, onRemoved):
        super().__init__(parent)
        self._name = name
        self._value = value
        self._onEdited = onEdited
        self._onRemoved = onRemoved

        self.nameEdit = HeaderCellEdit(self, isName=True, onPaste=onPaste)
        self.valueEdit = HeaderCellEdit(self, isName=False, onPaste=onPaste)
        self.removeButton = TransparentToolButton(FluentIcon.CLOSE, self)

        self._initWidget()
        self._initLayout()
        self._bind()

    def _initWidget(self) -> None:
        completer = QCompleter(HEADER_SUGGESTIONS, self.nameEdit)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.nameEdit.setCompleter(completer)
        self.nameEdit.setValidator(HeaderNameValidator(self.nameEdit))
        self.nameEdit.setPlaceholderText(self.tr("Name"))
        self.nameEdit.setText(self._name)

        self.valueEdit.setPlaceholderText(self.tr("Value"))
        self.valueEdit.setText(self._value)

        self.removeButton.setFixedSize(24, 24)
        self.removeButton.setIconSize(QSize(10, 10))
        sizePolicy = self.removeButton.sizePolicy()
        sizePolicy.setRetainSizeWhenHidden(True)
        self.removeButton.setSizePolicy(sizePolicy)
        self.removeButton.setVisible(bool(self._name or self._value))

    def _initLayout(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.nameEdit, 2)  # narrow name column, wide value column
        layout.addWidget(self.valueEdit, 3)
        layout.addWidget(self.removeButton)

    # the text is filled in _initWidget before connecting signals, so bulk filling and pasting won't cascade-trigger
    def _bind(self) -> None:
        self.nameEdit.textChanged.connect(self._onTextChanged)
        self.valueEdit.textChanged.connect(self._onTextChanged)
        self.removeButton.clicked.connect(lambda: self._onRemoved(self))

    def header(self) -> tuple[str, str]:
        return self.nameEdit.text(), self.valueEdit.text()

    def setDuplicate(self, isDuplicate: bool) -> None:
        self.nameEdit.setError(isDuplicate)

    def _onTextChanged(self) -> None:
        # once non-empty, reveal the delete button and never retract it - after clearing content this row must still be deletable
        if any(text.strip() for text in self.header()):
            self.removeButton.show()
        self._onEdited(self)


class HeadersTextEdit(AutoSizingEdit):

    def insertFromMimeData(self, source) -> None:
        rows = parseHeaders(source.text())
        if not rows:
            super().insertFromMimeData(source)
            return
        self.insertPlainText(toHeadersText(rows))


class HeadersEditor(QWidget):

    def __init__(self, parent=None, *, defaults: dict[str, str]):
        super().__init__(parent)
        self._defaults = dict(defaults)
        self._isTextMode = False

        self.toolbar = QWidget(self)
        self.helpButton = TransparentToolButton(FluentIcon.QUESTION, self.toolbar)
        self.modeButton = TransparentToolButton(FluentIcon.ALIGNMENT, self.toolbar)
        self.resetButton = TransparentToolButton(FluentIcon.SYNC, self.toolbar)
        self.table = QWidget(self)
        self.textEdit = HeadersTextEdit(self, minimumVisibleLines=4, maximumVisibleLines=12)

        self.vBoxLayout = QVBoxLayout(self)
        self.tableLayout = QVBoxLayout(self.table)
        self.toolbarLayout = QHBoxLayout(self.toolbar)

        self._initWidget()
        self._initLayout()
        self._bind()

    def _initWidget(self) -> None:
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.textEdit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.textEdit.hide()
        self.textEdit.setPlaceholderText(
            self.tr("One Name: Value pair per line, or paste a cURL command"))
        self.helpButton.setToolTip(self.tr("Help"))
        self.modeButton.setToolTip(self.tr("Switch to Text View"))
        self.resetButton.setToolTip(self.tr("Restore Default Request Headers"))
        for button in (self.helpButton, self.modeButton, self.resetButton):
            button.installEventFilter(ToolTipFilter(button))

    def _initLayout(self) -> None:
        self.toolbarLayout.setContentsMargins(0, 0, 0, 0)
        self.toolbarLayout.setSpacing(4)
        self.toolbarLayout.addWidget(self.helpButton)
        self.toolbarLayout.addWidget(self.modeButton)
        self.toolbarLayout.addWidget(self.resetButton)

        self.tableLayout.setContentsMargins(0, 0, 0, 0)
        self.tableLayout.setSpacing(4)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.addWidget(self.table)
        self.vBoxLayout.addWidget(self.textEdit)

    def _bind(self) -> None:
        self.helpButton.clicked.connect(self._onHelpClicked)
        self.modeButton.clicked.connect(self._onModeToggled)
        self.resetButton.clicked.connect(self.reset)

    def headers(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for name, value in self._currentRows():
            key = name.strip().lower()
            value = value.strip()
            if key and value:
                result[key] = value
        return result

    def setHeaders(self, headers: dict[str, str]) -> None:
        self._setRows(list(headers.items()))

    def reset(self) -> None:
        self.setHeaders(self._defaults)

    # the row order has only one owner, tableLayout; no separate list is kept
    def _rows(self) -> list[HeaderRow]:
        return [self.tableLayout.itemAt(i).widget()
                for i in range(self.tableLayout.count())]

    def _lastRow(self) -> HeaderRow:
        return self.tableLayout.itemAt(self.tableLayout.count() - 1).widget()

    def _currentRows(self) -> list[tuple[str, str]]:
        if self._isTextMode:
            return toHeaderRows(self.textEdit.toPlainText())
        return [row.header() for row in self._rows() if any(row.header())]

    def _setRows(self, rows: list[tuple[str, str]]) -> None:
        if self._isTextMode:
            self.textEdit.setPlainText(toHeadersText(rows))
            return
        self._clearRows()
        for name, value in rows:
            self._addRow(name, value)
        self._addRow()
        self._refreshDuplicates()

    def _onModeToggled(self) -> None:
        rows = self._currentRows()
        self._isTextMode = not self._isTextMode
        self.table.setVisible(not self._isTextMode)
        self.textEdit.setVisible(self._isTextMode)
        self.modeButton.setToolTip(
            self.tr("Switch to Table View") if self._isTextMode else self.tr("Switch to Text View"))
        self._setRows(rows)

    def _onHelpClicked(self) -> None:
        TeachingTip.create(
            self.helpButton,
            self.tr("Help"),
            self.tr(
                "Paste to recognize cURL or name: value (one per line)\n"
                "Multiple cURL entries; only the first is taken\n"
                "\n"
                "When spoof identity is on, User-Agent and sec-ch-ua have no effect,\n"
                "Set to no-spoof to send as-is"
            ),
            tailPosition=TeachingTipTailPosition.BOTTOM,
            isClosable=True,
            duration=-1,
            parent=self,
        )

    def _onPaste(self, edit: HeaderCellEdit, text: str) -> bool:
        # newlines are illegal in both header name and value, so a paste containing a newline is never intended to "fill this cell"
        if "\n" not in text and "\r" not in text:
            if not edit.isName or edit.text():
                return False
        rows = parseHeaders(text)
        if not rows:
            return False
        index = self.tableLayout.indexOf(edit.parentWidget())
        for offset, (name, value) in enumerate(rows):
            self._addRow(name, value, index + offset)
        self._refreshDuplicates()
        return True

    def _addRow(self, name: str = "", value: str = "", index: int | None = None) -> None:
        row = HeaderRow(self.table, name=name, value=value, onPaste=self._onPaste,
                        onEdited=self._onRowEdited, onRemoved=self._removeRow)
        self.tableLayout.insertWidget(
            self.tableLayout.count() if index is None else index, row)

    def _onRowEdited(self, row: HeaderRow) -> None:
        if row is self._lastRow() and any(text.strip() for text in row.header()):
            self._addRow()
        self._refreshDuplicates()

    def _removeRow(self, row: HeaderRow) -> None:
        if row is self._lastRow():
            return
        # setParent(None) makes it leave the layout immediately; deleteLater only takes effect at the event loop
        row.setParent(None)
        row.deleteLater()
        self._refreshDuplicates()

    def _clearRows(self) -> None:
        for row in self._rows():
            row.setParent(None)
            row.deleteLater()

    def _refreshDuplicates(self) -> None:
        seen: set[str] = set()
        for row in self._rows():
            name = row.header()[0].strip().lower()
            row.setDuplicate(name in seen)
            if name:
                seen.add(name)
