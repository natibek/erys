from textual.app import App, ComposeResult
from textual.widgets import (
    Footer,
    Header,
    DirectoryTree,
    Tab,
    Tabs,
    ContentSwitcher,
    Label,
    Button,
)
from textual.screen import Screen
from textual.containers import Horizontal, Vertical, Grid
from textual.events import Key

from pathlib import Path
import os.path
from argparse import ArgumentParser

from . import __version__
from .notebook import Notebook, DEFAULT_FILE_NAME
from .save_as_screen import SaveAsScreen
from .file import File


class QuitScreen(Screen):
    """Screen with a dialog to quit."""

    def compose(self) -> ComposeResult:
        """Composed with:
        - Screen
            - Grid (id=dialog)
                - Label (id=question)
                - Button (id=quit)
                - Button (id=cancel)
        """
        yield Grid(
            Label("Are you sure you want to quit?", id="question"),
            Button("Quit", variant="error", id="quit"),
            Button("Cancel", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Button pressed event handler that quits app or pops screen.

        Args:
            event: button pressed event.
        """
        if event.button.id == "quit":
            self.app.exit()
        else:
            self.app.pop_screen()

    def on_key(self, event: Key) -> None:
        """Key event handler that pops screen when escapa is pressed.

        Args:
            event: key event.
        """
        match event.key:
            case "escape":
                self.app.pop_screen()
                event.stop()


class DirectoryNav(DirectoryTree):
    """Custom directory tree with key navigation."""

    BINDINGS = [
        ("backspace", "back_dir", "Go up a directory"),
    ]
    selected_dir: str | None = None  # keep track of the selected directory

    def action_back_dir(self) -> None:
        """Moves up a directory."""
        parent = Path(self.path).resolve().parent
        self.path = parent

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        """Directory selected event handler that sets the current directory to selected.

        Args:
            event: directory selected event.
        """
        self.path = Path(event.path).resolve()


class Erys(App):
    """A Textual app for editing and running Python notebooks."""

    CSS_PATH = "./styles.tcss"
    # SCREENS = {
    #     "quit_screen": QuitScreen,
    #     "nb_save_as_screen": SaveAsScreen,
    #     "file_save_as_screen": SaveAsScreen,
    # }
    BINDINGS = [
        ("ctrl+n", "new_notebook", "New Notebook"),
        ("ctrl+k", "close", "Close Tab"),
        ("ctrl+l", "clear", "Clear Tabs"),
        ("d", "toggle_directory_tree", "Toggle Directory Tree"),
        ("ctrl+q", "push_screen('quit_screen')", "Quit"),
    ]

    def __init__(self, paths: list[str]) -> None:
        super().__init__()
        self.theme = "textual-dark"
        # check if the provided file paths are python notebooks
        self.paths = [
            os.path.relpath(path, Path.cwd())
            for path in paths
            if (Path(path).exists() or Path(path).parent.is_dir())
        ]
        self.tabs = Tabs(
            *[Tab(path, id=f"tab{idx}") for idx, path in enumerate(self.paths)]
        )
        self.cur_tab = len(paths)
        self.path_to_tab_id: dict[str, int] = {}  # maps from tab id to notebook id
        
        self.dir_tree = DirectoryNav(Path.cwd(), id="file-tree")
        self.switcher = ContentSwitcher(id="tab-content")

    def compose(self) -> ComposeResult:
        """Composed with:
        - App
            - Header
            - Horizontal
                - DirectoryNav (id=file-tree)
                - Vertical
                    - Tabs
                    - ContentSwitcher (id=tab-content)
                        - Notebook
            - Footer
        """

        yield Header(show_clock=True, time_format="%I:%M:%S %p")

        with Horizontal():
            yield self.dir_tree

            with Vertical():
                yield self.tabs
                with self.switcher:
                    for idx, path in enumerate(self.paths):
                        self.path_to_tab_id[path] = f"tab{idx}"
                        if Path(path).suffix == ".ipynb":
                            yield Notebook(path, f"tab{idx}", self)
                        else:
                            yield File(path, f"tab{idx}", self)

        yield Footer()

    def on_mount(self) -> None:
        """Mount event handler that creates a new notebook if none are opened when app starts,
        then focuses on the tabs.
        """
        self.install_screen(QuitScreen, "quit_screen")
        self.install_screen(lambda: SaveAsScreen(is_notebook=True), "nb_save_as_screen")
        self.install_screen(lambda: SaveAsScreen(is_notebook=False), "file_save_as_screen")

        if len(self.paths) == 0:
            self.dir_tree.display = True
            self.dir_tree.focus()
        else:
            self.dir_tree.display = False
            self.tabs.active = f"tab{self.cur_tab - 1}"

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Tab activated event handler that switches content to show notebook the tab belongs to.

        Args:
            event: tab activated event.
        """
        if event.tab is None or str(event.tab.label) not in self.path_to_tab_id:
            pass
        else:
            file_id = self.path_to_tab_id[str(event.tab.label)]
            self.switcher.current = f"{file_id}"

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """File selected event handler that opens notebook or file.

        Args:
            event: file selected event.
        """
        self.open_file(event.path)

    def on_key(self, event: Key) -> None:
        """Key event handler that
            - moves focus to the Tabs when escape is pressed
            - moves focus to latest Notebook when enter is pressed (and tabs was focused on)

        Args:
            event: key event.
        """
        match event.key:
            case "escape":
                self.set_focus(self.tabs)
            case "enter":
                if not self.switcher.current:
                    return

                # if currently focused on the tabs, change focus to the latest notebook
                if isinstance(self.app.focused, Tabs):
                    file = self.switcher.query_one(f"#{self.switcher.current}", Notebook | File)
                    file.focus_file()

    def action_toggle_directory_tree(self) -> None:
        """Toggle whether the directory tree is displayed."""
        self.dir_tree.display = not self.dir_tree.display
        if self.dir_tree.display:
            self.set_focus(self.dir_tree)
        elif cur_file := self.switcher.current:
            file = self.switcher.query_one(f"#{cur_file}", Notebook | File)
            file.focus_file()
        else:
            self.set_focus(self.tabs)

    def action_new_notebook(self) -> None:
        """Create a new notebook with the path set to `DEFAULT_FILE_NAME{self.cur_tab}`."""
        # for a new notebook the notebook id is the same as the tab id
        tab_id = f"tab{self.cur_tab}"
        # add a new tab
        self.notebook_path = f"{DEFAULT_FILE_NAME}{self.cur_tab}"
        self.tabs.add_tab(Tab(self.notebook_path, id=tab_id))
        self.path_to_tab_id[self.notebook_path] = tab_id

        new_notebook = Notebook(self.notebook_path, tab_id, self)
        self.switcher.mount(new_notebook)

        # set the new tab to be the active one
        # no need to change what is the current notebook since that will be set by the
        # tab activated event handler
        self.tabs.active = tab_id
        self.cur_tab += 1

    def action_close(self) -> None:
        """Remove active tab."""
        active_tab = self.tabs.active_tab
        self.remove_tab(active_tab.label)

    def action_clear(self) -> None:
        """Clear the tabs."""
        self.tabs.clear()
        for child in self.switcher.children:
            child.remove()

        # clear the map and the switcher's currently displayed widget to avoid errors
        self.path_to_tab_id = {}
        self.switcher.current = None

    def change_tab_name(self, tab_id: str, new_path: str) -> None:
        """Update the key in the map from path to tab id when a saved is saved as new.
        
        Args:
            tab_id: the tab id for the notebook with the new path.
            new_path: the new path for the file.
        """
        if tab_id not in self.path_to_tab_id:
            pass

        path = os.path.relpath(new_path, Path.cwd())
        target_tab: Tab = self.tabs.query_one(f"#{tab_id}", Tab)

        del self.path_to_tab_id[target_tab.label]

        target_tab.update(path)
        self.path_to_tab_id[path] = tab_id
        
        # reload the directory tree
        self.dir_tree.path = self.dir_tree.path

    def remove_tab(self, nb_path: str) -> None:
        """Deletes tab belonging to notebook with path `nb_path`.

        Args:
            nb_path: path of the notebook whose tab is being removed.
        """
        # if a tab is active then remove it and the notebook
        tab_id = self.path_to_tab_id[nb_path]
        target_tab: Tab = self.tabs.query_one(f"#{tab_id}", Tab)

        if target_tab is not None:
            self.tabs.remove_tab(target_tab.id)
            self.switcher.remove_children(f"#{tab_id}")
            del self.path_to_tab_id[target_tab.label]

        # set the switcher's currently displayed widget to none to avoid errors
        if len(self.path_to_tab_id) == 0:
            self.switcher.current = None

    def open_file(self, path: Path) -> None:
        """Open a file. Either change tabs to the file if it is already loaded or 
        create a new file (notebook or regular) in a new tab and swtich to that tab.
        
        Args:
            path: path to the file.
        """
        path = os.path.relpath(path, Path.cwd())

        if path in self.path_to_tab_id:
            self.tabs.active = self.path_to_tab_id[path]
            return

        tab_id = f"tab{self.cur_tab}"

        if Path(path).suffix == ".ipynb":
            new_file = Notebook(path, tab_id, self)
        else:
            new_file = File(path, tab_id, self)

        self.tabs.add_tab(Tab(path, id=tab_id))

        self.tabs.active = tab_id

        self.switcher.mount(new_file)
        self.path_to_tab_id[path] = tab_id
        self.cur_tab += 1


def main():
    parser = ArgumentParser(
        "erys",
        description="Terminal Interface for Jupyter Notebooks."
    )

    parser.add_argument("notebooks", nargs="*", help="One or more notebooks to open", type=Path)
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()

    app = Erys(args.notebooks)
    app.run()


if __name__ == "__main__":
    main()
