from textual.app import ComposeResult
from textual.widgets import Static, DirectoryTree, Input
from textual.containers import Vertical
from textual.screen import Screen
from textual.events import Key, ScreenResume
from pathlib import Path
from typing import Iterable
from textual.validation import ValidationResult, Validator


class NotebookName(Validator):
    def validate(self, value: str) -> ValidationResult:
        ext = Path(value).suffix
        if ext == ".ipynb":
            return self.success()
        else:
            return self.failure("File extension is not .ipynb.")


class FilteredDirectoryTree(DirectoryTree):
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if path.suffix == ".ipynb" or path.is_dir()]


class SaveAsScreen(Screen[str | None]):
    def compose(self) -> ComposeResult:
        with Vertical(id="save-as"):
            self.input = Input(
                placeholder="File Name", id="save-as-input", validators=[NotebookName()]
            )
            self.cur_dir = Static(f"Saving at: {Path.cwd()}", id="save-as-dir")
            self.dir_tree = FilteredDirectoryTree(Path.cwd(), id="save-as-dir-tree")

            yield self.cur_dir
            yield self.input
            yield self.dir_tree

    def on_screen_resume(self, event: ScreenResume) -> None:
        self.cur_dir.update(f"Saving at: {Path.cwd()}")
        self.dir_tree.path = Path.cwd()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        file_dir = event.path.parent
        self.cur_dir.update(f"Saving at: {file_dir}")

        file_name = event.path.name
        self.input.clear()
        self.input.insert(file_name, 0)
        event.stop()

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        self.dir_tree.path = event.path
        self.cur_dir.update(f"Saving at: {event.path}")
        event.stop()

    def on_key(self, event: Key) -> None:
        match event.key:
            case "escape":
                self.dismiss(None)
                event.stop()
            case "backspace" if self.app.focused == self.dir_tree:
                parent = Path(self.dir_tree.path).resolve().parent
                self.dir_tree.path = parent
                self.cur_dir.update(f"Saving at: {parent}")
            case "n" | "ctrl+k" | "ctrl+l" | "d":
                event.stop()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.validation_result.is_valid:
            file_path = self.dir_tree.path.joinpath(event.value)
            self.dismiss(file_path)
        else:
            self.notify(event.validation_result.failure_descriptions, severity="error")
