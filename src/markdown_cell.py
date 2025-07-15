from textual.app import ComposeResult
from textual.widgets import Markdown, Static
from textual.events import Key, MouseDown
from textual.containers import HorizontalGroup
from typing import Any
from time import time
from utils import DOUBLE_CLICK_INTERVAL
from cell import Cell, SplitTextArea


class FocusMarkdown(Markdown):
    can_focus = True

class MarkdownCell(Cell):
    _last_click_time: float = 0.0
    cell_type = "markdown"

    def __init__(
        self,
        notebook,
        source: str = "",
        metadata: dict[str, Any] = {},
        cell_id: str | None = None,
    ) -> None:
        super().__init__(notebook, source, metadata, cell_id)
        self.collapse_btn.styles.width = 5

    def compose(self) -> ComposeResult:
        with HorizontalGroup():

            yield self.collapse_btn
            with self.switcher:
                self.collapsed_markdown = Static("Collapsed Markdown...", id="collapsed-display")
                self.input_text = SplitTextArea.code_editor(self.source, id="text", language="markdown", show_line_numbers=False)
                self.markdown = FocusMarkdown(self.source, id="markdown")
                yield self.collapsed_display
                yield self.input_text
                yield self.markdown

    def on_mouse_down(self, event: MouseDown) -> None:
        now = time()
        if event.ctrl:
            if not self.merge_select:
                self.notebook._merge_list.append(self)
            else:
                self.notebook._merge_list.remove(self)

            self.merge_select = not self.merge_select
        elif now - self._last_click_time <= DOUBLE_CLICK_INTERVAL:
            self.on_double_click(event)
        self._last_click_time = now

    def on_double_click(self, event: MouseDown) -> None:
        if self.switcher.current == "markdown":
            self.switcher.current = "text"

    def action_collapse(self) -> None:
        self.collapse_btn.collapsed = not self.collapse_btn.collapsed

    def escape(self, event: Key) -> None:
        self.render_markdown()
        self.focus()
        event.stop()

    def render_markdown(self) -> None:
        self.source = self.input_text.text
        # if not self.source:
        #     self.markdown.update(PLACEHOLDER)
        # else:
        self.markdown.update(self.source)
        self.switcher.current = "markdown"

    @staticmethod
    def from_nb(nb: dict[str, Any], notebook) -> "MarkdownCell":
        assert nb
        for key in ["cell_type", "metadata", "source"]:
            assert key in nb
        assert nb["cell_type"] == "markdown"

        source = nb["source"]
        if isinstance(source, list):
            source = "".join(source)

        return MarkdownCell(
            notebook=notebook,
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
            "source": self.input_text.text,
            "id": self._cell_id,
        }

    def create_cell(self, source) -> "MarkdownCell":
        return MarkdownCell(self.notebook, source)

    def clone(self, connect: bool = True) -> "MarkdownCell":
        clone = MarkdownCell(
            notebook=self.notebook,
            source = self.input_text.text,
            metadata = self._metadata,
            cell_id = self._cell_id,
        )
        if connect:
            clone.next = self.next
            clone.prev = self.prev
        return clone

    async def open(self):
        self.switcher.current = "text"
        self.call_after_refresh(self.input_text.focus)