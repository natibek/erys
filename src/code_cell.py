from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import var
from textual.containers import HorizontalGroup, VerticalGroup
from textual.widgets import Static, TextArea, Label, ContentSwitcher
from typing import Any
from utils import get_cell_id
from textual.events import Key
from notebook_kernel import NotebookKernel

COLLAPSED_COLOR = "green"
EXPANDED_COLOR = "white"

class CodeCollapseLabel(Label):
    collapsed = var(False, init=False)

    def __init__(self, collapsed: bool = False, id: str = "") -> None:
        super().__init__("┃\n┃\n┃", id=id)
        self.collapsed = collapsed
    
    def on_click(self) -> None:
        self.collapsed = not self.collapsed

    def watch_collapsed(self, collapsed) -> None:
        code_cell: CodeCell = self.parent.parent.parent

        if collapsed:
            placeholder = self.get_placeholder(code_cell.code_area.text)
            code_cell.collapsed_code.update(f"{placeholder}...")
            code_cell.code_switcher.current = "collapsed-code"
            code_cell.exec_count_display.display = False
            self.styles.color = COLLAPSED_COLOR
            self.update("┃\n┃")
        else:
            code_cell.code_switcher.current = "code-editor"
            code_cell.exec_count_display.display = True
            self.styles.color = EXPANDED_COLOR
            self.update("┃\n┃\n┃")

    def get_placeholder(self, text: str) -> str:
        split = text.splitlines()
        if len(split) == 0:
            return ""
            
        for line in split:
            if line != "": return line


class OutputCollapseLabel(Label):
    collapsed = var(False, init=False)

    def __init__(self, collapsed: bool = False, id: str = "") -> None:
        super().__init__("\n┃", id=id)
        self.collapsed = collapsed
    
    def on_click(self) -> None:
        self.collapsed = not self.collapsed

    def watch_collapsed(self, collapsed: bool) -> None:
        code_cell: CodeCell = self.parent.parent

        if collapsed and len(code_cell.outputs) > 0:
            code_cell.output_switcher.current = "collapsed-output"
            self.styles.color = COLLAPSED_COLOR
        else:
            code_cell.output_switcher.current = "outputs"
            self.styles.color = EXPANDED_COLOR

class RunLabel(Label):
    def __init__(self, id: str = "") -> None:
        super().__init__("▶", id=id)

    def on_click(self) -> None:
        code_cell: CodeCell = self.parent.parent.parent.parent
        self.run_worker(code_cell.run_cell)


class CodeArea(TextArea):
    closing_map = {"{": "}", "(": ")", "[": "]", "'": "'", '"': '"'}

    def on_key(self, event: Key) -> None:
        if event.character in self.closing_map:
            self.insert(f"{event.character}{self.closing_map[event.character]}")
            self.move_cursor_relative(columns=-1)
            event.prevent_default()
            return

        match event.key:
            case "escape":
                code_cell: CodeCell = self.parent.parent.parent
                code_cell.focus()
                event.stop()

class OutputCell(TextArea):
    read_only = True

    def _on_focus(self):
        self.styles.border = "solid", "gray"

    def _on_blur(self):
        self.styles.border = None

class CodeCell(VerticalGroup):
    can_focus = True
    exec_count: int | None = var(None)

    BINDINGS = [
        ("r", "run_cell", "Run Cell"),
        ("c", "collapse", "Collapse Cell"),
    ]

    next = None
    prev = None

    def __init__(
        self,
        notebook,
        source: str = "",
        outputs: list[dict[str, Any]] = [],
        exec_count: int | None = None,
        metadata: dict[str, Any] = {},
        cell_id: str | None = None,
    ) -> None:
        super().__init__()
        self.notebook = notebook

        self.source = source

        self.outputs: list[dict[str, Any]] = outputs
        self.exec_count = exec_count

        self._metadata = metadata
        self._cell_id = cell_id or get_cell_id()
        self._collapsed = metadata.get("collapsed", False)

    def compose(self) -> ComposeResult:
        with HorizontalGroup():
            with HorizontalGroup(id="code-sidebar"):
                self.collapse_btn = CodeCollapseLabel(collapsed=self._collapsed, id="code-collapse-button").with_tooltip("Collapse Code")
                yield self.collapse_btn
                with VerticalGroup():
                    yield RunLabel(id="run-button").with_tooltip("Run")
                    self.exec_count_display = Static(
                        f"[{self.exec_count or ' '}]", id="exec-count"
                    )
                    yield self.exec_count_display
            self.code_area = CodeArea.code_editor(
                self.source, language="python", id="code-editor"
            )
            self.collapsed_code = Static("Collapsed Code...", id="collapsed-code")
            self.code_switcher = ContentSwitcher(id="collapse-code", initial="code-editor")
            with self.code_switcher:
                yield self.code_area
                yield self.collapsed_code

        with HorizontalGroup(id="output-section"):
            self.output_collapse_btn = OutputCollapseLabel(id="output-collapse-button").with_tooltip("Collapse Output")

            self.outputs_group = VerticalGroup(id="outputs")
            self.output_switcher = ContentSwitcher(id="collapse-outputs", initial="outputs")
            yield self.output_collapse_btn
            with self.output_switcher:
                yield self.outputs_group
                yield Static("Outputs are collapsed...", id="collapsed-output")

    def on_key(self, event: Key) -> None:
        match event.key:
            case "enter":
                self.call_after_refresh(self.code_area.focus)

    def _on_focus(self):
        self.styles.border = "solid", "lightblue"

    def _on_blur(self):
        self.styles.border = None

    def on_mount(self):
        self.output_collapse_btn.display = len(self.outputs) > 0
        self.call_after_refresh(self.update_outputs, self.outputs)

    def watch_exec_count(self, new: int | None) -> None:
        self.call_after_refresh(
            lambda: self.exec_count_display.update(f"[{new or ' '}]")
        )

    def action_run_cell(self) -> None:
        self.run_worker(self.run_cell)
    
    def action_collapse(self) -> None:
        if not self.collapse_btn.collapsed or not self.output_collapse_btn.collapsed:
            self.collapse_btn.collapsed = True
            self.output_collapse_btn.collapsed = True
        else:
            self.collapse_btn.collapsed = not self.collapse_btn.collapsed
            self.output_collapse_btn.collapsed = not self.output_collapse_btn.collapsed


    @staticmethod
    def from_nb(nb: dict[str, Any], notebook=None) -> "CodeCell":
        assert nb
        for key in ["cell_type", "execution_count", "metadata", "source", "outputs"]:
            assert key in nb
        assert nb["cell_type"] == "code"

        source = nb["source"]
        if isinstance(source, list):
            source = "".join(source)

        return CodeCell(
            source=source,
            outputs=nb["outputs"],
            exec_count=nb["execution_count"],
            metadata=nb["metadata"],
            cell_id=nb.get("id", None),
            notebook=notebook,
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

    def focus_widget(self):
        self.focus()

    async def open(self):
        self.call_after_refresh(self.code_area.focus)

    async def update_outputs(self, outputs: list[dict[str, Any]]) -> None:
        try:
            self.outputs_group = self.query_one("#outputs", VerticalGroup)
        except:
            return

        self.output_collapse_btn.display = len(outputs) > 0
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
                    self.outputs_group.mount(OutputCell(text=text))
                case "execute_result":
                    if isinstance(output["data"]["text/plain"], list):
                        text = "".join(output["data"]["text/plain"])
                    else:
                        text = output["data"]["text/plain"]
                    self.outputs_group.mount(OutputCell(text=text))
        self.refresh()

    async def run_cell(self):
        if not self.notebook.notebook_kernel:
            self.notify("No kernel available for notebook.", severity="error", timeout=8)
            return

        kernel: NotebookKernel = self.notebook.notebook_kernel

        self.source = self.code_area.text
        if not self.source:
            return

        outputs, execution_count = kernel.run_code(self.source)
        self.exec_count = execution_count
        self.outputs = outputs
        self.call_next(self.update_outputs, outputs)
