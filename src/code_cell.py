from textual.app import ComposeResult
from textual.reactive import reactive
from textual.containers import HorizontalGroup, VerticalGroup
from textual.widgets import Button, Static, TextArea, Label, Markdown, Log, RichLog
from typing import Any
from utils import generate_id
from textual.events import Key
from IPython.utils import io

from IPython.core.interactiveshell import InteractiveShell
import re

class RunLabel(Label):
    can_focus = True

    def on_click(self) -> None:
        code_cell: CodeCell = self.parent.parent
        if code_cell.shell is None:
            return
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
        shell: InteractiveShell | None = None,
    ) -> None:
        super().__init__()

        self.source = source

        self.outputs:list[dict[str, Any]] = outputs
        self.exec_count = exec_count

        self.metadata = metadata
        self.cell_id = cell_id or generate_id()
        self.shell = shell

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
                    text = "".join(output["text"])
                    output_widget.mount(OutputCell(text=text))
                case "error":
                    text = "".join(output["traceback"])
                    log = RichLog(highlight=True)
                    log.write(text)
                    output_widget.mount(log)#OutputCell(text=text))
                case "execute_result":
                    text = "".join(output["data"]["text/plain"])
                    output_widget.mount(OutputCell(text=text))
        self.refresh()

    def action_run_cell(self) -> None:
        self.call_after_refresh(self.run_cell)
    
    def run_cell(self):
        source = self.query_one("#code-editor", CodeArea).text
        self.source = source

        # capture the stdout and stderr
        with io.capture_output() as captured:
            result = self.shell.run_cell(source, store_history=True)

        outputs = []

        stdout_result = captured.stdout
        if stdout_result:
            text = [string+"\n" for string in stdout_result.split("\n") if string]
            if result.result:
                ipython_output_pattern = re.escape(f"Out[{result.execution_count}]: {result.result}")
                match = None
                for m in re.finditer(ipython_output_pattern, text[-1]): match = m
                if match:
                    if (start := match.span()[0]) == 0: # the 'Out[d]: result' is the begining of the last line
                        text.pop()
                    else:
                        text[-1] = text[-1][0:start]
            elif stdout_result[-1] != "\n":
                text[-1] = text[-1][:-1]

            stdout_output = {
                "output_type" : "stream",
                "name" : "stdout",
                "text" : text,
            }
            outputs.append(stdout_output)

        stderr_result = captured.stderr
        if stderr_result:
            text = [string+"\n" for string in stderr_result.split("\n") if string]
            if stderr_result[-1] != "\n":
                text[-1] = text[-1][:-1]

            stderr_output = {
                "output_type" : "stream",
                "name" : "stderr",
                "text" : text,
            }
            outputs.append(stderr_output)


        if result.result is not None: 
            exec_result = {
                "output_type" : "execute_result",
                "execution_count": result.execution_count,
                "data" : {
                    "text/plain" : [str(result.result)],
                    # "image/png": ["base64-encoded-png-data"],
                    # "application/json": {
                    # # JSON data is included as-is
                    # "json": "data",
                    # },
                },
                # "metadata" : {
                #     "image/png": {
                #     "width": 640,
                #     "height": 480,
                #     },
                # },
            }    # gives execute_result output
            outputs.append(exec_result)

        with open("../output", "a") as f:
            f.write(f"\nexecuting {source}")
            f.write(f"\n{stdout_result=}")
            f.write(f"\n{stderr_result=}")
            f.write(f"\n{result.result=}")
            f.write(f"\n{outputs=}\n")
            
        self.exec_count = result.execution_count
        self.outputs = outputs
        self.call_next(lambda: self.update_outputs(outputs))

    def compose(self) -> ComposeResult:
        with VerticalGroup(id="code-sidebar"):
            yield RunLabel("▶", id="run-button")
            yield Static(f"[{self.exec_count or ' '}]", id="exec-count")
        with VerticalGroup():
            yield CodeArea.code_editor(self.source, language="python", id="code-editor")
            yield VerticalGroup(id="outputs")