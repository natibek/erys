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
    # TODO: FIX PLACEFOLDER

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
        self._metadata = metadata
        self._cell_id = cell_id or generate_id()

    @staticmethod
    def from_nb(nb: dict[str, Any]) -> "MarkdownCell":
        assert nb
        for key in ["cell_type", "id", "metadata", "source"]:
            assert key in nb
        assert nb["cell_type"] == "markdown"

        source = nb["source"]
        if isinstance(source, list): source = "".join(source)

        return MarkdownCell(
            source=source,
            metadata=nb["metadata"],
            cell_id=nb["id"],
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
        }

    def compose(self) -> ComposeResult:
        self.switcher = ContentSwitcher(initial="markdown", id="text-cell")
        with self.switcher:
            self.text_area = TextArea(self.source, id="raw-text")
            self.markdown = FocusMarkdown(self.source, id="markdown")
            yield self.text_area
            yield self.markdown

    def show_markdown(self):
        self.switcher.current = "markdown"

    async def open(self):
        if self.switcher.current == "markdown":
            self.switcher.current = "raw-text"
        self.call_after_refresh(self.text_area.focus)

    def on_key(self, event: Key) -> None:
        if self.switcher.current == "raw-text" and event.key in {"ctrl+r", "escape"}:
            event.stop()
            self.switcher.current = "markdown"

            self.source = self.text_area.text
            self.markdown.update(self.source)
            self.markdown.focus()
        elif event.key == "enter" and self.switcher.current == "markdown":
            self.switcher.current = "raw-text"

    def on_mouse_down(self, event: MouseDown) -> None:
        now = time()
        if now - self._last_click_time <= DOUBLE_CLICK_INTERVAL:
            self.on_double_click(event)
        self._last_click_time = now

    def on_double_click(self, event: MouseDown) -> None:
        if self.switcher.current == "markdown":
            self.switcher.current = "raw-text"
