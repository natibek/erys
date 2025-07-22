# ***`Erys`***: Terminal Interface for Jupyter Notebooks.

![Demo](https://raw.githubusercontent.com/natibek/erys/main/data/demo.gif)

**`Erys`** is a tool for opening, creating, editing, running, interacting with, and
saving Jupyter Notebooks in the terminal as well as other text files. It uses [Textual](https://textual.textualize.io/)
for creating the interface and `jupyter_client` for executing code with kernel managers and clients.

---

## Table of Contents
- [Installation](#installation)
- [Using Erys](#using-erys)
- [App Features](#features)
- [Cell Functionalities](#cell-functionalities)
- [Key Bindings](#key-bindings)
- [Coming Features](#coming-features)
- [Contributing](#contributing)
- [License](#license)

---

## Installation:

The best way to install **`Erys`** is using [`uv`](https://github.com/astral-sh/uv):

```bash
$ uv tool install erys
```
will install it as a system wide executable tool.

Similarly, `pipx` can also be used to install **`Erys`** on the system,

```bash
$ pipx install erys
```

---

## Using `Erys`

Calling `$ erys` in the terminal without any arguments launches the application with an empty notebook.
Using the directory tree docked on the left, notebooks and other files can be loaded into the app. 
`backspace` will take you up a directory and `enter` will
go into a directory.

![Directory Tree](https://raw.githubusercontent.com/natibek/erys/main/data/directory-tree.png)

Look at the [Key Bindings](#key-bindings) section to see how to open, save, save as, and close notebooks and files.

**`Erys`** can also be called with arguments in the command line. These arguments should be paths to files. The app will
load each valid file path. If the file does not exist but the parent directory does, a new file will be opened with the
provided name.

When saving a notebook as new, the following screen is opened:

![Save as screen](https://raw.githubusercontent.com/natibek/erys/main/data/save_as_screen.png)

1. The directory that the file is being saved in is stated on the top.
1. The input field can be used to write the file name.
    1. The input field is validated on submission. Any file names that don't have the `.ipynb` extension
    are not accepted.
1. The directory tree can be used to change what directory to the save file in.
1. Selecting a file in the directory tree will update the input field to have the selected file name
and updates the path as well.

Use the up and down arrow keys within a notebook to traverse the cells. Pressing `enter` will focus
on the text area of the cell. `escape` will blur out of the text area and focus on the parent cell.
Cells have more functionality which are stated in the [Cell Key Bindings](#cell-key-bindings) section.

### SSH consideration

If using **`Erys`** over ssh, use X11 forwarding to get the rendered images and html. These two
outputs use the separate windows for rendering.

--- 

## Features:

### Opening Exising Notebooks

**`Erys`** Erys can open various notebook format versions and saves notebooks using format version 4.5.

> Do share problems with loading different notebook formats :)

> NB Format: https://nbformat.readthedocs.io/en/latest/format_description.html

### Creating Notebooks

**`Erys`** can create, edit, and save Jupyter Notebooks.

### Code Execution

**`Erys`** can execute `Python` source code in code cells. The `Python` environment in which the source code
is executed is the one in which the **`Erys`** is created. Also, if `ipykernel` is not found in the
`Python` environment, code cells can not be executed. However, the notebook can still be edited and saved.

Each notebook has its own kernel manager and kernel client. Hence, there is no leaking environment from
notebook to notebook within the application. However, all notebook opened in the same **`Erys`** process 
are in the same `Python` environment.

A running code cell can be interrupted by pressing the interrupt button `□` on the left.

### Rendering 

**`Erys`** handles terminal rendering for:
1. Markdown: Rendered with `Markdown` widget from `Textual`.
1. JSON: Rendered with `Pretty` widget from `Textual` \*.
1. Errors: Rendered with `Static` widget from `Textual` and `rich.Text` \*.
    1. ansi escaped string is converted to markup. (Some background coloring is difficult to read)

> \* When these are rendered as outputs from code execution, focus on them to get the plain text output.
> The plain text output supports copying content.

![Pretty and plain error](https://raw.githubusercontent.com/natibek/erys/main/data/pretty-plain-error.gif)

**`Erys`** parses image/png and text/html outputs from code cell execution and renders them outside of the 
terminal. Press on the `🖼 IMG` and `🖼 HTML` buttons to render them respectively. Images are rendered
using `Pillow` and html is rendered in the default browser using `webbrowser`.

![Notebook with image and html](https://raw.githubusercontent.com/natibek/erys/main/data/img-html-button.png)

![Rendering image and html](https://raw.githubusercontent.com/natibek/erys/main/data/rendering-img.png)

### Syntax Highlighting

**`Erys`** has python and markdown syntax highlighting through textual for the notebooks.

![Python syntax highlighting](https://raw.githubusercontent.com/natibek/erys/main/data/code-syntax-highlighting.png)

It also supports syntax highlighting via [tree-sitter](https://pypi.org/project/tree-sitter/) for when opening and editing files with the following extensions:

|Extension|Language|
|:-:|:-:|
|.py| Python|
|.md| Markdown|
|.yaml| Yaml|
|.sh| Bash|
|.css|Css|
|.go|Go|
|.html|Html|
|.java|Java|
|.js|Javascript|
|.json|Json|
|.rs|Rust|
|.toml|Toml|
|.xml|Xml|

--- 

## Cell Functionalities:

The `Markdown` and `Code` cells have useful features:

1. Splitting: A cell will be split with the text up to the cursor's position (not inclusive) kept in the
current cell and the text starting from the cursor's position (inclusive) used to create a new cell.

![Splitting](https://raw.githubusercontent.com/natibek/erys/main/data/splitting.gif)

1. Joining with cell before and after: A cell can be joined with the cell before or after it.

1. Merging: Multiple cells can be merged into one. Select the cells in the order they should appear in the merge
by holding down `ctrl` and selecting with the mouse. The content of first selected cell will appear first in the final merged cell. The resulting
cell wil be of the same type as the first selected cell. The cells selected for merging will be highlighted.

![Merging](https://raw.githubusercontent.com/natibek/erys/main/data/merging.gif)

1. Toggle cell type: The cell types can be swtiched back and forth.

1. Collapsing: Both cell types can be collapsed to take up less space. The `Code` cell's output can also be collapsed.

1. Moving: A cell can be moved up and down the notebook.

![Moving](https://raw.githubusercontent.com/natibek/erys/main/data/move_cell.gif)

1. Copy/Cut Paste: A cell can be copied or cut and pasted. It is pasted after the currently focused cell. 
The new cell will have a different id than the original. Cut can be undone.

1. Deleting: A cell can be deleted. Deletion can be undone.

--- 

## Key Bindings:

**`Erys`** has different sets on key bindings depending on what is in focus.

### App Key Bindings:

|Key Binding|Function|
|:-:|:-:|
|ctrl+n|New Notebook|
|ctrl+k|Close Notebook|
|ctrl+l|Clear Tabs|
|d|Toggle Directory Tree|
|ctrl+q|Quit|

### Notebook Key Bindings:

|Key Binding|Function|
|:-:|:-:|
|a| Add Cell After|
|b| Add Cell Before|
|t| Toggle Cell Type|
|ctrl+d| Delete Cell \*|
|ctrl+u| Undo Delete \*|
|ctrl+up| Move Cell Up|
|ctrl+down| Move Cell Down|
|M| Merge Cells|
|ctrl+c| Copy Cell|
|ctrl+x| Cut Cell|
|ctrl+v| Paste Cell|
|ctrl+s| Save|
|ctrl+w| Save As|

> \* A maximum of 20 deletes can be undone at a time. The stack keeping track of the deleted cells
> has a maximum size of 20.


### Cell Key Bindings:
|Key Binding|Function|
|:-:|:-:|
|c| Collapse Cell|
|ctrl+pageup| Join with Before|
|ctrl+pagedown| Join with After|

#### Additionally, for code cell

|Key Binding|Function|
|:-:|:-:|
|ctrl+r|Run Code Cell|

### Text Area Bindings:
|Key Binding|Function|
|:-:|:-:|
|ctrl+backslash|Split Cell|
|ctrl+r|Run Code Cell \*|

> \* Only for `Code` Cell.
---

## Coming Features
1. Execution time duration for code cell
1. Read config for themes and key bindings?
1. Attaching to user selected kernels
1. Raw cells
1. Saving progress backup
1. Opening from cached backup
1. Ask to save editted files on exit
1. Mime output types rendering

--- 

## Contributing

Pull requests and feedback are welcome! Create issues and PRs that can help improve and grow
the project.

--- 

## License

This project is licensed under the Apache-2.0 License. 
