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

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        self.path = Path(event.path).resolve()

class TerminalNotebook(App):
    """A Textual app to manage stopwatches."""

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("n", "add", "New Notebook"),
        ("ctrl+s", "save", "Save"),
        ("ctrl+S", "save_as", "Save As"),
        ("ctrl+k", "close", "Close Notebook"),
        ("ctrl+l", "clear", "Clear Tabs"),
        ("d", "toggle_directory_tree", "Toggle Directory Tree")
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
            yield Directory(Path.cwd(), id="file-tree")
            with Vertical():
                yield Tabs(*[Tab(path, id=f"tab{idx}") for idx,path in enumerate(self.paths)])
                with ContentSwitcher(id="tab-content"):
                    for idx, path in enumerate(self.paths):
                        self.tab_to_nb_id_map[path] = f"tab{idx}"
                        yield Notebook(path, f"tab{idx}")

        yield Footer()

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle TabActivated message sent by Tabs."""
        switcher = self.query_one("#tab-content", ContentSwitcher)
        if event.tab is None:
            pass
        else:
            notebook_id = self.tab_to_nb_id_map[str(event.tab.label)]
            switcher.current = f"{notebook_id}"

    def on_mount(self) -> None:
        """Focus the tabs when the app starts."""
        self.query_one(Tabs).focus()
        self.query_one(DirectoryTree).display = False

    def action_toggle_directory_tree(self) -> None:
        dir = self.query_one(DirectoryTree)
        dir.display = not dir.display
        if dir.display: self.set_focus(dir)
        else: self.set_focus(None)

    def action_add(self) -> None:
        tabs = self.query_one(Tabs)
        tab_id = f"tab{self.cur_tab}"
        tabs.add_tab(Tab(tab_id, id=tab_id))
        self.tab_to_nb_id_map[tab_id] = tab_id

        new_notebook = Notebook("new_empty_termimal_notebook", tab_id)
        switcher = self.query_one("#tab-content", ContentSwitcher)
        switcher.mount(new_notebook)

        tabs.active = tab_id
        self.cur_tab += 1

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        tabs = self.query_one(Tabs)
        path = os.path.relpath(event.path, Path.cwd())

        if path in self.tab_to_nb_id_map:
            tabs.active = self.tab_to_nb_id_map[path]
            return

        tab_id = f"tab{self.cur_tab}"
        tabs.add_tab(Tab(path, id=tab_id))
        self.tab_to_nb_id_map[path] = tab_id

        new_notebook = Notebook(path, tab_id)
        switcher = self.query_one("#tab-content", ContentSwitcher)
        switcher.mount(new_notebook)

        self.cur_tab += 1 
        tabs.active = tab_id

    def action_close(self) -> None:
        """Remove active tab."""
        tabs = self.query_one(Tabs)
        active_tab = tabs.active_tab
        if active_tab is not None:
            tabs.remove_tab(active_tab.id)
            notebook_id = self.tab_to_nb_id_map[active_tab.label]
            switcher = self.query_one("#tab-content", ContentSwitcher)
            switcher.remove_children(f"#{notebook_id}")
            del self.tab_to_nb_id_map[active_tab.label]

    def action_clear(self) -> None:
        """Clear the tabs."""
        self.query_one(Tabs).clear()
        for child in self.query_one("#tab-content", ContentSwitcher).children:
            child.remove()
        self.tab_to_nb_id_map = {}

    def on_key(self, event: Key) -> None:
        match event.key:
            case "escape":
                self.set_focus(None)


if __name__ == "__main__":
    app = TerminalNotebook(sys.argv[1:])
    app.run()
