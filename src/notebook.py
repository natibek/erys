from textual.app import ComposeResult
from textual.widgets import Button, TextArea
from textual.containers import HorizontalGroup, VerticalScroll, Container
from textual.events import Key, DescendantFocus

from typing import Any
import json

from markdown_cell import MarkdownCell, FocusMarkdown
from code_cell import CodeCell, CodeArea, OutputText, OutputJson
from cell import CopyTextArea
from notebook_kernel import NotebookKernel


class ButtonRow(HorizontalGroup):
    def compose(self) -> ComposeResult:
        yield Button("➕ Code", id="add-code-cell")
        yield Button("➕ Markdown", id="add-markdown-cell")
        yield Button("▲ Run Before", id="run-before")
        yield Button("▼ Run After", id="run-after")
        # yield Button("▶ ↑ Run Before", id="run-before")
        # yield Button("▶ ↓ Run After", id="run-after")
        yield Button("▶ Run All", id="run-all")
        yield Button("🔁 Restart", id="restart-shell")


class Notebook(Container):
    """A Textual app to manage stopwatches."""

    last_focused = None
    last_copied = None
    _delete_stack = []
    _merge_list: list[CodeCell | MarkdownCell] = []
    
    BINDINGS = [
        ("a", "add_cell_after", "Add Cell After"),
        ("b", "add_cell_before", "Add Cell Before"),
        ("ctrl+up", "move_up", "Move Cell Up"),
        ("ctrl+down", "move_down", "Move Cell Down"),
        ("M", "merge_cells", "Merge Cells"),
        ("ctrl+c", "copy_cell", "Copy Cell"),
        ("ctrl+x", "cut_cell", "Cut Cell"),
        ("ctrl+v", "paste_cell", "Paste Cell"),
        ("ctrl+d", "delete_cell", "Delete Cell"),
        ("ctrl+s", "save", "Save"),
        ("ctrl+w", "save_as", "Save As"),
    ]

    def __init__(self, path: str, id: str, term_app) -> None:
        super().__init__(id=id)

        self.path = path
        self.notebook_kernel = NotebookKernel()
        self.term_app = term_app

        self._metadata: dict[str, Any] | None = None
        self._nbformat: int = 4
        self._nbformat_minor: int = 5

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield ButtonRow()
        self.cell_container = VerticalScroll(id="cell-container")
        yield self.cell_container

    def on_mount(self) -> None:
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
        elif isinstance(event.widget, OutputText) or isinstance(
            event.widget, OutputJson
        ):
            self.last_focused = event.widget.parent.parent.parent.parent
        # elif isinstance(event.widget, CodeArea):
        #     self.last_focused = event.widget.parent.parent.parent
        elif any(
            isinstance(event.widget, widgetType)
            for widgetType in [FocusMarkdown, CopyTextArea, CodeArea]
        ):
            self.last_focused = event.widget.parent.parent.parent

    def on_key(self, event: Key) -> None:
        match event.key:
            case "tab" | "shift+tab":
                event.prevent_default()
                event.stop()
            case "escape":
                for cell in self._merge_list:
                    cell.merge_select = False

                self._merge_list = []

        if not isinstance(self.app.focused, TextArea):
            match event.key:
                case "up":
                    if self.last_focused and (prev_cell := self.last_focused.prev):
                        prev_cell.focus()
                case "down":
                    if self.last_focused and (next_cell := self.last_focused.next):
                        next_cell.focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "add-code-cell":
                widget = await self.add_cell(CodeCell, self.last_focused, "after")
                self.call_after_refresh(widget.open)
            case "add-markdown-cell":
                widget = await self.add_cell(MarkdownCell, self.last_focused, "after")
                self.call_after_refresh(widget.open)
            case "restart-shell":
                self.notebook_kernel.restart_kernel()
            case "run-all" | "run-after" | "run-before" if not self.notebook_kernel:
                if not self.notebook_kernel:
                    self.notify(
                        "No kernel available for notebook.", severity="error", timeout=8
                    )
                    self.last_focused.focus()
                    return
            case "run-all":
                for cell in self.cell_container.children:
                    if isinstance(cell, CodeCell):
                        await cell.run_cell()
                self.last_focused.focus()
            case "run-after":
                if not self.last_focused: return

                cell = self.last_focused
                while cell:
                    if isinstance(cell, CodeCell):
                        await cell.run_cell()
                    cell = cell.next 
                self.last_focused.focus()

            case "run-before":
                if not self.last_focused: return
                for cell in self.cell_container.children:
                    if cell == self.last_focused:
                        break
                    if isinstance(cell, CodeCell):
                        await cell.run_cell()
                self.last_focused.focus()

    async def action_add_cell_after(self) -> None:
        await self.add_cell(CodeCell, self.last_focused, "after")

    async def action_add_cell_before(self) -> None:
        await self.add_cell(CodeCell, self.last_focused, "before")

    def action_save_as(self) -> str:
        def check_save_as(path: str | None) -> None:
            if path:
                self.path = path
                self.save_notebook(path)
                self.notify(f"{self.path} saved!")

                self.term_app.open_notebook(path)

        self.app.push_screen("save_as_screen", check_save_as)

    def action_save(self) -> None:
        if self.path == "new_empty_terminal_notebook":
            self.action_save_as()
        else:
            self.save_notebook(self.path)
            self.notify(f"{self.path} saved!")

    def action_delete_cell(self) -> None:
        if not self.last_focused: return
        # update the prev and next pointers
        # update the new focused cell
        last_focused, position = self.last_focused.disconnect()
        # self.delete_stack.append(
        #     (self.last_focused.clone(connect=False), position, last_focused.id)
        # )

        self.call_after_refresh(self.last_focused.remove)
        self.last_focused = last_focused

        if self.last_focused:
            self.last_focused.focus()

    def action_copy_cell(self) -> None:
        if not self.last_focused: return
        self.last_copied = self.last_focused.to_nb()
    
    def action_cut_cell(self) -> None:
        if not self.last_focused: return

        self.last_copied = self.last_focused.to_nb()
        self.action_delete_cell()

    async def action_paste_cell(self) -> None:
        if not self.last_copied: return

        match self.last_copied["cell_type"]:
            case "markdown":
                widget = MarkdownCell.from_nb(self.last_copied, self)
            case "code":
                widget = CodeCell.from_nb(self.last_copied, self)

        widget.set_new_id()
        await self.cell_container.mount(widget, after=self.last_focused)
        self.connect_widget(widget)

    async def action_move_up(self) -> None:
        if not self.last_focused: return 

        if self.last_focused.prev:
            clone = self.last_focused.clone()
            prev = clone.prev

            # removes the cell
            prev.next = clone.next
            if clone.next:
                clone.next.prev = prev

            if prev.prev:
                prev.prev.next = clone

            clone.prev = prev.prev
            clone.next = prev
            prev.prev = clone

            await self.cell_container.mount(clone, before=clone.next)
            self.last_focused.remove()
            self.last_focused = clone
            self.last_focused.focus()

    async def action_move_down(self) -> None:
        if not self.last_focused: return 

        if self.last_focused.next:
            clone = self.last_focused.clone()
            next = clone.next

            # removes the cell
            next.prev = clone.prev
            if clone.prev:
                clone.prev.next = next

            if two_down := next.next:
                two_down.prev = clone

            # adds the cell
            clone.prev = next
            clone.next = next.next
            next.next = clone

            await self.cell_container.mount(clone, after=clone.prev)
            self.last_focused.remove()
            self.last_focused = clone
            self.last_focused.focus()

    def action_merge_cells(self) -> None:
        """Merge selected cells by combining content in text areas into the one selected. Should be
        called by the first selected cell in the the cells to merge. The resulting type will be 
        self.
        """
        if len(self._merge_list) < 2: return
        target: CodeCell | MarkdownCell = self._merge_list[0]
        target.merge_cells_with_self(self._merge_list[1:])
        target.merge_select = False
        self._merge_list = []

    def focus_notebook(self) -> None:
        if self.last_focused:
            self.call_after_refresh(self.last_focused.focus)
        else:
            self.call_after_refresh(self.cell_container.focus)

    def save_notebook(self, path) -> None:
        nb = self.to_nb()
        with open(path, "w") as nb_file:
            json.dump(nb, nb_file)

    def load_notebook(self) -> None:
        with open(self.path, "r") as notebook_file:
            content = json.load(notebook_file)
            for idx, cell in enumerate(content["cells"]):
                if cell["cell_type"] == "code":
                    widget = CodeCell.from_nb(cell, self)
                elif cell["cell_type"] == "markdown":
                    widget = MarkdownCell.from_nb(cell, self)

                if idx != 0:
                    prev.next = widget
                    widget.prev = prev
                else:
                    self.last_focused = widget

                prev = widget
                self.call_next(self.cell_container.mount, widget)

    async def add_cell(
        self, cell_type: CodeCell | MarkdownCell, relative_to: CodeCell | MarkdownCell | None, position: str = "after",  **cell_kwargs
    ) -> CodeCell | MarkdownCell:
        """
        Position is after or before.
        """
        kwargs = {position: relative_to}

        widget = cell_type(self, **cell_kwargs)

        await self.cell_container.mount(widget, **kwargs)
        self.connect_widget(widget, position)
            
        return widget

    def connect_widget(self, widget: CodeCell|MarkdownCell, position: str = "after") -> None:
        """
            Args:
                position: Where in relation to the focused cell to connect the widget 'after', 'before'
        """
        if not self.last_focused:
            self.last_focused = widget
            self.last_focused.focus()
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
