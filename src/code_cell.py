from textual.app import ComposeResult
from textual.reactive import reactive
from textual.containers import HorizontalGroup, VerticalGroup
from textual.widgets import Button, Static, TextArea, Label, Markdown
from typing import Any
from utils import generate_id
from textual.events import Key


class RunLabel(Label):
    can_focus = True

    def on_click(self) -> None:
        code_cell = self.parent.parent
        source = code_cell.query_one("#code-editor", CodeArea).text
        code_cell.source = source

        notebook = code_cell.parent.parent
        notebook.cur_exec_count += 1
        code_cell.exec_count = notebook.cur_exec_count
        # self.parent.parent.parent.parent.query_one("#output", Markdown).update(f"clicked {self.count} {str(self.parent.parent)} {source}")


class CodeArea(TextArea):
    offset_val: int = reactive(0)
    closing_map = {"{": "}", "(": ")", "[": "]", "'": "'", '"': '"'}

    def on_resize(self) -> None:
        # TODO: move the exec_count with resize
        pass

    def on_key(self, event: Key) -> None:
        if event.character in self.closing_map:
            self.insert(f"{event.character}{self.closing_map[event.character]}")
            self.move_cursor_relative(columns=-1)
            event.prevent_default()
            return

        match event.key:
            case "escape":
                self.parent.focus()
                event.stop()
            # case "enter":
            #     cur_height = self.styles.height.cells
            #     if cur_height + 1 > MIN_HEIGHT:
            #         self.styles.height = cur_height + 1
            #         exec_count = self.parent.query_one("#exec-count", Static)
            #         self.offset_val += 1
            #         exec_count.styles.margin = (self.offset_val, 0, 0, 1)
            # case "backspace":
            #     if self.cursor_at_start_of_line:
            #         cur_height = self.styles.height.cells
            #         if cur_height - 1 > MIN_HEIGHT:
            #             self.styles.height = cur_height - 1
            #             exec_count = self.parent.query_one("#exec-count", Static)
            #             self.offset_val -= 1
            #             exec_count.styles.margin = (self.offset_val, 0, 0, 1)
            #         else:
            #             self.styles.height = MIN_HEIGHT
            #             exec_count = self.parent.query_one("#exec-count", Static)
            #             self.offset_val = 0
            #             exec_count.styles.margin = (0, 0, 0, 1)


class OutputCell(TextArea):
    def on_mount(self) -> None:
        self.disabled = True


class CodeCell(HorizontalGroup):
    can_focus = True
    source: str = reactive("")
    output: str = reactive("")
    exec_count: int | None = reactive(None)

    def __init__(
        self,
        source: str = "",
        output: str = "",
        exec_count: int | None = None,
        metadata: dict[str, Any] = {},
        cell_id: str | None = None,
    ) -> None:
        super().__init__()

        self.source = source
        self.output = output
        self.exec_count = exec_count

        self.metadata = metadata
        self.cell_id = cell_id or generate_id()

    def _on_focus(self):
        self.styles.border = "solid", "lightblue"

    def _on_blur(self):
        self.styles.border = None

    def on_mount(self):
        self.exec_count = self.exec_count

    def watch_exec_count(self, old: int | None, new: int | None) -> None:
        if self.parent:
            self.query_one("#exec-count", Static).update(f"[{new or ' '}]")

    def compose(self) -> ComposeResult:
        with VerticalGroup(id="code-sidebar"):
            yield RunLabel("▶", id="run-button")
            yield Static(f"[{self.exec_count or ' '}]", id="exec-count")
        yield CodeArea.code_editor(self.source, language="python", id="code-editor")
