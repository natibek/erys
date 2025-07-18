from textual.app import ComposeResult
from textual.widgets import Markdown, Static, ContentSwitcher
from textual.events import Key, MouseDown
from textual.containers import HorizontalGroup

from typing import Any

from .cell import Cell, SplitTextArea


class MarkdownCell(Cell):
    """Widget to contain markdown cells in a notebook"""

    cell_type = "markdown"

    def __init__(
        self,
        notebook,
        source: str = "",
        metadata: dict[str, Any] = {},
        cell_id: str | None = None,
    ) -> None:
        super().__init__(notebook, source, "markdown", metadata, cell_id)
        self.collapse_btn.styles.width = 5
        self.switcher = ContentSwitcher(id="collapse-content", initial="markdown")
        self.collapsed_markdown = Static(
            "Collapsed Markdown...", id="collapsed-display"
        )
        self.input_text = SplitTextArea.code_editor(
            self.source, id="text", language="markdown", show_line_numbers=False
        )
        self.markdown = Markdown(self.source, id="markdown")

    def compose(self) -> ComposeResult:
        """Compose with:
        - VerticalGroup
            - HorziontalGroup
                - CollapseLabela (id=collapse-button)
                - ContentSwitcher (id=collapse-content)
                    - SplitTextArea (id=text)
                    - FocusMarkdown (id=markdown)
                    - Static (id=collapsed-display)
        """
        with HorizontalGroup():
            yield self.collapse_btn
            with self.switcher:
                yield self.collapsed_display
                yield self.input_text
                yield self.markdown

    def on_double_click(self, event: MouseDown) -> None:
        """Double click event handler that switches content to the input text from markdown.

        Args:
            event: MouseDown event.
        """
        if self.switcher.current == "markdown":
            self.switcher.current = "text"
            self.input_text.focus()

    def action_collapse(self) -> None:
        """Toggle the collapsed."""
        self.collapse_btn.collapsed = not self.collapse_btn.collapsed

    def escape(self, event: Key) -> None:
        """Event handler to be called when the escape key is pressed."""
        self.render_markdown()
        self.focus()
        event.stop()

    def render_markdown(self) -> None:
        """Changes content switcher's currently displayed widget to the markdown and
        updates the content input_text."""
        self.source = self.input_text.text
        # if not self.source:
        #     self.markdown.update(PLACEHOLDER)
        # else:
        self.markdown.update(self.source)
        self.switcher.current = "markdown"

    @staticmethod
    def from_nb(nb: dict[str, Any], notebook) -> "MarkdownCell":
        """Static method to generate a `MarkdownCell` from a json/dict that represent a
        makrdown cell.

        Args:
            nb: the notebook json/dict format of the markdown cell.
            notebook: the `Notebook` object the markdown cell belongs too.

        Returns: `MarkdownCell` from notebook format.

        Raises:
            AssertionError: if no notebook or bad notebook representation.
        """
        # need to have a notebook object and a notebook format
        assert nb
        # needs to be a valid notebook representation
        for key in ["cell_type", "metadata", "source"]:
            assert key in nb
        assert nb["cell_type"] == "markdown"

        source = nb["source"]
        if isinstance(source, list):
            # join the strings if the input was a multiline string
            source = "".join(source)

        return MarkdownCell(
            notebook=notebook,
            source=source,
            metadata=nb["metadata"],
            cell_id=nb.get("id"),
        )

    def to_nb(self) -> dict[str, Any]:
        """Serialize the `MarkdownCell` to notebook format. Format for markdown cell:
            {
                "cell_type" : "markdown",
                "metadata" : {},
                "source" : ["some *markdown*"],
            }

        Returns: serialized markdown cell representation.
        """
        return {
            "cell_type": "markdown",
            "metadata": self._metadata,
            "source": self.input_text.text,
            "id": self._cell_id,
        }

    def create_cell(self, source) -> "MarkdownCell":
        """Returns a `MarkdownCell` with a source. Used for splitting code cell."""
        return MarkdownCell(self.notebook, source)

    def clone(self, connect: bool = True) -> "MarkdownCell":
        """Clone a markdown cell. Used for cut/paste.

        Args:
            connect: whether to keep the pointers to the next and previous cells.

        Returns: cloned markdown cell.
        """
        clone = MarkdownCell(
            notebook=self.notebook,
            source=self.input_text.text,
            metadata=self._metadata,
            cell_id=self._cell_id,
        )
        if connect:
            clone.next = self.next
            clone.prev = self.prev
        return clone

    async def open(self):
        """Defines what it means to open a markdown cell. Focus on the input_text widget."""
        self.switcher.current = "text"
        self.call_after_refresh(self.input_text.focus)
