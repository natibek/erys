from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Key
from pathlib import Path
from .cell import CopyTextArea


extension_to_language: dict[str, str] = {
    ".py": "python",
    ".md": "markdown",
    ".yaml": "yaml",
    ".sh": "bash",
    ".css":"css",
    ".go":"go",
    ".html":"html",
    ".java":"java",
    ".js":"javascript",
    ".json":"json",
    ".rs":"rust",
    ".toml":"toml",
    ".xml":"xml",
}

class FileEditor(CopyTextArea):
    def on_key(self, event: Key) -> None:
        """Handle key press event for saving and saving as.

        Args:
            event: the Key event. 
        """
        file: File = self.parent
        match event.key:
            case "ctrl+s":
                file.save_file(file.path)
                event.stop()
            case "ctrl+w":
                file.save_as_file()
                event.stop()


class File(Container):
    """Widget for rendering and editing contents of non-notebook files."""
    def __init__(self, path: str, id: str, term_app) -> None:
        super().__init__(id=id)

        self.path = Path(path)
        self.language = extension_to_language.get(self.path.suffix, None)
        self.source = ""

        self.input_text = FileEditor.code_editor(
            self.source,
            language=self.language,
            id="file-text",
            soft_wrap=True,
            theme="vscode_dark",
        )

        self.term_app = term_app

    def compose(self) -> ComposeResult:
        """Composed with:
        - Container
            - CopyTextArea (id=file-text)
        """
        yield self.input_text

    def on_mount(self) -> None:
        """Load the file if the path exists. Otherwise, create the file where it is."""
        if self.path.exists():
            self.call_after_refresh(self.load_file)

        self.call_next(self.focus_file)

    def save_as_file(self) -> str:
        """Save notebook as a new file."""

        def check_save_as(path: Path | None) -> None:
            """Callback function to save notebook if save as screen dismisses successfully.

            Args:
                path: string if save as screen dismisses with a file path chosen
                    to save notebook at.
            """
            if path:
                self.path = path
                # notify after successfuly serializing and saving notebook
                self.save_file(path)
                self.notify(f"{self.path} saved!")
                # open the saved notebook
                
                # change the tab name
                self.term_app.change_tab_name(self.id, self.path)

        # push the save as screen with the above callback function
        self.app.push_screen("file_save_as_screen", check_save_as)

    def save_file(self, path: str) -> None:
        """Saves the file to the provided path.

        Args:
            path: file path to save file at.
        """
        self.source = self.input_text.text
        with open(path, "w") as f:
            f.write(self.source)
        self.notify(f"{self.path} saved!")

    def load_file(self) -> None:
        """Load contents of a file from a path to the editor."""
        with open(self.path, "r") as f:
            try:
                # if the json decoding fails then the notebook is bad
                self.source = f.read()
                self.input_text.text = self.source
            except UnicodeDecodeError:
                self.notify(f"Failed to read {self.path}.", severity="error")
                self.term_app.remove_tab(str(self.path))
                return

    def focus_file(self) -> None:
        """Focus on the editor area."""
        self.call_next(self.input_text.focus)