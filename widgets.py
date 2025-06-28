from textual.widgets import Markdown, TextArea, ContentSwitcher, Collapsible
from textual.events import Key

PLACEHOLDER = "*Empty markdown cell, double-click or press enter to edit.*"
MIN_HEIGHT = 4

class FocusMarkdown(Markdown):
    can_focus = True

    def on_mount(self) -> None:
        if self.size == 0:
            self.update(PLACEHOLDER)

class ExpandingTextArea(TextArea):
    def on_key(self, event: Key) -> None:
        match event.key:
            case "enter":
                cur_height = self.styles.height.cells
                self.styles.height = max(MIN_HEIGHT, cur_height + 1)
            case "backspace":
                if self.cursor_at_start_of_line:
                    cur_height = self.styles.height.cells
                    self.styles.height = max(MIN_HEIGHT, cur_height - 1)