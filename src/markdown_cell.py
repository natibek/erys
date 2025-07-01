from textual.app import ComposeResult
from textual.widgets import Markdown, TextArea, ContentSwitcher
from textual.events import Key, MouseDown
from textual.containers import HorizontalGroup
from typing import Any
from time import time
from utils import generate_id, DOUBLE_CLICK_INTERVAL

PLACEHOLDER = "*Empty markdown cell, double-click or press enter to edit.*"


class FocusMarkdown(Markdown):
    can_focus = True

    def on_mount(self) -> None:
        if self.size == 0:
            self.update(PLACEHOLDER)

    def on_key(self, event: Key) -> None:
        match event.key:
            case "escape":
                pass

    def _on_focus(self):
        self.styles.border = "solid", "lightblue"

    def _on_blur(self):
        self.styles.border = None


class MarkdownCell(HorizontalGroup):
    _last_click_time: float = 0.0

    def __init__(
        self,
        source: str = "",
        metadata: dict[str, Any] = {},
        cell_id: str | None = None,
    ) -> None:
        super().__init__()
        self.source = source
        self.metadata = metadata
        self.cell_id = cell_id or generate_id()

    def compose(self) -> ComposeResult:
        with ContentSwitcher(initial="markdown", id="text-cell"):
            yield TextArea(self.source, id="raw-text")
            yield FocusMarkdown(self.source, id="markdown")

    def on_key(self, event: Key) -> None:
        switcher = self.query_one("#text-cell", ContentSwitcher)
        if switcher.current == "raw-text" and event.key in {"ctrl+e", "escape"}:
            event.stop()
            switcher.current = "markdown"

            self.source = self.query_one("#raw-text", TextArea).text
            markdown = self.query_one("#markdown", Markdown)
            markdown.update(self.source)
            markdown.focus()
        elif event.key == "enter" and switcher.current == "markdown":
            switcher.current = "raw-text"

    def on_mouse_down(self, event: MouseDown) -> None:
        now = time()
        if now - self._last_click_time <= DOUBLE_CLICK_INTERVAL:
            self.on_double_click(event)
        self._last_click_time = now

    def on_double_click(self, event: MouseDown) -> None:
        switcher = self.query_one("#text-cell", ContentSwitcher)
        if switcher.current == "markdown":
            switcher.current = "raw-text"
