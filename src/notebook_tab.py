from textual.app import ComposeResult
from textual.widgets import Button, Rule, Tabs
from textual.containers import HorizontalGroup, VerticalScroll
from textual.events import Key, DescendantFocus
from textual.widget import Widget
from notebook import Notebook

import os.path
import json
from time import time

from markdown_cell import MarkdownCell, FocusMarkdown
from code_cell import CodeCell, CodeArea
from utils import DOUBLE_CLICK_INTERVAL

class ButtonRow(HorizontalGroup):
    def compose(self) -> ComposeResult:
        yield Button("➕ Code", id="add-code-cell")
        yield Button("➕ Markdown", id="add-markdown-cell")
        yield Button("▶ Run All", id="run-all")
        yield Button("🔁 Restart", id="restart")

class NotebookTab(Widget):
    """A Textual app to manage stopwatches."""

    _last_click_time: float = 0.0
    BINDINGS = [
        ("a", "add_after", "Add cell after"),
        ("b", "add_before", "Add cell before"),
        ("dd", "delete", "Delete cell"),
    ]
    def __init__(self, path: str | None = None) -> None:
        super().__init__()
        self.last_focused = None
        self.path = path


    def on_mount(self):
        self.load_notebook()

    def load_notebook(self):
        if not os.path.exists(self.path):
            pass

        with open(self.path, "r") as notebook_file:
            content = json.load(notebook_file)
            for cell in content["cells"]:
                cell_kwargs = {
                    "source": "".join(cell["source"]),
                    "metadata": cell["metadata"],
                    "cell_id": cell["id"],
                }
                if cell["cell_type"] == "code":
                    # TODO: fix the execution count
                    cell_kwargs["exec_count"] = cell["execution_count"]
                    # TODO: fix the output parsing
                    cell_kwargs["output"] = ""
                    self.add_cell(CodeCell, "after", **cell_kwargs)
                elif cell["cell_type"] == "markdown":
                    self.add_cell(MarkdownCell, "after", **cell_kwargs)
                


    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield ButtonRow()
        yield Rule(line_style="double", id="header-rule")
        # https://textual.textualize.io/widgets/tabs/#__tabbed_1_2 TABS FOR EACH FILE
        yield VerticalScroll(id="cell-container")

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

    def add_cell(self, cell_type: str, position: str = "after", **cell_kwargs) -> None:
        """
        Position is after or before. 
        """
        kwargs = {position:self.last_focused}
        container = self.query_one("#cell-container", VerticalScroll)
        container.mount(cell_type(**cell_kwargs), **kwargs)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "add-code-cell":
                self.add_cell(CodeCell)
            case "add-markdown-cell":
                self.add_cell(MarkdownCell)

    def action_add_after(self):
        self.add_cell(CodeCell, "after")

    def action_add_before(self):
        self.add_cell(CodeCell, "before")

    def on_key(self, event: Key) -> None:
        match event.key:
            case "escape": 
                self.last_focused = None
            case "d":
                now = time()
                if now - self._last_click_time <=  DOUBLE_CLICK_INTERVAL:
                    if self.last_focused: 
                        self.last_focused.remove()
                        self.last_focused = None
                self._last_click_time = now
