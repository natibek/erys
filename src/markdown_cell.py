from textual.app import ComposeResult
from textual.widgets import Markdown, TextArea, ContentSwitcher, Label, Static
from textual.events import Key, MouseDown
from textual.containers import HorizontalGroup
from typing import Any
from time import time
from utils import get_cell_id, DOUBLE_CLICK_INTERVAL, COLLAPSED_COLOR, EXPANDED_COLOR
from textual.reactive import var
import pyperclip

PLACEHOLDER = "*Empty markdown cell, double-click or press enter to edit.*"

class MarkdownCollapseLabel(Label):
    collapsed = var(False, init=False)

    def __init__(self, collapsed: bool = False, id: str = "") -> None:
        super().__init__("\n┃\n┃", id=id)
        self.collapsed = collapsed
        self.prev_switcher = None

    def on_click(self) -> None:
        self.collapsed = not self.collapsed

    def watch_collapsed(self, collapsed) -> None:
        markdown_cell: MarkdownCell = self.parent

        if collapsed:
            placeholder = self.get_placeholder(markdown_cell.text_area.text)
            markdown_cell.collapsed_markdown.update(f"{placeholder}...")

            self.prev_switcher = markdown_cell.switcher.current
            markdown_cell.switcher.current = "collapsed-markdown"

            self.styles.color = COLLAPSED_COLOR
            self.update("┃")
        else:
            markdown_cell.switcher.current = self.prev_switcher or "markdown"
            self.styles.color = EXPANDED_COLOR
            self.update("\n┃\n┃")

    def get_placeholder(self, text: str) -> str:
        split = text.splitlines()
        if len(split) == 0:
            return ""

        for line in split:
            if line != "":
                return line

class CopyTextAreaMarkdown(TextArea):

    def on_key(self, event: Key) -> None:
        match event.key:
            case "ctrl+c":
                pyperclip.copy(self.selected_text)
            case "escape" | "ctrl+r":
                markdown_cell: MarkdownCell = self.parent.parent
                markdown_cell.render_markdown()
                markdown_cell.focus()
                event.stop()


class FocusMarkdown(Markdown):
    can_focus = True

class MarkdownCell(HorizontalGroup):
    can_focus = True
    _last_click_time: float = 0.0
    next = None
    prev = None

    BINDINGS = [
        ("c", "collapse", "Collapse Cell"),
    ]

    def __init__(
        self,
        idx: int =  0,
        source: str = "",
        metadata: dict[str, Any] = {},
        cell_id: str | None = None,
    ) -> None:
        super().__init__()
        self.idx = idx
        self.source = source
        self._metadata = metadata
        self._cell_id = cell_id or get_cell_id()
        self._collapsed = metadata.get("collapsed", False)

    def compose(self) -> ComposeResult:
        self.collapse_btn = MarkdownCollapseLabel(
            collapsed=self._collapsed, id="markdown-collapse-button"
        ).with_tooltip("Collapse")

        yield self.collapse_btn

        self.switcher = ContentSwitcher(initial="markdown", id="raw-text")
        with self.switcher:
            self.collapsed_markdown = Static("Collapsed Markdown...", id="collapsed-markdown")
            self.text_area = CopyTextAreaMarkdown.code_editor(self.source, id="raw-text", language="markdown", show_line_numbers=False)
            self.markdown = FocusMarkdown(self.source, id="markdown")
            yield self.collapsed_markdown
            yield self.text_area
            yield self.markdown

    def _on_focus(self):
        self.styles.border = "solid", "lightblue"
        self.border_subtitle = "Markdown"

    def _on_blur(self):
        self.styles.border = None
        # self.render_markdown()

    async def on_key(self, event: Key) -> None:
        match event.key:
            case "enter":
                await self.open()

    def on_mouse_down(self, event: MouseDown) -> None:
        now = time()
        if now - self._last_click_time <= DOUBLE_CLICK_INTERVAL:
            self.on_double_click(event)
        self._last_click_time = now

    def on_double_click(self, event: MouseDown) -> None:
        if self.switcher.current == "markdown":
            self.switcher.current = "raw-text"

    def action_collapse(self) -> None:
        self.collapse_btn.collapsed = not self.collapse_btn.collapsed

    def render_markdown(self) -> None:
        self.source = self.text_area.text
        # if not self.source:
        #     self.markdown.update(PLACEHOLDER)
        # else:
        self.markdown.update(self.source)
        self.switcher.current = "markdown"

    @staticmethod
    def from_nb(nb: dict[str, Any], idx: int) -> "MarkdownCell":
        assert nb
        for key in ["cell_type", "metadata", "source"]:
            assert key in nb
        assert nb["cell_type"] == "markdown"

        source = nb["source"]
        if isinstance(source, list):
            source = "".join(source)

        return MarkdownCell(
            idx=idx,
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

    def clone(self, connect: bool = True) -> "MarkdownCell":
        clone = MarkdownCell(
            idx=self.idx,
            source = self.text_area.text,
            metadata = self._metadata,
            cell_id = self._cell_id,
        )
        if connect:
            clone.next = self.next
            clone.prev = self.prev
        return clone

    def show_markdown(self):
        self.switcher.current = "markdown"

    async def open(self):
        self.switcher.current = "raw-text"
        self.call_after_refresh(self.text_area.focus)
