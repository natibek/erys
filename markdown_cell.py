from textual.app import ComposeResult
from textual.widgets import Markdown, TextArea, ContentSwitcher, Collapsible
from textual.events import Key
from widgets import ExpandingTextArea, FocusMarkdown
from typing import Any
from utils import generate_id
        

class MarkdownCell(Collapsible):
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
        with ContentSwitcher(initial="raw-text", id="text-cell"):
            yield ExpandingTextArea(self.source, id="raw-text")
            yield FocusMarkdown(self.source, id="markdown")

    def on_key(self, event: Key) -> None:
        switcher = self.query_one("#text-cell", ContentSwitcher)
        if event.key == "ctrl+e" and switcher.current == "raw-text":
            self.source= self.query_one("#raw-text", TextArea).text
            self.query_one("#markdown", Markdown).update(self.source)
            switcher.current = "markdown"
        elif event.key == "enter" and switcher.current == "markdown":
            switcher.current = "raw-text"