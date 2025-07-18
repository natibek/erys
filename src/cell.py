from textual.widgets import TextArea, Label, Static
from textual.events import MouseDown, Key, Enter, Leave
from textual.reactive import var
from textual.containers import VerticalGroup
from textual.binding import Binding

from time import time
import pyperclip
from typing import Any
import uuid

DOUBLE_CLICK_INTERVAL = 0.4  # Threshold for interval between mousedown in seconds
COLLAPSED_COLOR = "green"
EXPANDED_COLOR = "white"


# https://github.com/jupyter/enhancement-proposals/blob/master/62-cell-id/cell-id.md
def get_cell_id(id_length=8):
    """Generate the cell id for cells in notebook."""
    return uuid.uuid4().hex[:id_length]


class StaticBtn(Static):
    """Widget to use as button instead of textual's `Button`."""

    def on_enter(self, event: Enter):
        """Add left border when hovering over."""
        self.styles.border_left = "solid", "gray"

    def on_leave(self, event: Leave):
        """Remove borders when mouse leaves."""
        self.styles.border = None


class CollapseLabel(Label):
    """Custom label to use as the collapse button for a cell."""

    collapsed = var(False, init=False)  # keep track of collapse state

    def __init__(
        self, parent_cell: "Cell", collapsed: bool = False, id: str = ""
    ) -> None:
        super().__init__("\n┃\n┃", id=id)
        self.collapsed = collapsed
        self.parent_cell: Cell = parent_cell
        self.prev_switcher = None

    def on_click(self) -> None:
        """Toggle the collapsed state on clicks."""
        self.collapsed = not self.collapsed

    def watch_collapsed(self, collapsed) -> None:
        """Watched method to switch the content from the input text area for cell
        to the collapsed label.

        Args:
            collapsed: updated collapsed state.
        """
        if collapsed:
            # get the placeholder from the input text and set the collapsed display to it
            placeholder = self.get_placeholder(self.parent_cell.input_text.text)
            self.parent_cell.collapsed_display.update(f"{placeholder}...")
            self.prev_switcher = self.parent_cell.switcher.current

            self.parent_cell.switcher.current = "collapsed-display"

            if (
                self.parent_cell.cell_type == "code"
            ):  # if code cell, hide the execution count
                self.parent_cell.exec_count_display.display = False

            self.styles.color = COLLAPSED_COLOR
            self.update("\n┃")
        else:
            # set the switcher to the previous widget it was displaying
            self.parent_cell.switcher.current = self.prev_switcher

            if (
                self.parent_cell.cell_type == "code"
            ):  # if code cell, display the execution count
                self.parent_cell.exec_count_display.display = True

            self.styles.color = EXPANDED_COLOR
            self.update("\n┃\n┃")

    def get_placeholder(self, text: str) -> str:
        """Get the placeholder to represent the cell's text area. Either the first line or an
        empty string.

        Args:
            text: the content of the input text

        Returns: placeholder representing the collapsed input text.
        """
        split = text.splitlines()
        if len(split) == 0:
            return ""

        for line in split:
            if line != "":
                return line


class CopyTextArea(TextArea):
    """Widget to contain text that can be copied."""

    def on_key(self, event: Key) -> None:
        """Key event handler to copy selected text to system clipboard when ctrl+c is pressed."""
        match event.key:
            case "ctrl+c":
                pyperclip.copy(self.selected_text)


class SplitTextArea(CopyTextArea):
    """Widget to contain text that can be split."""

    BINDINGS = [
        ("ctrl+backslash", "split_cell", "Split Cell")
    ]

    def on_key(self, event: Key) -> None:
        """Key event handler. Copy selected text to system clipboard. Call escape event handler
        for the parent cell.

        Args:
            event: Key event.
        """
        match event.key:
            case "ctrl+c":
                pyperclip.copy(self.selected_text)
            case "escape":
                cell: Cell = self.parent.parent.parent
                cell.escape(event)

    def action_split_cell(self) -> None:
        """Creates new cell of the same type as parent."""

        # parent cell containing widget
        cell: Cell = self.parent.parent.parent
        string_to_keep = self.get_text_range((0, 0), self.cursor_location)
        string_for_new_cell = self.text[len(string_to_keep) :]

        self.load_text(string_to_keep)

        # create and mount new cell of the same type as we are spliting from
        new_cell = cell.create_cell(string_for_new_cell)
        cell.notebook.cell_container.mount(new_cell, after=cell)
        # connect the new cell to the cells next and before it
        cell.notebook.connect_widget(new_cell)


class Cell(VerticalGroup):
    """Base class for the markdown and code cell."""

    can_focus = True
    _last_click_time: float = 0.0  # keep track of the last mouse click
    merge_select: bool = var(False, init=False)  # whether cell is selected for merging

    # pointers to the next and prevous cells in the notebook
    next = None
    prev = None

    # name of the cell type
    cell_type = ""

    BINDINGS = [
        Binding("c", "collapse", "Collapse Cell", False),
        Binding("ctrl+pageup", "join_above", "Join with Before", False),
        Binding("ctrl+pagedown", "join_below", "Join with After", False),
    ]

    def __init__(
        self,
        notebook,
        source: str,
        language: str,
        metadata: dict[str, Any] = {},
        cell_id: str | None = None,
    ) -> None:
        super().__init__()
        self.notebook = notebook  # notebook cell belongs to
        self.source = source
        self._metadata = metadata
        self._cell_id = cell_id or get_cell_id()
        self.id = f"_{self._cell_id}"
        self._collapsed = metadata.get("collapsed", False)
        self._language = language

        self.collapse_btn = CollapseLabel(
            self, collapsed=self._collapsed, id="collapse-button"
        ).with_tooltip("Collapse")

        self.collapsed_display = Static("", id="collapsed-display")

    async def on_key(self, event: Key) -> None:
        """Key press event handler to 'open' the `Cell` when enter is pressed.

        Args:
            event: Key press event.
        """
        match event.key:
            case "enter":
                await self.open()

    def _on_focus(self):
        """Focus event handler that adds border."""
        if not self.merge_select:
            self.styles.border_left = "solid", "lightblue"
        # self.styles.border = "solid", "lightblue"
        # self.border_subtitle = self._language

    def _on_blur(self):
        """Blur event handler that removes border if not selected for merge."""
        if not self.merge_select:
            self.styles.border = None

    def on_enter(self, event: Enter) -> None:
        """Mouse enter event handler that adds border if not selected for merge and not focused."""
        if self.merge_select:
            return

        if self.notebook.last_focused != self:
            self.styles.border_left = "solid", "grey"

    def on_leave(self, event: Leave) -> None:
        """Mouse leave event handler that removes border if not selected for merge and not focused."""
        if self.merge_select:
            return

        if self.notebook.last_focused != self:
            self.styles.border_left = None

    def on_mouse_down(self, event: MouseDown) -> None:
        """Mouse down event handler. Add cell to the merge list if ctrl is held. If the time
        between mouse down event is below the threshold, call the double click event handler.

        Args:
            event: MouseDown event.
        """
        now = time()
        if event.ctrl:
            if not self.merge_select:
                self.notebook._merge_list.append(self)
            else:
                self.notebook._merge_list.remove(self)

            self.merge_select = not self.merge_select
        elif now - self._last_click_time <= DOUBLE_CLICK_INTERVAL:
            self.on_double_click(event)
        self._last_click_time = now

    def watch_merge_select(self, selected: bool) -> None:
        """Watcher method that updates the border of the cell depending on whether it is selected
        for merging.

        Args:
            selected: whether cell is selected for merging.
        """
        if selected:
            self.styles.border_left = "solid", "yellow"
        else:
            self.styles.border_left = None

    def action_join_above(self) -> None:
        """Merges cell with the previous cell."""
        if self.prev:
            self.prev.merge_cells_with_self([self])

    def action_join_below(self) -> None:
        """Merges cell with the next cell."""
        if self.next:
            self.merge_cells_with_self([self.next])

    def disconnect(self) -> tuple["Cell", str]:
        """Remove self from the linked list of cells. Update the pointers of the surrounding cells
        to point to each other.

        Returns: The next cell to focus on and where the removed cell was relative to it.
        """
        next_focus = None
        position = "after"
        if prev := self.prev:
            next_focus = prev
            position = "after"
            prev.next = self.next

        if next := self.next:
            next_focus = next
            position = "before"
            next.prev = self.prev

        return next_focus, position

    def set_new_id(self) -> None:
        """Update cell id with a new uuid."""
        self._cell_id = get_cell_id()

    def merge_cells_with_self(self, cells) -> None:
        """Merge self with a list of cells by combining content in text areas into self. Should be
        called by the first selected cell in the the cells to merge. The resulting type will be
        self.

        Args:
            cells: List of MarkdownCell | CodeCell to merge with self.
        """
        source = self.input_text.text

        for cell in cells:
            source += "\n"
            source += cell.input_text.text
            cell.disconnect()
            cell.remove()

        self.input_text.load_text(source)
        self.focus()

    def on_double_click(self, event: MouseDown) -> None:
        """Double click event handler."""
        pass

    def escape(self, event: Key) -> None:
        """Event handler for the escape key."""
        raise NotImplementedError()

    @staticmethod
    def from_nb(nb: dict[str, Any], notebook) -> "Cell":
        """Static method to generate a `Cell` from a json/dict that represent a cell."""
        raise NotImplementedError()

    def to_nb(self) -> dict[str, Any]:
        """Static method to generate a `Cell` from a json/dict that represent a cell."""
        raise NotImplementedError()

    def create_cell(self, str: str) -> "Cell":
        """Returns a `CodeCell` with a source. Used for splitting cell."""
        raise NotImplementedError()

    def clone(self, connect: bool = True):
        """Clone a code cell. Used for cut/paste."""
        raise NotImplementedError()
