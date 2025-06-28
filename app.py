from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Collapsible, Markdown, DirectoryTree, TextArea, ContentSwitcher
from textual.containers import HorizontalGroup, VerticalScroll
from textual.events import Key
from notebook import Notebook

from markdown_cell import MarkdownCell
from code_cell import CodeCell

class NotebookApp(App):
    """A Textual app to manage stopwatches."""

    CSS_PATH = "styles.tcss"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
    ]
    def __init__(self) -> None:
        super().__init__()
        self.theme = "nord"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        # with Collapsible(collapsed_symbol=">>>", expanded_symbol="v"):
        #     yield DirectoryTree(".")

        yield MarkdownCell()
        yield MarkdownCell()
        yield CodeCell()
                
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "nord" if self.theme == "solarized-light" else "solarized-light"
        )

    def on_mount(self) -> None:
        self.set_focus(None)

    def on_key(self, event: Key) -> None:
        match event.key:
            case "escape": self.set_focus(None)

if __name__ == "__main__":
    app = NotebookApp()
    app.run()