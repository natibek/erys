from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Button, DirectoryTree, Collapsible
from textual.widget import Widget
from textual.containers import HorizontalGroup, Vertical, Container
from textual.events import Key
from notebook import Notebook

from markdown_cell import MarkdownCell
from code_cell import CodeCell

class ButtonRow(HorizontalGroup):
    def compose(self) -> ComposeResult:
        yield Button("Code")
        yield Button("Markdown")
        yield Button("Run All")
        yield Button("Restart")

class DirectorySideBar(Container):
    def compose(self) -> ComposeResult:
        # with Collapsible(id="tree-panel"):
            # yield DirectoryTree(".", id="file-tree")
        with Vertical(id="tree-sidebar"):
            with Collapsible(id="tree-panel"):
                yield DirectoryTree(".", id="file-tree")

class NotebookApp(App):
    """A Textual app to manage stopwatches."""

    CSS_PATH = "styles.tcss"
    # BINDINGS = [
    #     ("d", "toggle_dark", "Toggle dark mode"),
    # ]
    def __init__(self) -> None:
        super().__init__()
        self.theme = "textual-dark"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        # yield DirectoryTree(".")
        # yield DirectorySideBar()
        yield ButtonRow()

        yield MarkdownCell()
        yield CodeCell()
            
        yield Footer()

    def on_mount(self) -> None:
        self.set_focus(None)

    def on_key(self, event: Key) -> None:
        pass
        # match event.key:
        #     case "escape": self.set_focus(None)

if __name__ == "__main__":
    app = NotebookApp()
    app.run()