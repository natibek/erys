from __future__ import annotations
from asyncio import to_thread
from textual.app import ComposeResult
from textual.reactive import var
from textual.containers import HorizontalGroup, VerticalGroup
from textual.widgets import Static, Label, ContentSwitcher, Pretty
from typing import Any
import re
from utils import COLLAPSED_COLOR, EXPANDED_COLOR
from textual.events import Key, DescendantBlur
from rich.text import Text
from notebook_kernel import NotebookKernel
from cell import CopyTextArea, SplitTextArea, Cell

class OutputCollapseLabel(Label):
    """Custom label to use as the collapse button for the output of a code cell."""
    collapsed = var(False, init=False) # keep track of collapse state

    def __init__(self, collapsed: bool = False, id: str = "") -> None:
        super().__init__("\n┃", id=id)
        self.collapsed = collapsed

    def on_click(self) -> None:
        """Toggle the collapsed state on clicks."""
        self.collapsed = not self.collapsed

    def watch_collapsed(self, collapsed: bool) -> None:
        """Watched method to switch the content from the outputs to the collapsed label.

        Args:
            collapsed: updated collapsed state.
        """
        code_cell: CodeCell = self.parent.parent

        if collapsed and len(code_cell.outputs) > 0:
            code_cell.output_switcher.current = "collapsed-output"
            self.styles.color = COLLAPSED_COLOR
        else:
            code_cell.output_switcher.current = "outputs"
            self.styles.color = EXPANDED_COLOR


class RunLabel(Label):
    """Custom label used as button for running/interrupting code cell."""
    running: bool = var(False, init=False)
    glyphs = {False: "▶", True: "□"} # glyphs representing running state
    toolips = {False: "Run", True: "Interrupt"}

    def __init__(self, id: str = "") -> None:
        super().__init__(self.glyphs[False], id=id)
        self.tooltip = self.toolips[False]

    def on_click(self) -> None:
        """Button to run or interrupt code cell."""
        code_cell: CodeCell = self.parent.parent.parent.parent

        if not self.running:
            self.run_worker(code_cell.run_cell)
        else:
            code_cell.interrupt_cell()

    def watch_running(self, is_running: bool) -> None:
        """Watcher method to update the glyph and the tooltip depending on running state.
        
        Args:
            is_running: whether the code cell is running.
        """
        self.update(self.glyphs[is_running])
        self.tooltip = self.toolips[is_running]


class CodeArea(SplitTextArea):
    """Widget used for editing code. Inherits from the SplitTextArea."""
    closing_map = {"{": "}", "(": ")", "[": "]", "'": "'", '"': '"'}

    def on_key(self, event: Key) -> None:
        """Key press event handler to close brackets and quotes.

        Args:
            event: Key press event. 
        """
        if event.character in self.closing_map:
            self.insert(f"{event.character}{self.closing_map[event.character]}")
            self.move_cursor_relative(columns=-1)
            event.prevent_default()
            return

        super().on_key(event)

class OutputJson(HorizontalGroup):
    """Widget for displaying application/json output_type."""
    can_focus = True # Make the widget focusable

    def __init__(self, data):
        super().__init__()
        self.data = data
        self.output_text = CopyTextArea(str(self.data), id="plain-json")
        self.output_text.read_only = True
        self.output_text.styles.padding = 0
        self.output_text.styles.margin = 0
        self.output_text.styles.border = "solid", "gray"

    def compose(self) -> ComposeResult:
        """Composed of 
            - Content switcher (initial=pretty-json)
                - Pretty (id=pretty-json)
                - CopyTextArea (id=plain-json)
        """
        self.switcher = ContentSwitcher(initial="pretty-json")
        with self.switcher:
            yield Pretty(self.data, id="pretty-json")
            yield self.output_text

    def _on_focus(self) -> None:
        """Switch to plain-json when focusing on widget."""
        self.switcher.current = "plain-json"

    def on_descendant_blur(self, event: DescendantBlur) -> None:
        """Switch to pretty-json when bluring away from descendants."""
        self.switcher.current = "pretty-json"

    def _on_blur(self) -> None:
        """Swtich to the pretty-json when bluring away from widget unless new focused widget is
        the plain-json.
        """
        if not self.app.focused or self.app.focused != self.output_text:
            self.switcher.current = "pretty-json"


class OutputText(CopyTextArea):
    """Widget for displaying stream/plain error outputs"""
    read_only = True # make text area read only

    def _on_focus(self) -> None:
        """Add border when focused."""
        self.styles.border = "solid", "gray"

    def _on_blur(self) -> None:
        """Remove border when focused."""
        self.styles.border = None

class OutputError(HorizontalGroup):
    """Widget for displaying error output_type for code cells."""
    can_focus = True # make widget focusable

    def __init__(self, error_string: list[str]) -> None:
        super().__init__()
        error_string = "\n".join(error_string) # comes as a multiline 
        self.plain_error_string = self.replace_ansi_escape_with_markup(error_string, True) # remove the ansi
        self.pretty_error_string = Text.from_ansi(error_string) # convert ansi to markup

        self.static_output = Static(content=self.pretty_error_string, id="pretty-error-output")
        self.text_output = OutputText(text=self.plain_error_string, id="plain-error-output")

    def compose(self) -> ComposeResult:
        """Composed of 
            - HorizontalGroup
                - Content switcher (initial=pretty-error-output)
                    - Pretty (id=pretty-error-output)
                    - CopyTextArea (id=plain-error-output)
        """
        self.switcher = ContentSwitcher(initial="pretty-error-output")
        with self.switcher:
            yield self.static_output
            yield self.text_output
   
    def _on_focus(self) -> None:
        """Switch to plain-error-output when focusing on widget."""
        self.switcher.current = "plain-error-output"

    def on_descendant_blur(self, event: DescendantBlur) -> None:
        """Switch to pretty-error-output when bluring away from descendants."""
        self.switcher.current = "pretty-error-output"

    def _on_blur(self) -> None:
        """Swtich to the pretty-error-output when bluring away from widget unless new focused
        widget is the plain-error-output.
        """
        if not self.app.focused or self.app.focused != self.text_output:
            self.switcher.current = "pretty-error-output"

    def replace_ansi_escape_with_markup(self, ansi_escaped_string: str, remove: bool = False) -> str:
        """Returns the strings with ansi escapes replaced with markup if map is found but removed  if not 
        using regex. Used to remove color from error messages.
        
        Args:
            ansi_escaped_string: input string containing ansi escapes.
        
        Returns: string without ansi escapes.
        """
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        return ansi_escape.sub("" if remove else self.substitute_with_markup, ansi_escaped_string)

class CodeCell(Cell):
    """Widget to contain code cells in a notebook"""
    BINDINGS = [
        ("r", "run_cell", "Run Cell"),
    ]
    exec_count: int | None = var(None, init=False) # Reactive to keep track of the execution count
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

        self.run_label = RunLabel(id="run-button")
        self.exec_count_display = Static(
            f"[{self.exec_count or ' '}]", id="exec-count"
        )

        self.input_text = CodeArea.code_editor(
            self.source,
            language=self._language.lower(),
            id="text",
            soft_wrap=True,
            theme="vscode_dark",
        )

        self.output_collapse_btn = OutputCollapseLabel(
            id="output-collapse-button"
        ).with_tooltip("Collapse Output")

        self.outputs_group = VerticalGroup(id="outputs")
        self.output_switcher = ContentSwitcher(
            id="collapse-outputs", initial="outputs"
        )

    def compose(self) -> ComposeResult:
        """Compose with:
            - VerticalGroup
                - HorziontalGroup
                    - HorizontalGroup (id=code-sidte)
                        - CollapseLabel (id=collapse-button)
                        - Static (id=exec-count)
                    - ContentSwitcher (id=collapse-content)
                        - CodeArea (id=text)
                        - Static (id=collapsed-display)
                - HorizontalGroup (id=output-section)
                    - OutputCollapseLabel (id=output-collapse-button)
                    - ContentSwitcher (id=collapse-outputs)
                        - VerticalGroup (id=outputs)
                        - Static (id=collapsed-output)
        """
        with HorizontalGroup():
            with HorizontalGroup(id="code-sidebar"):
                yield self.collapse_btn
                with VerticalGroup():
                    yield self.run_label
                    yield self.exec_count_display
            with self.switcher:
                yield self.input_text
                yield self.collapsed_display

        with HorizontalGroup(id="output-section"):
            yield self.output_collapse_btn
            with self.output_switcher:
                yield self.outputs_group
                yield Static("Outputs are collapsed...", id="collapsed-output")

    def on_mount(self):
        """On mount, toggle the display for the output collapse button if there are outputs and 
        display the outputs.
        """
        self.output_collapse_btn.display = len(self.outputs) > 0
        self.call_after_refresh(self.update_outputs, self.outputs)

    def escape(self, event: Key):
        """Event handler to be called when the escape key is pressed."""
        self.focus()
        event.stop()

    def watch_exec_count(self, new: int | None) -> None:
        """Watcher for the execution count to update the value of the Static widget when it changes."""
        self.call_after_refresh(
            lambda: self.exec_count_display.update(f"[{new or ' '}]")
        )

    async def action_run_cell(self) -> None:
        """Action for the run cell binding. Calls the `run_cell` function."""
        self.run_worker(self.run_cell)

    def action_collapse(self) -> None:
        """Action for the collapse cell binding. If the outputs or the code cell is not collapsed,
        collapse it; otherwise, toggle the collapsed state.
        """
        if not self.collapse_btn.collapsed or not self.output_collapse_btn.collapsed:
            self.collapse_btn.collapsed = True
            self.output_collapse_btn.collapsed = True
        else:
            self.collapse_btn.collapsed = not self.collapse_btn.collapsed
            self.output_collapse_btn.collapsed = not self.output_collapse_btn.collapsed 

    async def open(self):
        """Defines what it means to open a code cell. Focus on the input_text widget."""
        self.call_after_refresh(self.input_text.focus)

    @staticmethod
    def from_nb(nb: dict[str, Any], notebook) -> "CodeCell":
        """Static method to generate a `CodeCell` from a json/dict that represent a code cell.

        Args:
            nb: the notebook json/dict format of the code cell.
            notebook: the `Notebook` object the code cell belongs too.
        
        Raises:
            AssertionError: if no notebook or bad notebook representation.
        """
        # need to have a notebook object and a notebook format
        assert nb
        assert notebook
        # needs to be a valid notebook representation
        for key in ["cell_type", "execution_count", "metadata", "source", "outputs"]:
            assert key in nb
        assert nb["cell_type"] == "code"

        source = nb["source"]
        if isinstance(source, list):
            # join the strings if the input was a multiline string
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
        """Serialize the `CodeCell` to notebook format. Format for code cell:
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

        Returns: serialized code cell representation.
        """
        return {
            "cell_type": "code",
            "execution_count": self.exec_count,
            "id": self._cell_id,
            "metadata": self._metadata,
            "outputs": self.outputs,
            "source": self.input_text.text,
        }

    def create_cell(self, source: str) -> "CodeCell":
        """Returns a `CodeCell` with a source. Used for splitting code cell."""
        return CodeCell(notebook=self.notebook, source=source)

    def clone(self, connect: bool = True) -> "CodeCell":
        """Clone a code cell. Used for cut/paste.
        
        Args:
            connect: whether to keep the pointers to the next and previous cells.
        
        Returns: cloned code cell.
        """
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
        """Generate the widgets to store the different output types that result from running
        code cell.

        Args:
            outputs: list of serialized outputs. 
        """
        try:
            self.outputs_group = self.query_one("#outputs", VerticalGroup)
        except:
            return

        self.output_collapse_btn.display = len(outputs) > 0
        # remove the children widgets first
        await self.outputs_group.remove_children()

        for output in outputs:
            match output["output_type"]:
                case "stream":
                    # join the strings and display them in the `OutputText` widget
                    if isinstance(output["text"], list):
                        text = "".join(output["text"])
                    else:
                        text = output["text"]
                    self.outputs_group.mount(OutputText(text=text))
                case "error":
                    # display the errors with the `OutputError` widget
                    self.outputs_group.mount(OutputError(output["traceback"]))
                case "execute_result" | "display_data":
                    # the display_data and output_result have different formats
                    for type, data in output["data"].items():
                        match type:
                            case "text/plain":
                                # plain text can also use the `OutputText` widget for display
                                if isinstance(data, list):
                                    text = "".join(data)
                                else:
                                    text = data
                                self.outputs_group.mount(OutputText(text=text))
                            case "application/json":
                                # json is displayed with the `OutputJson` widget
                                self.outputs_group.mount(OutputJson(data))
                            case "img/png":
                                self.outputs_group.mount(OutputJson(data))

        self.refresh()

    async def run_cell(self) -> None:
        """Run code in code cell with the kernel in a thread. Update the outputs and the
        execution count for the cell.
        """
        if not self.notebook.notebook_kernel: # check if there is a kernel for the notebook
            self.notify(
                "No kernel available for notebook.", severity="error", timeout=8
            )
            return

        kernel: NotebookKernel = self.notebook.notebook_kernel

        self.source = self.input_text.text 
        if not self.source: # only call the kernel execute if there is code
            return

        self.run_label.running = True # update the running status for the code cell
        outputs, execution_count = await to_thread(kernel.run_code, self.source)
        self.run_label.running = False 
        self.exec_count = execution_count
        self.outputs = outputs
        self.call_next(self.update_outputs, outputs) # update the output cells

    def interrupt_cell(self) -> None:
        """Interrupt kernel when running cell."""
        if not self.notebook.notebook_kernel:
            self.notify(
                "No kernel available for notebook.", severity="error", timeout=8
            )
            return

        kernel: NotebookKernel = self.notebook.notebook_kernel
        kernel.interrupt_kernel()