from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.containers import HorizontalGroup, VerticalGroup
from textual.widgets import Static, TextArea, Label, Markdown, Log, RichLog, Collapsible
from typing import Any
from utils import get_cell_id
from textual.events import Key
from notebook_kernel import NotebookKernel


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
        self.notebook = notebook

        self._metadata = metadata
        self._cell_id = cell_id or get_cell_id()

    @staticmethod
    def from_nb(nb: dict[str, Any], notebook = None) -> "CodeCell":
        assert nb
        for key in ["cell_type", "id", "execution_count", "metadata", "source", "outputs"]:
            assert key in nb
        assert nb["cell_type"] == "code"
        
        source = nb["source"]
        if isinstance(source, list): source = "".join(source)

        return CodeCell(
            source=source,
            outputs=nb["outputs"],
            exec_count=nb["execution_count"],
            metadata=nb["metadata"],
            cell_id=nb["id"],
            notebook=notebook
        )

    def to_nb(self):
        """
        Format for code cell
            {
            "cell_type" : "code",
            "execution_count": 1, # integer or null
            "metadata" : {
                "collapsed" : True, # whether the output of the cell is collapsed
                "autoscroll": False, # any of true, false or "auto"
            },
            "source" : ["some code"],
            "outputs": [{
                # list of output dicts (described below)
                "output_type": "stream",
                ...
            }],
            }
        """
        return {
            "cell_type": "code",
            "execution_count": self.exec_count,
            "id": self._cell_id,
            "metadata": self._metadata,
            "outputs": self.outputs,
            "source": self.source,
        }

    def _on_focus(self):
        self.styles.border = "solid", "lightblue"

    def _on_blur(self):
        self.styles.border = None

    def on_mount(self):
        self.call_after_refresh(lambda : self.update_outputs(self.outputs)) 

    def watch_exec_count(self, new: int | None) -> None:
        self.call_after_refresh(lambda : self.exec_count_display.update(f"[{new or ' '}]"))

    async def open(self):
        self.call_after_refresh(self.code_area.focus)

    async def update_outputs(self, outputs: list[dict[str, Any]]) -> None:
        self.outputs_group = self.query_one("#outputs", VerticalGroup)
        await self.outputs_group.remove_children()
        for output in outputs:
            match output["output_type"]:
                case "stream":
                    if isinstance(output["text"], list):
                        text = "".join(output["text"]) 
                    else:
                        text = output["text"]
                    self.outputs_group.mount(OutputCell(text=text))
                case "error":
                    text = "".join(output["traceback"])
                    # log = RichLog(highlight=True)
                    # log.write(text)
                    # self.outputs_group.mount(log)#
                    self.outputs_group.mount(OutputCell(text=text))
                case "execute_result":
                    if isinstance(output["data"]["text/plain"], list):
                        text = "".join(output["data"]["text/plain"])
                    else: 
                        text = output["data"]["text/plain"]
                    self.outputs_group.mount(OutputCell(text=text))
        self.refresh()

    def action_run_cell(self) -> None:
        self.call_after_refresh(self.run_cell)
    
    def run_cell(self):
        if not self.notebook.notebook_kernel:
            # TODO: Show warning message
            return

        kernel: NotebookKernel = self.notebook.notebook_kernel

        self.source = self.code_area.text
        # capture the stdout and stderr
        outputs, execution_count = kernel.run_code(self.source)
        self.exec_count = execution_count
        self.outputs = outputs
        self.call_next(lambda: self.update_outputs(outputs))

    def compose(self) -> ComposeResult:
        with VerticalGroup(id="code-sidebar"):
            yield RunLabel("▶", id="run-button")
            self.exec_count_display = Static(f"[{self.exec_count or ' '}]", id="exec-count")
            yield self.exec_count_display
        with VerticalGroup():
            self.code_area = CodeArea.code_editor(self.source, language="python", id="code-editor")
            self.outputs_group = VerticalGroup(id="outputs")

            yield self.code_area
            yield self.outputs_group