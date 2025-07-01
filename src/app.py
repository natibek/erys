from textual.app import App, ComposeResult
from textual.widgets import (
    Footer,
    Header,
    DirectoryTree,
    Collapsible,
    Tabs,
    ContentSwitcher,
    Label,
)
from textual.containers import Container, Vertical
from notebook import Notebook
from textual.events import Key
import sys

NAMES = [
    "Paul Atreidies",
    "Duke Leto Atreides",
    "Lady Jessica",
    "Gurney Halleck",
    "Baron Vladimir Harkonnen",
    "Glossu Rabban",
    "Chani",
    "Silgar",
]


class DirectorySideBar(Container):
    def compose(self) -> ComposeResult:
        # with Collapsible(id="tree-panel"):
        # yield DirectoryTree(".", id="file-tree")
        with Vertical(id="tree-sidebar"):
            with Collapsible(id="tree-panel"):
                yield DirectoryTree(".", id="file-tree")


class TerminalNotebook(App):
    """A Textual app to manage stopwatches."""

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("n", "add", "New Notebook"),
        ("ctrl+r", "clear", "Clear Tabs"),
        ("ctrl+s", "save", "Save"),
        ("ctrl+S", "save_as", "Save As"),
        ("ctrl+k", "close", "Close Notebook"),
    ]

    def __init__(self, paths: list[str]) -> None:
        super().__init__()
        self.theme = "dracula"
        self.paths = paths
        self.cur_tab = len(paths)
        self.tab_to_nb_id_map: dict[str, int] = {}

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        # yield DirectorySideBar()

        yield Header(show_clock=True)

        with Vertical():
            yield Tabs(*[path for path in self.paths])
            with ContentSwitcher(id="tab-content"):
                for idx, path in enumerate(self.paths):
                    self.tab_to_nb_id_map[path] = f"tab{idx}"
                    yield Notebook(path, f"tab{idx}")

        yield Footer()

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle TabActivated message sent by Tabs."""
        switcher = self.query_one("#tab-content", ContentSwitcher)
        if event.tab is None:
            # When the tabs are cleared, event.tab will be None
            pass
        elif event.tab.label in self.tab_to_nb_id_map:
            switcher.current = f"{self.tab_to_nb_id_map[event.tab.label]}"
        else:
            tab_id = event.tab.label
            new_notebook = Notebook("new_empty_termimal_notebook", f"{tab_id}")
            switcher.mount(new_notebook)
            switcher.current = f"{tab_id}"
            self.tab_to_nb_id_map[f"{tab_id}"] = tab_id

    def on_mount(self) -> None:
        """Focus the tabs when the app starts."""
        self.query_one(Tabs).focus()

    def action_add(self) -> None:
        tabs = self.query_one(Tabs)
        tabs.add_tab(f"tab{self.cur_tab}")
        self.cur_tab += 1

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

    def on_key(self, event: Key) -> None:
        match event.key:
            case "escape":
                self.set_focus(None)


if __name__ == "__main__":
    app = TerminalNotebook(sys.argv[1:])
    app.run()
