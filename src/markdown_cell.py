from textual.app import ComposeResult
from textual.widgets import Markdown, TextArea, ContentSwitcher, Label, Static
from textual.events import Key, MouseDown, Enter, Leave
from textual.containers import HorizontalGroup
from typing import Any
from time import time
from utils import get_cell_id, DOUBLE_CLICK_INTERVAL, COLLAPSED_COLOR, EXPANDED_COLOR
from textual.reactive import var
import pyperclip

PLACEHOLDER = "*Empty markdown cell, double-click or press enter to edit.*"

class MarkdownCollapseLabel(Label):
    collapsed = var(False, init=False)

    def __init__(self, collapsed: bool = False, id: str = "") -> None:
        super().__init__("\n┃\n┃", id=id)
        self.collapsed = collapsed
        self.prev_switcher = None

    def on_click(self) -> None:
        self.collapsed = not self.collapsed

    def watch_collapsed(self, collapsed) -> None:
        markdown_cell: MarkdownCell = self.parent

        if collapsed:
            placeholder = self.get_placeholder(markdown_cell.text_area.text)
            markdown_cell.collapsed_markdown.update(f"{placeholder}...")

            self.prev_switcher = markdown_cell.switcher.current
            markdown_cell.switcher.current = "collapsed-markdown"

            self.styles.color = COLLAPSED_COLOR
            self.update("┃")
        else:
            markdown_cell.switcher.current = self.prev_switcher or "markdown"
            self.styles.color = EXPANDED_COLOR
            self.update("\n┃\n┃")

    def get_placeholder(self, text: str) -> str:
        split = text.splitlines()
        if len(split) == 0:
            return ""

        for line in split:
            if line != "":
                return line

class CopyTextAreaMarkdown(TextArea):
    BINDINGS = [
        ("ctrl+backslash", "split_cell", "Split Cell")
    ]

    def on_key(self, event: Key) -> None:
        match event.key:
            case "ctrl+c":
                pyperclip.copy(self.selected_text)
            case "escape":
                markdown_cell: MarkdownCell = self.parent.parent
                markdown_cell.render_markdown()
                markdown_cell.focus()
                event.stop()

    def action_split_cell(self):
        markdown_cell: MarkdownCell = self.parent.parent
        string_to_keep = self.get_text_range((0,0), self.cursor_location)
        string_for_new_cell = self.text[len(string_to_keep):]
        self.load_text(string_to_keep)
        new_cell = MarkdownCell(markdown_cell.notebook, string_for_new_cell)
        markdown_cell.notebook.cell_container.mount(new_cell, after=markdown_cell)
        markdown_cell.notebook.connect_widget(new_cell)


class FocusMarkdown(Markdown):
    can_focus = True

class MarkdownCell(HorizontalGroup):
    merge_select = var(False, init=False)
    can_focus = True
    _last_click_time: float = 0.0
    next = None
    prev = None
    cell_type = "markdown"

    BINDINGS = [
        ("c", "collapse", "Collapse Cell"),
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

    def compose(self) -> ComposeResult:
        self.collapse_btn = MarkdownCollapseLabel(
            collapsed=self._collapsed, id="markdown-collapse-button"
        ).with_tooltip("Collapse")

        yield self.collapse_btn

        self.switcher = ContentSwitcher(initial="markdown", id="raw-text")
        with self.switcher:
            self.collapsed_markdown = Static("Collapsed Markdown...", id="collapsed-markdown")
            self.text_area = CopyTextAreaMarkdown.code_editor(self.source, id="raw-text", language="markdown", show_line_numbers=False)
            self.markdown = FocusMarkdown(self.source, id="markdown")
            yield self.collapsed_markdown
            yield self.text_area
            yield self.markdown

    def _on_focus(self):
        self.styles.border_left = "solid", "lightblue"
        # self.styles.border = "solid", "lightblue"
        # self.border_subtitle = "Markdown"
    
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

    async def on_key(self, event: Key) -> None:
        match event.key:
            case "enter":
                await self.open()

    def on_mouse_down(self, event: MouseDown) -> None:
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

    def on_double_click(self, event: MouseDown) -> None:
        if self.switcher.current == "markdown":
            self.switcher.current = "raw-text"

    def action_collapse(self) -> None:
        self.collapse_btn.collapsed = not self.collapse_btn.collapsed

    def watch_merge_select(self, selected: bool) -> None:
        if selected:
            self.styles.border_left = "solid", "yellow"
        else:
            self.styles.border_left = None

    def render_markdown(self) -> None:
        self.source = self.text_area.text
        # if not self.source:
        #     self.markdown.update(PLACEHOLDER)
        # else:
        self.markdown.update(self.source)
        self.switcher.current = "markdown"

    def disconnect(self): #-> tuple[str]:
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

    @staticmethod
    def from_nb(nb: dict[str, Any], notebook) -> "MarkdownCell":
        assert nb
        for key in ["cell_type", "metadata", "source"]:
            assert key in nb
        assert nb["cell_type"] == "markdown"

        source = nb["source"]
        if isinstance(source, list):
            source = "".join(source)

        return MarkdownCell(
            notebook=notebook,
            source=source,
            metadata=nb["metadata"],
            cell_id=nb.get("id"),
        )

    def to_nb(self) -> dict[str, Any]:
        """
        Format for Markdown cell
        {
            "cell_type" : "markdown",
            "metadata" : {},
            "source" : ["some *markdown*"],
        }
        """
        return {
            "cell_type": "markdown",
            "metadata": self._metadata,
            "source": self.text_area.text,
            "id": self._cell_id,
        }

    def clone(self, connect: bool = True) -> "MarkdownCell":
        clone = MarkdownCell(
            notebook=self.notebook,
            source = self.text_area.text,
            metadata = self._metadata,
            cell_id = self._cell_id,
        )
        if connect:
            clone.next = self.next
            clone.prev = self.prev
        return clone

    def set_new_id(self) -> None:
        self._cell_id = get_cell_id()

    def show_markdown(self):
        self.switcher.current = "markdown"

    async def open(self):
        self.switcher.current = "raw-text"
        self.call_after_refresh(self.text_area.focus)

    def merge_cells_with_self(self, cells) -> None:
        """Merge self with a list of cells by combining content in text areas into self. Should be
        called by the first selected cell in the the cells to merge. The resulting type will be 
        self.
        
        Args:
            cells: List of MarkdownCell | CodeCell to merge with self.
        """
        source = self.text_area.text

        for cell in cells:
            source += "\n"
            match cell.cell_type:
                case "code":
                    source += cell.code_area.text
                case "markdown":
                    source += cell.text_area.text
            cell. disconnect()
            cell.remove()
        self.text_area.load_text(source)
        self.focus()