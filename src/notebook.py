from textual.app import ComposeResult
from textual.widgets import Button, TextArea
from textual.containers import HorizontalGroup, VerticalScroll, Container
from textual.events import Key, DescendantFocus

from typing import Any
import json

from markdown_cell import MarkdownCell, FocusMarkdown
from code_cell import CodeCell, CodeArea, OutputText, OutputJson, OutputError
from cell import CopyTextArea
from notebook_kernel import NotebookKernel


class ButtonRow(HorizontalGroup):
    """Buttton row on top of Notebook"""

    def compose(self) -> ComposeResult:
        """Composed with:
        - HorizontalGroup
            - Button (id=add-code-cell)
            - Button (id=add-markdown-cell)
            - Button (id=run-before)
            - Button (id=run-after)
            - Button (id=run-all)
            - Button (id=restart-shell)

        """
        yield Button("➕ Code", id="add-code-cell")
        yield Button("➕ Markdown", id="add-markdown-cell")
        yield Button("▲ Run Before", id="run-before")
        yield Button("▼ Run After", id="run-after")
        # yield Button("▶ ↑ Run Before", id="run-before")
        # yield Button("▶ ↓ Run After", id="run-after")
        yield Button("▶ Run All", id="run-all")
        yield Button("🔁 Restart", id="restart-shell")
        yield Button("Switch Cell Type", id="switch-cell-type")


class Notebook(Container):
    """Container representing a notebook."""

    last_focused: CodeCell | MarkdownCell | None = None  # keep track of the last focused cell
    last_copied: CodeCell | MarkdownCell | None = None  # keep track of the copied/cut cell
    _delete_stack = []
    _merge_list: list[CodeCell | MarkdownCell] = []  # list of the cells to be merged.

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
        """Composed with:
        - Container
            - ButtonRow
            - VerticalScroll (id=cell-container)
                - Cell
        """
        yield ButtonRow()
        self.cell_container = VerticalScroll(id="cell-container")
        yield self.cell_container

    def on_mount(self) -> None:
        """Mount event handler that loads a notebook if path is provided."""
        if self.path != "new_empty_terminal_notebook":
            self.call_after_refresh(self.load_notebook)

        self.call_after_refresh(self.focus_notebook)

    def on_unmount(self) -> None:
        """Unmount event handler that shuts down kernel if avaialble."""
        if self.notebook_kernel:
            self.notebook_kernel.shutdown_kernel()

    def on_descendant_focus(self, event: DescendantFocus) -> None:
        """Descendant focus event handler that assigns the last focused cell depending on what
        widget is being focused on. Chooses the parent cell of the widget being currently focused
        on.

        Args:
            event: descendant focus event.
        """
        # Ignore buttons
        if isinstance(event.widget, CodeCell) or isinstance(event.widget, MarkdownCell):
            self.last_focused = event.widget
        elif any(
            isinstance(event.widget, widgetType)
            for widgetType in [OutputJson, OutputText, OutputError]
        ) or event.widget.id in ["pretty-error-output", "plain-error-output"]:
            self.last_focused = event.widget.parent.parent.parent.parent
        elif any(
            isinstance(event.widget, widgetType)
            for widgetType in [FocusMarkdown, CopyTextArea, CodeArea]
        ):
            self.last_focused = event.widget.parent.parent.parent

    def on_key(self, event: Key) -> None:
        """Key event handler that
            - disables tab and shift+tab for changing focus,
            - clears merge list when escape is presed
            - moves focus between cells using up and down arrows.

        Args:
            event: key event.
        """
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
        """Button pressed event handler for button row on top of notebook.

        Args:
            event: button pressed event.
        """
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
                # if any of the run buttons are pressed check if there is a notebook kernel
                if not self.notebook_kernel:
                    self.notify(
                        "No kernel available for notebook.", severity="error", timeout=8
                    )
                    self.last_focused.focus()
                    return
            case "run-all":
                await self.run_all_cells()
            case "run-after":
                await self.run_cells_after()
            case "run-before":
                await self.run_cells_before()
            case "switch-cell-type":
                await self.switch_cell_type()

    async def action_add_cell_after(self) -> None:
        """Add code cell after current cell."""
        await self.add_cell(CodeCell, self.last_focused, "after")

    async def action_add_cell_before(self) -> None:
        """Add code cell before current cell."""
        await self.add_cell(CodeCell, self.last_focused, "before")

    def action_save_as(self) -> str:
        """Save notebook as a new file."""

        def check_save_as(path: str | None) -> None:
            """Callback function to save notebook if save as screen dismisses successfully.

            Args:
                path: string if save as screen dismisses with a file path chosen
                    to save notebook at.
            """
            if path:
                self.path = path
                # notify after successfuly serializing and saving notebook
                self.save_notebook(path)
                self.notify(f"{self.path} saved!")
                # open the saved notebook
                self.term_app.open_notebook(path)

        # push the save as screen with the above callback function
        self.app.push_screen("save_as_screen", check_save_as)

    def action_save(self) -> None:
        """Save notebook."""
        # notebooks with path 'new_empty_terminal_notebook' were created by terminal-notebook
        # need save_as call to get file name
        if self.path == "new_empty_terminal_notebook":
            self.action_save_as()
        else:
            # notify after successfuly serializing and saving notebook
            self.save_notebook(self.path)
            self.notify(f"{self.path} saved!")

    def action_delete_cell(self) -> None:
        """Delete cell."""
        if not self.last_focused:
            return

        # disconnect the cell from surrounding cells and find new cell to focus on
        last_focused, position = self.last_focused.disconnect()

        # add it to the `delete_stack` for undoing
        # self.delete_stack.append(
        #     (self.last_focused.clone(connect=False), position, last_focused.id)
        # )

        # remove cell
        self.call_after_refresh(self.last_focused.remove)
        self.last_focused = last_focused

        if self.last_focused:
            self.last_focused.focus()

    def action_copy_cell(self) -> None:
        """Copy cell."""
        if not self.last_focused:
            return
        # store serialized representation of copied cell
        self.last_copied = self.last_focused.to_nb()

    def action_cut_cell(self) -> None:
        """Cut cell."""
        if not self.last_focused:
            return

        # store serialized representation of cut cell and delete it
        self.last_copied = self.last_focused.to_nb()
        self.action_delete_cell()

    async def action_paste_cell(self) -> None:
        """Paste cut/copied cell."""
        if not self.last_copied:
            return

        # generate the `MarkdownCell` or `CodeCell` from the stored serialized copy.
        match self.last_copied["cell_type"]:
            case "markdown":
                widget = MarkdownCell.from_nb(self.last_copied, self)
            case "code":
                widget = CodeCell.from_nb(self.last_copied, self)

        widget.set_new_id()  # update id to avoid conflict during copy/paste
        # mount and connect the widget
        await self.cell_container.mount(widget, after=self.last_focused)
        self.connect_widget(widget)

    async def action_move_up(self) -> None:
        """Move the cell up."""
        if not self.last_focused:
            return

        if self.last_focused.prev:
            # clone the cell
            clone = self.last_focused.clone()
            prev = clone.prev

            # removes the cell from linked list
            prev.next = clone.next
            if clone.next:
                clone.next.prev = prev

            if prev.prev:
                prev.prev.next = clone

            clone.prev = prev.prev
            clone.next = prev
            prev.prev = clone

            # remove the original cell
            self.last_focused.remove()

            # mount the new cloned cell in the new position
            await self.cell_container.mount(clone, before=clone.next)

            self.last_focused = clone
            self.last_focused.focus()

    async def action_move_down(self) -> None:
        """Move the cell down."""
        if not self.last_focused:
            return

        if self.last_focused.next:
            # clone the cell
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

            # mount the new cloned cell in the new position
            await self.cell_container.mount(clone, after=clone.prev)

            # removes the cell from linked list
            self.last_focused.remove()
            self.last_focused = clone
            self.last_focused.focus()

    def action_merge_cells(self) -> None:
        """Merge selected cells by combining content in text areas into the one selected. Should be
        called by the first selected cell in the the cells to merge. The resulting type will be
        of the first selected's type.
        """
        if len(self._merge_list) < 2:
            return
        target: CodeCell | MarkdownCell = self._merge_list[0]
        target.merge_cells_with_self(self._merge_list[1:])
        target.merge_select = False
        self._merge_list = []

    async def run_all_cells(self) -> None:
        """Run all code cells."""
        # iterate over all the code cells and run them
        for cell in self.cell_container.children:
            if isinstance(cell, CodeCell):
                await cell.run_cell()
        self.last_focused.focus()

    async def run_cells_after(self) -> None:
        """Run code cells after currently focused cell (inclusive)."""
        if not self.last_focused:
            return

        # iterate over all the code cells starting from (including) the current and run them
        cell = self.last_focused
        while cell:
            if isinstance(cell, CodeCell):
                await cell.run_cell()
            cell = cell.next
        self.last_focused.focus()

    async def run_cells_before(self) -> None:
        """Run code cells before currently focused cell (not inclusive)."""
        if not self.last_focused:
            return
        # iterate over all the code cells up to (not including) the current and run them
        for cell in self.cell_container.children:
            if cell == self.last_focused:
                break
            if isinstance(cell, CodeCell):
                await cell.run_cell()
        self.last_focused.focus()
    
    async def switch_cell_type(self) -> None:
        """Swtich the cell type keeping the input text source."""
        if not self.last_focused:
            return

        # get the source in the input text of the cell
        src = self.last_focused.input_text.text
        # get the type to swtich to and construct object
        new_cell_type = MarkdownCell if isinstance(self.last_focused, CodeCell) else CodeCell
        new_cell = new_cell_type(self, src)

        # easiest solution is to mount after the cell that is switching then deleting the original
        await self.cell_container.mount(new_cell, after=self.last_focused)
        self.connect_widget(new_cell)

        self.last_focused.disconnect()
        self.call_after_refresh(self.last_focused.remove)
        self.last_focused = new_cell
        self.last_focused.focus()

    def focus_notebook(self) -> None:
        """Defines what focusing on a notebook does. If there is a cell that was last focused,
        focus on it; otherwise, focus on the `cell_container`.
        """
        if self.last_focused:
            self.call_after_refresh(self.last_focused.focus)
        else:
            self.call_after_refresh(self.cell_container.focus)

    def save_notebook(self, path: str) -> None:
        """Saves the notebook to the provided path.

        Args:
            path: file path to save notebook at.
        """
        nb = self.to_nb()
        with open(path, "w") as nb_file:
            json.dump(nb, nb_file)

    def load_notebook(self) -> None:
        """Load notebook from a file. Iterate through the cells and generate the `CodeCell` and
        `MarkdownCell` objects from the serialized formats and mount them to the `cell_container`.
        """
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
        self,
        cell_type: CodeCell | MarkdownCell,
        relative_to: CodeCell | MarkdownCell | None,
        position: str = "after",
        **cell_kwargs,
    ) -> CodeCell | MarkdownCell:
        """Add a cell by creating object of `cell_type` with arguments `cell_kwargs` with position
        `position` relative to the widget `relative_to`.

        Args:
            cell_type: the type of the cell being added.
            relative_to: what cell if any it should be added relative to.
            position: where in relation to the focused cell to connect the widget 'after', 'before'.
            **cell_kwargs: key word arguments to use to create the cell.
        """
        kwargs = {position: relative_to}

        widget = cell_type(self, **cell_kwargs)

        await self.cell_container.mount(widget, **kwargs)
        self.connect_widget(widget, position)

        return widget

    def connect_widget(
        self, widget: CodeCell | MarkdownCell, position: str = "after"
    ) -> None:
        """Connect the cell (widget) after or before the `last_focused` cell.

        Args:
            widget: the widget being connected.
            position: where in relation to the focused cell to connect the widget 'after', 'before'.
        """
        if (
            not self.last_focused
        ):  # if no cell has been focused on, set the new cell as the focused
            self.last_focused = widget
            self.last_focused.focus()

        # if positioning after last focused, add widget between last_focused and last_focused.next
        elif position == "after":
            next = self.last_focused.next
            self.last_focused.next = widget
            widget.next = next
            widget.prev = self.last_focused

            if next:
                next.prev = widget

        # if positioning before last focused, add widget between last_focused and last_focused.prev
        elif position == "before":
            prev = self.last_focused.prev
            self.last_focused.prev = widget
            widget.next = self.last_focused
            widget.prev = prev

            if prev:
                prev.next = widget

    def to_nb(self) -> dict[str, Any]:
        """Serialize the `Notebook` to notebook format. Format for notebook is:
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

        Returns: serialized notebook in notebook format.
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
