from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.containers import HorizontalGroup, VerticalGroup
from textual.widgets import Static, TextArea, Label, Markdown, Log, RichLog, Collapsible
from typing import Any
from utils import generate_id
from textual.events import Key
from IPython.utils import io
from notebook_kernel import NotebookKernel

import re

class RunLabel(Label):
    can_focus = True

    def on_click(self) -> None:
        code_cell: CodeCell = self.parent.parent
        code_cell.run_cell()



class CodeArea(TextArea):
    offset_val: int = reactive(0)
    closing_map = {"{": "}", "(": ")", "[": "]", "'": "'", '"': '"'}

    def _on_blur(self) -> None:
        code_cell: CodeCell = self.parent.parent
        code_cell.focus()

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


class OutputCell(TextArea):
    read_only = True

    def _on_focus(self):
        self.styles.border = "solid", "gray"

    def _on_blur(self):
        self.styles.border = None


class CodeCell(HorizontalGroup):
    can_focus = True
    exec_count: int | None = reactive(None)
    BINDINGS = [
        ("r", "run_cell", "Run Cell"),
    ]
    def __init__(
        self,
        source: str = "",
        outputs: list[dict[str, Any]] = [],
        exec_count: int | None = None,
        metadata: dict[str, Any] = {},
        cell_id: str | None = None,
        notebook: "Notebook" | None = None
    ) -> None:
        super().__init__()

        self.source = source

        self.outputs:list[dict[str, Any]] = outputs
        self.exec_count = exec_count

        self.metadata = metadata
        self.cell_id = cell_id or generate_id()
        self.notebook = notebook

    def _on_focus(self):
        self.styles.border = "solid", "lightblue"

    def _on_blur(self):
        self.styles.border = None

    def on_mount(self):
        self.call_after_refresh(lambda : self.update_outputs(self.outputs)) 

    def watch_exec_count(self, new: int | None) -> None:
        self.call_after_refresh(lambda : self.query_one("#exec-count", Static).update(f"[{new or ' '}]"))

    async def update_outputs(self, outputs: list[dict[str, Any]]) -> None:
        with open("../output", "a") as f:
            f.write(f"\nchanged outputs {outputs}")
        output_widget = self.query_one("#outputs", VerticalGroup)
        await output_widget.remove_children()
        for output in outputs:
            match output["output_type"]:
                case "stream":
                    text = "".join(output["text"]) if isinstance(output["text"], list) else output["text"]
                    output_widget.mount(OutputCell(text=text))
                case "error":
                    text = "".join(output["traceback"])
                    # log = RichLog(highlight=True)
                    # log.write(text)
                    # output_widget.mount(log)#
                    output_widget.mount(OutputCell(text=text))
                case "execute_result":
                    text = "".join(output["data"]["text/plain"]) if isinstance(output["data"]["text/plain"], list) else output["data"]["text/plain"]
                    output_widget.mount(OutputCell(text=text))
        self.refresh()

    def action_run_cell(self) -> None:
        self.call_after_refresh(self.run_cell)
    
    def run_cell(self):
        if not self.notebook.notebook_kernel:
            # TODO: Show warning message
            return

        kernel: NotebookKernel = self.notebook.notebook_kernel

        source = self.query_one("#code-editor", CodeArea).text
        self.source = source

        # capture the stdout and stderr
        outputs, execution_count = kernel.run_code(source)
        self.exec_count = execution_count
        self.outputs = outputs
        self.call_next(lambda: self.update_outputs(outputs))

    def compose(self) -> ComposeResult:
        with VerticalGroup(id="code-sidebar"):
            yield RunLabel("▶", id="run-button")
            yield Static(f"[{self.exec_count or ' '}]", id="exec-count")
        with VerticalGroup():
            yield CodeArea.code_editor(self.source, language="python", id="code-editor")
            yield VerticalGroup(id="outputs")