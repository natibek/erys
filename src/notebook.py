from textual.app import ComposeResult
from textual.widgets import Button, TextArea
from textual.containers import HorizontalGroup, VerticalScroll, Container
from textual.events import Key, DescendantFocus

from typing import Any
import json

from markdown_cell import MarkdownCell, FocusMarkdown, CopyTextAreaMarkdown
from code_cell import CodeCell, CodeArea, OutputText, OutputJson
from notebook_kernel import NotebookKernel
from save_as_screen import SaveAsScreen


class ButtonRow(HorizontalGroup):
    def compose(self) -> ComposeResult:
        yield Button("➕ Code", id="add-code-cell")
        yield Button("➕ Markdown", id="add-markdown-cell")
        yield Button("▶ Run All", id="run-all")
        yield Button("🔁 Restart", id="restart-shell")


class Notebook(Container):
    """A Textual app to manage stopwatches."""
    last_focused = None

    SCREENS = {"save_as_screen": SaveAsScreen}
    BINDINGS = [
        ("a", "add_cell_after", "Add cell after"),
        ("b", "add_cell_before", "Add cell before"),
        ("ctrl+d", "delete_cell", "Delete cell"),
        ("ctrl+s", "save", "Save"),
        ("ctrl+w", "save_as", "Save As"),
    ]

    def __init__(self, path: str, id: str) -> None:
        super().__init__(id=id)

        self.path = path
        self.notebook_kernel = NotebookKernel()

        self._metadata: dict[str, Any] | None = None
        self._nbformat: int = 4
        self._nbformat_minor: int = 5

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield ButtonRow()
        self.cell_container = VerticalScroll(id="cell-container")
        yield self.cell_container

    def on_mount(self):
        if self.path != "new_empty_terminal_notebook":
            self.call_after_refresh(self.load_notebook)

        self.call_after_refresh(self.focus_notebook)

    def on_unmount(self) -> None:
        if self.notebook_kernel:
            self.notebook_kernel.shutdown_kernel()

    def on_descendant_focus(self, event: DescendantFocus) -> None:
        # Ignore buttons
        if isinstance(event.widget, CodeCell) or isinstance(event.widget, MarkdownCell):
            self.last_focused = event.widget
        elif isinstance(event.widget, OutputText) or isinstance(event.widget, OutputJson):
            self.last_focused = event.widget.parent.parent.parent.parent
        elif isinstance(event.widget, CodeArea):
            self.last_focused = event.widget.parent.parent.parent
        elif any(
            isinstance(event.widget, widgetType)
            for widgetType in [FocusMarkdown, CopyTextAreaMarkdown]
        ):
            self.last_focused = event.widget.parent.parent

    def on_key(self, event: Key) -> None:
        match event.key:
            case "tab" | "shift+tab":
                event.prevent_default() 
                event.stop()

        if not isinstance(self.app.focused, TextArea):
            match event.key:
                case "up":
                    if self.last_focused and (prev_cell := self.last_focused.prev):
                        prev_cell.focus_widget()
                case "down":
                    if self.last_focused and (next_cell := self.last_focused.next):
                        next_cell.focus_widget()


    async def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "add-code-cell":
                widget = await self.add_cell(CodeCell, "after")
                self.call_after_refresh(widget.open)
            case "add-markdown-cell":
                widget = await self.add_cell(MarkdownCell, "after")
                self.call_after_refresh(widget.open)
            case "restart-shell":
                self.notebook_kernel.restart_kernel()
            case "run-all":
                if not self.notebook_kernel:
                    self.notify("No kernel available for notebook.", severity="error", timeout=8)
                    return

                for child in self.cell_container.children:
                    if isinstance(child, CodeCell):
                        await child.run_cell()

    async def action_add_cell_after(self) -> None:
        await self.add_cell(CodeCell, "after")

    async def action_add_cell_before(self) -> None:
        await self.add_cell(CodeCell, "before")

    def action_save_as(self) -> None:
        self.app.switch_screen("save_as_screen")

    def action_save(self) -> None:
        if self.path == "new_empty_terminal_notebook":
            self.action_save_as()
        else:
            nb = self.to_nb()
            with open(self.path, "w") as nb_file:
                json.dump(nb, nb_file)

    def action_delete_cell(self) -> None:
        # TODO: Move to cells
        # TODO: Change the focused cell when one is deleted
        if self.last_focused:
            self.call_after_refresh(self.last_focused.remove)
            # update the prev and next pointers 
            # update the new focused cell
            last_focused = None
            if prev := self.last_focused.prev:
                last_focused = prev
                prev.next = self.last_focused.next

            if next := self.last_focused.next:
                last_focused = next
                next.prev = self.last_focused.prev

            self.last_focused = last_focused

            if self.last_focused:
                self.last_focused.focus_widget()

    def focus_notebook(self):
        if self.last_focused:
            self.call_after_refresh(self.last_focused.focus_widget)
        else:
            self.call_after_refresh(self.cell_container.focus)

    def load_notebook(self):
        with open(self.path, "r") as notebook_file:
            content = json.load(notebook_file)
            for idx, cell in enumerate(content["cells"]):
                if cell["cell_type"] == "code":
                    widget = CodeCell.from_nb(cell, self)
                elif cell["cell_type"] == "markdown":
                    widget = MarkdownCell.from_nb(cell)

                if idx != 0:
                    prev.next = widget
                    widget.prev = prev
                else:
                    self.last_focused = widget

                prev = widget
                self.call_next(self.cell_container.mount, widget)

    async def add_cell(
        self, cell_type: CodeCell | MarkdownCell, position: str = "after", **cell_kwargs
    ) -> CodeCell | MarkdownCell:
        """
        Position is after or before.
        """
        kwargs = {position: self.last_focused}

        if cell_type is CodeCell:
            widget = cell_type(self, **cell_kwargs)
        else:
            widget = cell_type(**cell_kwargs)

        await self.cell_container.mount(widget, **kwargs)

        if not self.last_focused:
            self.last_focused = widget
            self.last_focused.focus_widget()
        elif position == "after":
            next = self.last_focused.next
            self.last_focused.next = widget
            widget.next = next
            widget.prev = self.last_focused

            if next:
                next.prev = widget

        elif position == "before":
            prev = self.last_focused.prev
            self.last_focused.prev = widget
            widget.next = self.last_focused
            widget.prev = prev

            if prev:
                prev.next = widget

        return widget

    def to_nb(self) -> dict[str, Any]:
        """
        Format for notebook
        {
            "metadata" : {
                "signature": "hex-digest",
                "kernel_info": {
                    "name" : "the name of the kernel"
                },
                "language_info": {
                    "name" : "the programming language of the kernel",
                    "version": "the version of the language",
                    "codemirror_mode": "The name of the codemirror mode to use [optional]"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 0,
            "cells" : [
            ],
        }
        """
        kernel_spec = self.notebook_kernel.get_kernel_spec()
        kernel_info = self.notebook_kernel.get_kernel_info()
        language_info = self.notebook_kernel.get_language_info()

        cells = [cell.to_nb() for cell in self.cell_container.children]

        return {
            "metadata": {
                "kernel_info": kernel_info,
                "kernel_spec": kernel_spec,
                "language_info": language_info,
            },
            "nbformat": self._nbformat,
            "nbformat_minor": self._nbformat_minor,
            "cells": cells,
        }
