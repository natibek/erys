from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Button, DirectoryTree, Collapsible, Static, Markdown
from textual.widget import Widget
from textual.containers import HorizontalGroup, VerticalScroll, Container, Vertical
from textual.events import Key, DescendantFocus
from notebook import Notebook

from time import time

from markdown_cell import MarkdownCell, FocusMarkdown
from code_cell import CodeCell, CodeArea
from utils import DOUBLE_CLICK_INTERVAL

class ButtonRow(HorizontalGroup):
    def compose(self) -> ComposeResult:
        yield Button("Code", id="add-code-cell")
        yield Button("Markdown", id="add-markdown-cell")
        yield Button("Run All", id="run-all")
        yield Button("Restart", id="restart")


class DirectorySideBar(Container):
    def compose(self) -> ComposeResult:
        # with Collapsible(id="tree-panel"):
            # yield DirectoryTree(".", id="file-tree")
        with Vertical(id="tree-sidebar"):
            with Collapsible(id="tree-panel"):
                yield DirectoryTree(".", id="file-tree")

class NotebookApp(App):
    """A Textual app to manage stopwatches."""

    _last_click_time: float = 0.0
    CSS_PATH = "styles.tcss"
    # BINDINGS = [
    #     ("d", "toggle_dark", "Toggle dark mode"),
    # ]
    def __init__(self) -> None:
        super().__init__()
        self.theme = "textual-dark"
        self.last_focused = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        # yield DirectoryTree(".")
        # yield DirectorySideBar()
        yield ButtonRow()
        yield VerticalScroll(id="cell-container")
        yield Footer()

    def on_descendant_focus(self, event: DescendantFocus) -> None:
        # Ignore buttons
        if isinstance(event.widget, CodeCell) or isinstance(event.widget, MarkdownCell):
            self.last_focused = event.widget
        elif isinstance(event.widget, CodeArea):
            self.last_focused = event.widget.parent
        elif isinstance(event.widget, FocusMarkdown):
            self.last_focused = event.widget.parent.parent
        elif not isinstance(event.widget, Button):
            self.last_focused = None

    def add_cell(self, cell_type: str, position: str = "after") -> None:
        """
        Position is after or before. 
        """
        kwargs = {position:self.last_focused}
        container = self.query_one("#cell-container", VerticalScroll)
        container.mount(cell_type(), **kwargs)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "add-code-cell":
                self.add_cell(CodeCell)
            case "add-markdown-cell":
                self.add_cell(MarkdownCell)

    def on_key(self, event: Key) -> None:
        match event.key:
            case "escape": 
                self.set_focus(None)
                self.last_focused= None
            case "a":
                self.add_cell(CodeCell, "after")
            case "b":
                self.add_cell(CodeCell, "before")
            case "d":
                now = time()
                if now - self._last_click_time <=  DOUBLE_CLICK_INTERVAL:
                    if self.last_focused: 
                        self.last_focused.remove()
                        self.last_focused = None
                self._last_click_time = now


if __name__ == "__main__":
    app = NotebookApp()
    app.run()