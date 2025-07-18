# ***`Erys`***: Terminal Interface for Jupyter Notebook.

**`Erys`** is a terminal interface for opening, creating, editing, running, interacting with, and
saving Jupyter Notebooks in the terminal. It uses [Textual](https://textual.textualize.io/)
for creating the interface and `jupyter_client` to create kernel managers and clients to execute
code cells.

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
will install `erys` as a command line executable tool.

`pipx` can also be used to install **`Erys`** on the system,

```bash
$ pipx install erys
```

---

## Using `Erys`

Calling `$ erys` in the terminal without any arguments launches the application with an empty notebook.
Look at the [Key Bindings](#key-bindings) section to see how to open, save, save as, and close notebooks.

**`Erys`** can also be called with arguments. These arguments should be paths to jupyter notebook files
with the extension `.ipynb`. Any file path that does not have this extension is ignored. The app will
load each valid file paths into an *`erys`* notebook.

Using the directory tree docked on the left, notebooks can be loaded into the app. File types without
the `.ipynb` extension will not be opened.

When saving a notebook as new, the following screen is opened:

![Save as screen](https://raw.githubusercontent.com/natibek/erys/main/data/save_as_screen.png)

1. The directory that the file is being saved in is stated on the top.
1. The input field can be used to write the file name (must end with `.ipynb`).
    1. The input field is validated on submission. Any file names that don't have the `.ipynb` extension
    are not accepted.
1. The directory tree can be used to change what directory to the save file in.
1. Selecting a file in the directory tree will update the input field to have the selected file name
and updates the path as well.

Use the up and down arrow keys within a notebook to traverse the cells. Pressing `enter` will focus
on the text area of the cell. `escape` will blur out of the text area and focus on the parent cell.
Cells have more functionality which are stated in the [Cell Key Bindings](#cell-key-bindings) section.

### SSH consideration

If using **`Erys`** over ssh, use X11 forwarding to also get the rendered images and html. The two
use the operating systems default image opening software and the default browser to render outputs
which results in opening new windows.

--- 

## Features:

### Opening Exising Notebooks

**`Erys`** Erys can open various notebook format versions and always saves notebooks using format version 4.5.

> Do share problems with loading different notebook formats :)

> NB Format: https://nbformat.readthedocs.io/en/latest/format_description.html

### Creating Notebooks

**`Erys`** can create, edit, and save Jupyter Notebooks with the 4.5 notebook format.

### Code Execution

**`Erys`** can execute `Python` source code in code cells. The `Python` environment in which the source code
is executed is the one in which the **`Erys`** is created. Also, if `ipykernel` is not found in the
`Python` environment, no code cells can be executed. However, the notebook can still be edited and saved.

Each notebook has its own kernel manager and kernel client. Hence, there is no leaking environment from
notebook to notebook. However, all notebook opened in the same **`Erys`** process are in the same
`Python` environment.

A running code cell can be interrupted by pressing the interrupt button on the left.

### Rendering 

**`Erys`** handles terminal rendering for:
1. Markdown: Rendered with `Markdown` widget from `Textual`.
1. JSON: Rendered with `Pretty` widget from `Textual`.
1. Errors: Rendered with `Static` with `rich.Text`.
    1. ansi string is converted to markup. (Some background coloring is difficult to view)

**`Erys`** parses image/png and text/html outputs from code cell execution and renders them outside of the 
terminal. Press on the `🖼 IMG` and `🖼 HTML` buttons to render them respectively. Images are rendered
using `Pillow` and html is rendered in the default browser using `webbrowser`.

![Notebook with image and html](https://raw.githubusercontent.com/natibek/erys/main/data/img-html-button.png)

![Rendering image and html](https://raw.githubusercontent.com/natibek/erys/main/data/rendering-img.png)

### Syntax Highlighting

**`Erys`** has python and markdown syntax highlighting through textual.

![Python syntax highlighting](https://raw.githubusercontent.com/natibek/erys/main/data/code-syntax-highlighting.png)

--- 

## Cell Functionalities:

The `Markdown` and `Code` cells have useful features:

1. Splitting: A cell will be split will the text up to the cursor's position (not inclusive) kept in the
current cell and the text starting from the cursor's position used to create a new cell
that is added following the current.

1. Joining with above and below: A cell can be joined with the cell below or after it.

1. Merging: Multiple cells can be merged into one. First select the cells in the order they should appear in the merge
by holding down `ctrl` and selecting with the mouse. The content of first selected cell will appear first in the final merged cell. The resulting
cell wil be the same type as the first selected as well. The cells selected for merging will be highlighted.

1. Toggle cell type: The cell types can be swtiched back and forth.

1. Collapsing: Both cell types can be collapsed to take up less space. The `Code` cell's output can also be collapsed.

1. Moving: A cell can be moved up and down the notebook.

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
|M| Merge Cells \*\*|
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
|ctrl+pageup| Join with Above|
|ctrl+pagedown| Join with Below|

#### Additionally, for code cell

|Key Binding|Function|
|:-:|:-:|
|r| Run|

### Text Area Bindings:
|Key Binding|Function|
|:-:|:-:|
|ctrl+backslash|Split Cell|

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
1. Edit other text and code files

--- 

## Contributing

Pull requests and feedback are welcome! Create issues and PRs that can help improve and grow
the project.

--- 

## License

This project is licensed under the Apache-2.0 License. 