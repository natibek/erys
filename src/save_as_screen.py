from textual.app import ComposeResult
from textual.widgets import Static, DirectoryTree, Input
from textual.containers import Vertical
from textual.screen import Screen
from textual.events import Key, ScreenResume
from textual.validation import ValidationResult, Validator

from pathlib import Path
from typing import Iterable


class NotebookName(Validator):
    """Validator for notebook name."""

    def validate(self, value: str) -> ValidationResult:
        """Checks if the provided name for a noteboook has correct ipynb extension.

        Args:
            value: provided file name for notebook.

        Returns: validation result based on whether extension is correct.
        """
        ext = Path(value).suffix
        if ext == ".ipynb":
            return self.success()
        else:
            return self.failure("File extension is not .ipynb.")


class FilteredDirectoryTree(DirectoryTree):
    """Filtered directory tree containing only directories and notebook files."""

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if path.suffix == ".ipynb" or path.is_dir()]


class SaveAsScreen(Screen[str | None]):
    def __init__(self, is_notebook: bool) -> None:
        super().__init__()
        self.is_notebook = is_notebook
        if is_notebook:
            # input for file name
            self.input = Input(
                placeholder="File Name", id="save-as-input", validators=[NotebookName()]
            )
            # to help select the directory where the file can be saved at
            self.dir_tree = FilteredDirectoryTree(Path.cwd(), id="save-as-dir-tree")
        else:
            self.input = Input(
                placeholder="File Name", id="save-as-input",
            )
            self.dir_tree = DirectoryTree(Path.cwd(), id="save-as-dir-tree")

    def compose(self) -> ComposeResult:
        """Composed with:
        - Screen
            - Vertical (id=save-as)
                - Input (id=save-as-input)
                - Static (id=save-as-dir)
                - FilteredDirectoryTree (id=save-as-dir-tree)
        """
        with Vertical(id="save-as"):
            # displays the directory where the file will be saved at
            self.cur_dir = Static(f"Saving at: {Path.cwd()}", id="save-as-dir")

            yield self.cur_dir
            yield self.input
            yield self.dir_tree

    def on_mount(self) -> None:
        """Properly set directory tree path after mount."""
        self.cur_dir.update(f"Saving at: {Path.cwd()}")
        self.dir_tree.path = Path.cwd()

    def on_screen_resume(self, event: ScreenResume) -> None:
        """Screen resume event handler that resets the path for directory tree and static to pwd.

        Args:
            event: screen resume event.
        """
        self.cur_dir.update(f"Saving at: {Path.cwd()}")
        self.dir_tree.path = Path.cwd()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """File selected event handler that sets the file name for saving file to
        the name of the selected file and updates the directory where the file will be saved.

        Args:
            event: file selected event.
        """
        file_dir = event.path.parent
        self.cur_dir.update(f"Saving at: {file_dir}")

        file_name = event.path.name
        # clear and update the input widget to show selected file's file name
        self.input.clear()
        self.input.insert(file_name, 0)
        # don't propagate this event to other handlers
        event.stop()

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        """Directory selected event handler that sets the directory where
        file will be saved to the selected directory.

        Args:
            event: directory selected event.
        """
        self.dir_tree.path = event.path
        self.cur_dir.update(f"Saving at: {event.path}")
        # don't propagate this event to other handlers
        event.stop()

    def on_key(self, event: Key) -> None:
        """Key press event handler that
            - prevents event propagation for the escape, n, ctrl+k, ctrl+l, d keys
            - used backspace for navigating up a directory

        Args:
            event: key event.
        """
        match event.key:
            case "escape":
                self.dismiss(None)
                # don't propagate this event to other handlers
                event.stop()
            case "backspace" if self.app.focused == self.dir_tree:
                parent = Path(self.dir_tree.path).resolve().parent
                self.dir_tree.path = parent
                self.cur_dir.update(f"Saving at: {parent}")
            case "n" | "ctrl+k" | "ctrl+l" | "d":
                # don't propagate this event to other handlers
                event.stop()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Input submitted event handler that dismisses the screen with the file path if
        input value is valid; otherwise notifies that the input value is not a valid file name.


        Args:
            event: input submitted event.
        """
        if self.is_notebook:
            if event.validation_result.is_valid:
                file_path = self.dir_tree.path.joinpath(event.value)
                self.dismiss(file_path)
            else:
                self.notify(event.validation_result.failure_descriptions, severity="error")
        else:
            file_path = self.dir_tree.path.joinpath(event.value)
            self.dismiss(file_path)
