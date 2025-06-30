from textual.widgets import TextArea
from textual.events import Key

MIN_HEIGHT = 4


class ExpandingTextArea(TextArea):
    def on_key(self, event: Key) -> None:
        match event.key:
            case "escape":
                pass
            case "enter":
                cur_height = self.styles.height.cells
                self.styles.height = max(MIN_HEIGHT, cur_height + 1)
            case "backspace":
                if self.cursor_at_start_of_line:
                    cur_height = self.styles.height.cells
                    self.styles.height = max(MIN_HEIGHT, cur_height - 1)