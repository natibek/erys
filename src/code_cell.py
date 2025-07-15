from __future__ import annotations
from asyncio import to_thread
from textual.app import ComposeResult
from textual.reactive import var
from textual.containers import HorizontalGroup, VerticalGroup
from textual.widgets import Static, Label, ContentSwitcher, Pretty
from typing import Any
from utils import COLLAPSED_COLOR, EXPANDED_COLOR
from textual.events import Key, DescendantBlur
from notebook_kernel import NotebookKernel
from cell import CopyTextArea, SplitTextArea, Cell

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
    running: bool = var(False, init=False)
    glyphs = {False: "▶", True: "□"}
    toolips = {False: "Run", True: "Interrupt"}

    def __init__(self, id: str = "") -> None:
        super().__init__(self.glyphs[False], id=id)
        self.tooltip = self.toolips[False]

    def on_click(self) -> None:
        code_cell: CodeCell = self.parent.parent.parent.parent

        if not self.running:
            self.run_worker(code_cell.run_cell)
        else:
            code_cell.interrupt_cell()

    def watch_running(self, is_running: bool) -> None:
        self.update(self.glyphs[is_running])
        self.tooltip = self.toolips[is_running]


class CodeArea(SplitTextArea):
    closing_map = {"{": "}", "(": ")", "[": "]", "'": "'", '"': '"'}

    def on_key(self, event: Key) -> None:
        if event.character in self.closing_map:
            self.insert(f"{event.character}{self.closing_map[event.character]}")
            self.move_cursor_relative(columns=-1)
            event.prevent_default()
            return

        super().on_key(event)

class OutputJson(HorizontalGroup):
    can_focus = True

    def __init__(self, data):
        super().__init__()
        self.data = data
        self.output_text = CopyTextArea(str(self.data), id="text")
        self.output_text.read_only = True
        self.output_text.styles.padding = 0
        self.output_text.styles.margin = 0
        self.output_text.styles.border = "solid", "gray"

    def compose(self) -> ComposeResult:
        self.switcher = ContentSwitcher(initial="json")
        with self.switcher:
            yield Pretty(self.data, id="json")
            yield self.output_text

    def _on_focus(self) -> None:
        self.switcher.current = "text"

    def on_descendant_blur(self, event: DescendantBlur) -> None:
        self.switcher.current = "json"

    def _on_blur(self) -> None:
        if not self.app.focused or self.app.focused != self.output_text:
            self.switcher.current = "json"


class OutputText(CopyTextArea):
    read_only = True

    def _on_focus(self) -> None:
        self.styles.border = "solid", "gray"

    def _on_blur(self) -> None:
        self.styles.border = None


class CodeCell(Cell):
    BINDINGS = [
        ("r", "run_cell", "Run Cell"),
    ]
    exec_count: int | None = var(None)
    cell_type = "code"

    def __init__(
        self,
        notebook,
        source: str = "",
        outputs: list[dict[str, Any]] = [],
        exec_count: int | None = None,
        metadata: dict[str, Any] = {},
        cell_id: str | None = None,
        language: str = "Python"
    ) -> None:
        super().__init__(notebook, source, metadata, cell_id)
        self.outputs: list[dict[str, Any]] = outputs
        self.exec_count = exec_count
        self._language = language
        self.switcher.current = ""

    def compose(self) -> ComposeResult:
        with HorizontalGroup():
            with HorizontalGroup(id="code-sidebar"):
                yield self.collapse_btn
                with VerticalGroup():
                    self.run_label = RunLabel(id="run-button")
                    yield self.run_label
                    self.exec_count_display = Static(
                        f"[{self.exec_count or ' '}]", id="exec-count"
                    )
                    yield self.exec_count_display
            self.input_text = CodeArea.code_editor(
                self.source,
                language=self._language.lower(),
                id="text",
                soft_wrap=True,
                theme="vscode_dark",
            )
            with self.switcher:
                yield self.input_text
                yield self.collapsed_display

        with HorizontalGroup(id="output-section"):
            self.output_collapse_btn = OutputCollapseLabel(
                id="output-collapse-button"
            ).with_tooltip("Collapse Output")

            self.outputs_group = VerticalGroup(id="outputs")
            self.output_switcher = ContentSwitcher(
                id="collapse-outputs", initial="outputs"
            )
            yield self.output_collapse_btn
            with self.output_switcher:
                yield self.outputs_group
                yield Static("Outputs are collapsed...", id="collapsed-output")

    def on_mount(self):
        self.output_collapse_btn.display = len(self.outputs) > 0
        self.call_after_refresh(self.update_outputs, self.outputs)

    def escape(self, event: Key):
        self.focus()
        event.stop()

    def watch_exec_count(self, new: int | None) -> None:
        self.call_after_refresh(
            lambda: self.exec_count_display.update(f"[{new or ' '}]")
        )

    async def action_run_cell(self) -> None:
        self.run_worker(self.run_cell)

    def action_collapse(self) -> None:
        if not self.collapse_btn.collapsed or not self.output_collapse_btn.collapsed:
            self.collapse_btn.collapsed = True
            self.output_collapse_btn.collapsed = True
        else:
            self.collapse_btn.collapsed = not self.collapse_btn.collapsed
            self.output_collapse_btn.collapsed = not self.output_collapse_btn.collapsed 

    async def open(self):
        self.call_after_refresh(self.input_text.focus)

    @staticmethod
    def from_nb(nb: dict[str, Any], notebook) -> "CodeCell":
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

    def to_nb(self) -> dict[str, Any]:
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
            "source": self.input_text.text,
        }

    def create_cell(self, source) -> "CodeCell":
        return CodeCell(self.notebook, source)

    def clone(self, connect: bool = True) -> "CodeCell":
        clone = CodeCell(
            notebook=self.notebook,
            source=self.input_text.text,
            outputs=self.outputs,
            exec_count=self.exec_count,
            metadata=self._metadata,
            cell_id=self._cell_id,
            language=self._language,
        )
        if connect:
            clone.next = self.next
            clone.prev = self.prev

        return clone

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
                    self.outputs_group.mount(OutputText(text=text))
                case "error":
                    text = "\n".join(output["traceback"])
                    with open("output", "w") as f:
                        f.write(f"{text}\n")
                    self.outputs_group.mount(OutputText(text=text))
                case "execute_result" | "display_data":
                    for type, data in output["data"].items():
                        match type:
                            case "text/plain":
                                if isinstance(data, list):
                                    text = "".join(data)
                                else:
                                    text = data
                                self.outputs_group.mount(OutputText(text=text))
                            case "application/json":
                                self.outputs_group.mount(OutputJson(data))
                            case "img/png":
                                self.outputs_group.mount(OutputJson(data))

        self.refresh()

    async def run_cell(self) -> None:
        if not self.notebook.notebook_kernel:
            self.notify(
                "No kernel available for notebook.", severity="error", timeout=8
            )
            return

        kernel: NotebookKernel = self.notebook.notebook_kernel

        self.source = self.input_text.text
        if not self.source:
            return

        self.run_label.running = True
        outputs, execution_count = await to_thread(kernel.run_code, self.source)
        self.run_label.running = False
        self.exec_count = execution_count
        self.outputs = outputs
        self.call_next(self.update_outputs, outputs)

    def interrupt_cell(self) -> None:
        if not self.notebook.notebook_kernel:
            self.notify(
                "No kernel available for notebook.", severity="error", timeout=8
            )
            return

        kernel: NotebookKernel = self.notebook.notebook_kernel
        kernel.interrupt_kernel()