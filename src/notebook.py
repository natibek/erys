from textual.reactive import reactive
from textual.app import ComposeResult
from textual.widgets import Button, Rule, Label
from textual.containers import HorizontalGroup, VerticalScroll, Container
from textual.events import Key, DescendantFocus

import os.path
import json

from markdown_cell import MarkdownCell, FocusMarkdown
from code_cell import CodeCell, CodeArea


class ButtonRow(HorizontalGroup):
    def compose(self) -> ComposeResult:
        yield Button("➕ Code", id="add-code-cell")
        yield Button("➕ Markdown", id="add-markdown-cell")
        yield Button("▶ Run All", id="run-all")
        yield Button("🔁 Restart", id="restart")


class Notebook(Container):
    """A Textual app to manage stopwatches."""
    valid_notebook = reactive(True)

    _last_click_time: float = 0.0
    last_focused = None
    cur_exec_count = 0
    BINDINGS = [
        ("a", "add_after", "Add cell after"),
        ("b", "add_before", "Add cell before"),
        ("ctrl+d", "delete", "Delete cell"),
    ]

    def __init__(self, path: str, id: str) -> None:
        super().__init__(id=id)

        self.path = path

    def watch_valid_notebook(self, is_valid: bool) -> None:
        for node in [ButtonRow, Rule, VerticalScroll]:
            self.query_one(node).display = is_valid

        self.query_one(Label).display = not is_valid

    def on_mount(self):
        self.load_notebook()

    def load_notebook(self):
        if self.path == "new_empty_termimal_notebook":
            return

        if not os.path.exists(self.path):
            self.valid_notebook = False
            return

        if os.path.splitext(self.path)[1] != ".ipynb":
            self.valid_notebook = False
            return
        
        with open(self.path, "r") as notebook_file:
            content = json.load(notebook_file)
            for cell in content["cells"]:
                cell_kwargs = {
                    "source": "".join(cell["source"]),
                    "metadata": cell["metadata"],
                    "cell_id": cell["id"],
                }
                if cell["cell_type"] == "code":
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
        yield VerticalScroll(id="cell-container")

        yield Label(
            f"{self.path} is not a valid notebook. "
            "File does not have a .ipynb extension."
        )

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
        kwargs = {position: self.last_focused}
        container = self.query_one("#cell-container", VerticalScroll)
        widget = cell_type(**cell_kwargs)
        container.mount(widget, **kwargs)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "add-code-cell":
                self.add_cell(CodeCell)
            case "add-markdown-cell":
                self.add_cell(MarkdownCell)

    def action_delete(self) -> None:
        if self.last_focused:
            self.last_focused.remove()
            self.last_focused = None

    def action_add_after(self) -> None:
        self.add_cell(CodeCell, "after")

    def action_add_before(self) -> None:
        self.add_cell(CodeCell, "before")

    def on_key(self, event: Key) -> None:
        match event.key:
            case "escape":
                self.last_focused = None

