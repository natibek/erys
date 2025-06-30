from textual.app import ComposeResult
from textual.reactive import reactive
from textual.containers import HorizontalGroup, VerticalGroup
from widgets import ExpandingTextArea, MIN_HEIGHT
from textual.widgets import Button, Static, TextArea
from typing import Any
from utils import generate_id
from textual.events import Key

class CodeArea(TextArea):
    offset_val: int = reactive(1)
    def on_key(self, event: Key) -> None:
        match event.key:
            case "escape":
                pass
            case "enter":
                cur_height = self.styles.height.cells
                if cur_height + 1 > MIN_HEIGHT:
                    self.styles.height = cur_height + 1
                    exec_count = self.parent.query_one("#exec-count", Static)
                    self.offset_val += 1
                    exec_count.styles.margin = (self.offset_val, 0, 0, 1)
            case "backspace":
                if self.cursor_at_start_of_line:
                    cur_height = self.styles.height.cells
                    if cur_height - 1 > MIN_HEIGHT:
                        self.styles.height = cur_height - 1
                        exec_count = self.parent.query_one("#exec-count", Static)
                        self.offset_val -= 1
                        exec_count.styles.margin = (self.offset_val, 0, 0, 1)
                    else:
                        self.styles.height = MIN_HEIGHT
                        exec_count = self.parent.query_one("#exec-count", Static)
                        self.offset_val = 1
                        exec_count.styles.margin = (1, 0, 0, 1)

class OutputCell(ExpandingTextArea):
    def on_mount(self) -> None:
        self.disabled = True

class CodeCell(HorizontalGroup):
    def __init__(
        self, 
        source: str = "",
        output: str =  "",
        metadata: dict[str, Any] = {},
        exec_count: int | None = None,
        cell_id: str | None = None,
    ) -> None:
        super().__init__()
        self.source = source
        self.output = output
        self.metadata = metadata
        self.cell_id = cell_id or generate_id()
        self.exec_count = exec_count

    def compose(self) -> ComposeResult:
        with HorizontalGroup():
            with VerticalGroup(id="code-sidebar"):
                yield Button(">", id="run-button")
                yield Static(f"[{self.exec_count or ""}]", id="exec-count")
            yield CodeArea.code_editor(self.source, language="python", id="code-editor")