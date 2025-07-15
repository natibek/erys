from textual.widgets import TextArea, Label, ContentSwitcher, Static
from textual.events import MouseDown, Key, Enter, Leave
from textual.reactive import var
from textual.containers import VerticalGroup

import re
import pyperclip
from typing import Any
import uuid

COLLAPSED_COLOR = "green"
EXPANDED_COLOR = "white"

# https://github.com/jupyter/enhancement-proposals/blob/master/62-cell-id/cell-id.md
def get_cell_id(id_length=8):
    return uuid.uuid4().hex[:id_length]

class CollapseLabel(Label):
    collapsed = var(False, init=False)

    def __init__(self, parent_cell: "Cell", collapsed: bool = False, id: str = "") -> None:
        super().__init__("\n┃\n┃", id=id)
        self.collapsed = collapsed
        self.parent_cell: Cell = parent_cell
        self.prev_switcher = None

    def on_click(self) -> None:
        self.collapsed = not self.collapsed

    def watch_collapsed(self, collapsed) -> None:
        if collapsed:
            placeholder = self.get_placeholder(self.parent_cell.input_text.text)
            self.parent_cell.collapsed_display.update(f"{placeholder}...")
            self.prev_switcher = self.parent_cell.switcher.current

            self.parent_cell.switcher.current = "collapsed-display"

            if self.parent_cell.cell_type == "code":
                self.parent_cell.exec_count_display.display = False

            self.styles.color = COLLAPSED_COLOR
            self.update("\n┃")
        else:
            self.parent_cell.switcher.current = self.prev_switcher

            if self.parent_cell.cell_type == "code":
                self.parent_cell.exec_count_display.display = True

            self.styles.color = EXPANDED_COLOR
            self.update("\n┃\n┃")

    def get_placeholder(self, text: str) -> str:
        split = text.splitlines()
        if len(split) == 0:
            return ""

        for line in split:
            if line != "":
                return line
class CopyTextArea(TextArea):
    def on_key(self, event: Key):
        match event.key:
            case "ctrl+c":
                pyperclip.copy(self.selected_text)

class SplitTextArea(CopyTextArea):
    BINDINGS = [
        ("ctrl+backslash", "split_cell", "Split Cell")
    ]
    def on_key(self, event: Key):
        match event.key:
            case "ctrl+c":
                pyperclip.copy(self.selected_text)
            case "escape":
                cell: Cell = self.parent.parent.parent
                cell.escape(event)
    
    def action_split_cell(self):
        cell: Cell = self.parent.parent.parent
        string_to_keep = self.get_text_range((0,0), self.cursor_location)
        string_for_new_cell = self.text[len(string_to_keep):]
        self.load_text(string_to_keep)
        new_cell = cell.create_cell(string_for_new_cell)
        cell.notebook.cell_container.mount(new_cell, after=cell)
        cell.notebook.connect_widget(new_cell)

class Cell(VerticalGroup):
    can_focus = True
    merge_select: bool = var(False, init=False)
    next = None
    prev = None

    cell_type = ""

    BINDINGS = [
        ("c", "collapse", "Collapse Cell"),
        ("ctrl+pageup", "join_above", "Join with Above"),
        ("ctrl+pagedown", "join_below", "Join with Below"),
    ]

    def __init__(
        self,
        notebook,
        source: str = "",
        metadata: dict[str, Any] = {},
        cell_id: str | None = None,
    ) -> None:
        super().__init__()
        self.notebook = notebook
        self.source = source
        self._metadata = metadata
        self._cell_id = cell_id or get_cell_id()
        self._collapsed = metadata.get("collapsed", False)

        self.collapse_btn = CollapseLabel(
            self, collapsed=self._collapsed, id="collapse-button"
        ).with_tooltip("Collapse")

        self.switcher = ContentSwitcher(
            id="collapse-content", initial="text"
        )
        self.collapsed_display = Static("", id="collapsed-display")

    async def on_key(self, event: Key) -> None:
        match event.key:
            case "enter":
                await self.open()

    def _on_focus(self):
        self.styles.border_left = "solid", "lightblue"
        # self.styles.border = "solid", "lightblue"
        # self.border_subtitle = self._language

    def _on_blur(self):
        if not self.merge_select:
            self.styles.border = None

    def on_enter(self, event: Enter) -> None:
        if self.merge_select: return

        if self.notebook.last_focused != self:
            self.styles.border_left = "solid", "grey"

    def on_leave(self, event: Leave) -> None:
        if self.merge_select: return

        if self.notebook.last_focused != self:
            self.styles.border_left = None

    def on_mouse_down(self, event: MouseDown) -> None:
        if event.ctrl:
            if not self.merge_select:
                self.notebook._merge_list.append(self)
            else:
                self.notebook._merge_list.remove(self)

            self.merge_select = not self.merge_select

    def watch_merge_select(self, selected: bool) -> None:
        if selected:
            self.styles.border_left = "solid", "yellow"
        else:
            self.styles.border_left = None

    def action_join_above(self) -> None:
        if self.prev:
            self.prev.merge_cells_with_self([self])

    def action_join_below(self) -> None:
        if self.next:
            self.merge_cells_with_self([self.next])

    def disconnect(self) -> tuple["Cell", str]:
        """Remove self from the linked list of cells. Update the pointers of the surrounding cells 
        to point to each other.

        Returns: The next cell to focus on and there was relative to the removed cell
        """
        last_focused = None
        position = "after"
        if prev := self.prev:
            last_focused = prev
            prev.next = self.next
            position = "before"

        if next := self.next:
            last_focused = next
            next.prev = self.prev

        return last_focused, position

    def set_new_id(self) -> None:
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

    def escape(self, event: Key) -> None:
        raise NotImplementedError()

    def from_nb(nb: dict[str, Any], notebook) -> "Cell":
        raise NotImplementedError()

    def to_nb(self) -> dict[str, Any]:
        raise NotImplementedError()

    def create_cell(self, str: str) -> "Cell":
        raise NotImplementedError()

    def clone(self, connect: bool = True):
        raise NotImplementedError()
