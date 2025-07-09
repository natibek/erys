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
from pathlib import Path
import os.path

from save_as_screen import SaveAsScreen
from textual.screen import Screen
from textual.reactive import reactive
from textual.containers import Horizontal, Vertical, Grid
from notebook import Notebook
from textual.events import Key
import sys


class QuitScreen(Screen):
    """Screen with a dialog to quit."""

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Are you sure you want to quit?", id="question"),
            Button("Quit", variant="error", id="quit"),
            Button("Cancel", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
        else:
            self.app.pop_screen()

    def on_key(self, event: Key) -> None:
        match event.key:
            case "escape":
                self.app.pop_screen()
                event.stop()


class DirectoryNav(DirectoryTree):
    BINDINGS = [
        ("backspace", "back_dir", "Go back up directory"),
    ]
    selected_dir: str | None = None

    def action_back_dir(self) -> None:
        parent = Path(self.path).resolve().parent
        self.path = parent

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        self.path = Path(event.path).resolve()


class TerminalNotebook(App):
    """A Textual app to manage stopwatches."""

    CSS_PATH = "styles.tcss"
    SCREENS = {"quit_screen": QuitScreen, "save_as_screen": SaveAsScreen}
    BINDINGS = [
        ("n", "new_notebook", "New Notebook"),
        ("ctrl+k", "close", "Close Notebook"),
        ("ctrl+l", "clear", "Clear Tabs"),
        ("d", "toggle_directory_tree", "Toggle Directory Tree"),
        ("ctrl+q", "push_screen('quit_screen')", "Quit"),
    ]

    tab_id = reactive("")

    def __init__(self, paths: list[str]) -> None:
        super().__init__()
        self.theme = "dracula"
        self.paths = [
            os.path.relpath(path, Path.cwd())
            for path in paths
            if Path(path).is_file() and Path(path).suffix == ".ipynb"
        ]
        self.cur_tab = len(paths)
        self.tab_to_nb_id_map: dict[str, int] = {}

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""

        yield Header(show_clock=True, time_format="%I:%M:%S %p")

        with Horizontal():
            self.dir_tree = DirectoryNav(Path.cwd(), id="file-tree")
            yield self.dir_tree

            with Vertical():
                self.tabs = Tabs(
                    *[Tab(path, id=f"tab{idx}") for idx, path in enumerate(self.paths)]
                )
                yield self.tabs
                self.switcher = ContentSwitcher(id="tab-content")
                with self.switcher:
                    for idx, path in enumerate(self.paths):
                        self.tab_to_nb_id_map[path] = f"tab{idx}"
                        yield Notebook(path, f"tab{idx}", self)

        yield Footer()

    def on_mount(self) -> None:
        """Focus the tabs when the app starts."""
        if len(self.paths) == 0:
            self.action_new_notebook()

        self.tabs.focus()
        self.dir_tree.display = False

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle TabActivated message sent by Tabs."""
        if event.tab is None:
            pass
        else:
            notebook_id = self.tab_to_nb_id_map[str(event.tab.label)]
            self.switcher.current = f"{notebook_id}"

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        if not os.path.exists(event.path):
            self.notify(f"{event.path} does not exist.", severity="error", timeout=8)
            return

        if event.path.suffix != ".ipynb":
            self.notify(
                f"{event.path} is not a jupyter notebook.", severity="error", timeout=8
            )
            return

        self.open_notebook(event.path)

    def on_key(self, event: Key) -> None:
        match event.key:
            case "escape":
                self.set_focus(self.tabs)
            case "enter":
                if not self.switcher.current:
                    return

                if isinstance(self.app.focused, Tabs):
                    notebook = self.switcher.query_one(
                        f"#{self.switcher.current}", Notebook
                    )
                    self.call_next(notebook.focus_notebook)

    def action_toggle_directory_tree(self) -> None:
        self.dir_tree.display = not self.dir_tree.display
        if self.dir_tree.display:
            self.set_focus(self.dir_tree)
        else:
            self.set_focus(self.tabs)

    def action_new_notebook(self) -> None:
        tab_id = f"tab{self.cur_tab}"
        self.tabs.add_tab(Tab(tab_id, id=tab_id))
        self.tab_to_nb_id_map[tab_id] = tab_id

        new_notebook = Notebook("new_empty_terminal_notebook", tab_id, self)
        self.switcher.mount(new_notebook)

        self.tabs.active = tab_id
        self.cur_tab += 1

    def action_close(self) -> None:
        """Remove active tab."""
        active_tab = self.tabs.active_tab
        # TODO: ask for save
        if active_tab is not None:
            self.tabs.remove_tab(active_tab.id)
            notebook_id = self.tab_to_nb_id_map[active_tab.label]
            self.switcher.remove_children(f"#{notebook_id}")
            del self.tab_to_nb_id_map[active_tab.label]

        if len(self.tab_to_nb_id_map) == 0:
            self.switcher.current = None

    def action_clear(self) -> None:
        """Clear the tabs."""
        self.tabs.clear()
        for child in self.switcher.children:
            child.remove()
        self.tab_to_nb_id_map = {}
        self.switcher.current = None

    def open_notebook(self, path: Path) -> None:
        path = os.path.relpath(path, Path.cwd())

        if path in self.tab_to_nb_id_map:
            self.tabs.active = self.tab_to_nb_id_map[path]
            return

        tab_id = f"tab{self.cur_tab}"

        new_notebook = Notebook(path, tab_id, self)
        self.tabs.add_tab(Tab(path, id=tab_id))

        self.tabs.active = tab_id

        self.switcher.mount(new_notebook)
        self.tab_to_nb_id_map[path] = tab_id
        self.cur_tab += 1


if __name__ == "__main__":
    app = TerminalNotebook(sys.argv[1:])
    app.run()
