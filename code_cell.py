from textual.app import ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup
from widgets import ExpandingTextArea
from typing import Any
from utils import generate_id

class OutputCell(ExpandingTextArea):
    def on_mount(self) -> None:
        self.disabled = True

class CodeCell(ExpandingTextArea):
    def __init__(
            self, 
            source: str = "",
            output: str =  "",
            metadata: dict[str, Any] = {},
            cell_id: str | None = None,
        ) -> None:
        super().__init__()
        self.source = source
        self.output = output
        self.metadata = metadata
        self.id = cell_id or generate_id()

    def compose(self) -> ComposeResult:
        ExpandingTextArea.code_editor(self.source, language="python"),


class CodeCell(VerticalGroup):
    pass    
