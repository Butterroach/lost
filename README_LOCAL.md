<p align="center"><img src="logo.png" height="256"/></p>

<h1 align="center"><a href="https://github.com/Butterroach/lost">Lost</a></h1>

Lost is a lightweight Linux hosts manager made in Python and QT6.

## Features

-   You can add sources
-   You can update your sources
-   You can remove your sources
-   ...that's pretty much all you need (no it doesn't include auto updating that's stupid!!!
    you shouldn't leave updates of stuff like that unattended!!! who wants broken internet cuz that one program you installed 2 weeks ago went rogue????)

## How to install

1. Download the source code of the [latest release](https://github.com/Butterroach/lost/releases/latest). Do NOT download the repo as a zip or git clone.
2. Extract the archive into a directory.
3. Go into the directory with a terminal.
4. Create a venv: `python3 -m venv .venv`.
5. Activate the venv: `source .venv/bin/activate`.
6. Make sure to unset any aliases that take the name `pip`, `python`, `python3`, etc.. (`unalias pip`, `unalias python`, `unalias python3`, etc..)
7. Install the requirements: `pip install -r requirements.txt`. This'll take a bit. Make sure you got good internet.
8. Run `pyside6-uic form.ui -o ui_form.py` to generate `ui_form.py`.

You're done installing.

## How to run

`sudo .venv/bin/python app.py`

Lost needs root to run. Don't run it without `sudo`.

## How to update

Just download the source code of the [latest release](https://github.com/Butterroach/lost/releases/latest), extract into a new dir, and move the .venv folder from the old dir to the new one.

You can delete the old dir after confirming the new version works.

## How to contribute

Fork the repo and make your changes! (Make sure you can Git and code Python)

For changing the UI: Use Design mode in QT Creator (open the form.ui file).

For changing the code: QT Creator is terrible for Python. Use VS Code instead of QT Creator.

After doing whatever you did, open a pull request with a detailed changelog of what you did. I'll review it.

Btw, PLEASE have clear commit messages!!!!

## License

Lost is licensed under the GNU GPL v3, or (at your option) any later version. See the LICENSE file for more info.
