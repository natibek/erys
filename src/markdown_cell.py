from textual.app import ComposeResult
from textual.widgets import Markdown, TextArea, ContentSwitcher
from textual.events import Key, MouseDown
from textual.containers import HorizontalGroup, VerticalScroll
from typing import Any
from time import time
from utils import get_cell_id, DOUBLE_CLICK_INTERVAL
import pyperclip

PLACEHOLDER = "*Empty markdown cell, double-click or press enter to edit.*"


class CopyTextAreaMarkdown(TextArea):
    def on_key(self, event: Key):
        if event.key == "ctrl+c":
            pyperclip.copy(self.selected_text)


class FocusMarkdown(Markdown):
    can_focus = True
    # TODO: FIX PLACEFOLDER

    def _on_focus(self):
        self.styles.border = "solid", "lightblue"

    def _on_blur(self):
        self.styles.border = None


class MarkdownCell(HorizontalGroup):
    _last_click_time: float = 0.0
    next = None
    prev = None

    def __init__(
        self,
        source: str = "",
        metadata: dict[str, Any] = {},
        cell_id: str | None = None,
    ) -> None:
        super().__init__()
        self.source = source
        self._metadata = metadata
        self._cell_id = cell_id or get_cell_id()

    def compose(self) -> ComposeResult:
        self.switcher = ContentSwitcher(initial="markdown", id="text-cell")
        with self.switcher:
            self.text_area = CopyTextAreaMarkdown(self.source, id="raw-text")
            self.markdown = FocusMarkdown(self.source, id="markdown")
            yield self.text_area
            yield self.markdown

    def on_key(self, event: Key) -> None:
        if self.switcher.current == "raw-text":
            match event.key:
                case "ctrl+r" | "escape":
                    event.stop()
                    self.switcher.current = "markdown"

                    self.source = self.text_area.text
                    self.markdown.update(self.source)
                    self.markdown.focus()

        elif self.switcher.current == "markdown":
            match event.key:
                case "enter":
                    self.switcher.current = "raw-text"

    def on_mouse_down(self, event: MouseDown) -> None:
        now = time()
        if now - self._last_click_time <= DOUBLE_CLICK_INTERVAL:
            self.on_double_click(event)
        self._last_click_time = now

    def on_double_click(self, event: MouseDown) -> None:
        if self.switcher.current == "markdown":
            self.switcher.current = "raw-text"

    def focus_widget(self) -> None:
        if cur := self.switcher.current:
            self.query_one(f"#{cur}").focus()
        # else:
        #     self.call_after_refresh(self.query_one(f"#markdown").focus)

    @staticmethod
    def from_nb(nb: dict[str, Any]) -> "MarkdownCell":
        assert nb
        for key in ["cell_type", "metadata", "source"]:
            assert key in nb
        assert nb["cell_type"] == "markdown"

        source = nb["source"]
        if isinstance(source, list):
            source = "".join(source)

        return MarkdownCell(
            source=source,
            metadata=nb["metadata"],
            cell_id=nb.get("id"),
        )

    def to_nb(self) -> dict[str, Any]:
        """
        Format for Markdown cell
        {
            "cell_type" : "markdown",
            "metadata" : {},
            "source" : ["some *markdown*"],
        }
        """
        return {
            "cell_type": "markdown",
            "metadata": self._metadata,
            "source": self.text_area.text,
            "id": self._cell_id,
        }

    def clone(self) -> "MarkdownCell":
        clone = MarkdownCell(
            source = self.text_area.text,
            metadata = self._metadata,
            cell_id = self._cell_id,
        )
        clone.next = self.next
        clone.prev = self.prev
        return clone

    def show_markdown(self):
        self.switcher.current = "markdown"

    async def open(self):
        if self.switcher.current == "markdown":
            self.switcher.current = "raw-text"
        self.call_after_refresh(self.text_area.focus)
