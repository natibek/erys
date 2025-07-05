from textual.app import App, ComposeResult
from textual.widgets import (
    Footer,
    Header,
    DirectoryTree,
    Tab,
    Tabs,
    ContentSwitcher,
    Label,
)
from pathlib import Path
import os.path

from textual.reactive import reactive
from textual.containers import Horizontal, Vertical
from notebook import Notebook
from textual.events import Key
import sys


class Directory(DirectoryTree):
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

    BINDINGS = [
        ("n", "add", "New Notebook"),
        ("ctrl+k", "close", "Close Notebook"),
        ("ctrl+l", "clear", "Clear Tabs"),
        ("d", "toggle_directory_tree", "Toggle Directory Tree"),
    ]
    tab_id = reactive("")

    def __init__(self, paths: list[str]) -> None:
        super().__init__()
        self.theme = "dracula"
        self.paths = [os.path.relpath(path, Path.cwd()) for path in paths]
        self.cur_tab = len(paths)
        self.tab_to_nb_id_map: dict[str, int] = {}

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""

        yield Header(show_clock=True, time_format="%I:%M:%S %p")

        with Horizontal():
            self.dir_tree = Directory(Path.cwd(), id="file-tree")
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
                        yield Notebook(path, f"tab{idx}")

        yield Footer()

    def on_mount(self) -> None:
        """Focus the tabs when the app starts."""
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
        path = os.path.relpath(event.path, Path.cwd())

        if path in self.tab_to_nb_id_map:
            self.tabs.active = self.tab_to_nb_id_map[path]
            return

        tab_id = f"tab{self.cur_tab}"
        self.tabs.add_tab(Tab(path, id=tab_id))
        self.tab_to_nb_id_map[path] = tab_id

        new_notebook = Notebook(path, tab_id)
        self.switcher.mount(new_notebook)

        self.cur_tab += 1
        self.tabs.active = tab_id

    def on_key(self, event: Key) -> None:
        match event.key:
            case "escape":
                self.set_focus(self.tabs)
            case "enter":
                if isinstance(self.app.focused, Tabs):
                    notebook = self.switcher.query_one(
                        f"#{self.switcher.current}", Notebook
                    )
                    self.call_after_refresh(notebook.cell_container.focus)

    def action_toggle_directory_tree(self) -> None:
        self.dir_tree.display = not self.dir_tree.display
        if self.dir_tree.display:
            self.set_focus(self.dir_tree)
        else:
            self.set_focus(None)

    def action_add(self) -> None:
        tab_id = f"tab{self.cur_tab}"
        self.tabs.add_tab(Tab(tab_id, id=tab_id))
        self.tab_to_nb_id_map[tab_id] = tab_id

        new_notebook = Notebook("new_empty_terminal_notebook", tab_id)
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

    def action_clear(self) -> None:
        """Clear the tabs."""
        self.tabs.clear()
        for child in self.switcher.children:
            child.remove()
        self.tab_to_nb_id_map = {}


if __name__ == "__main__":
    app = TerminalNotebook(sys.argv[1:])
    app.run()
