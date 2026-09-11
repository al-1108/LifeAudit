# LifeAudit

A Python desktop activity tracker built with PySide6. Account for every hour spent.

## Setup

Install Python 3, then open a terminal in the project folder.

**macOS / Linux**
```sh
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (Command Prompt)**
```bat
py -m venv .venv
.venv\Scripts\activate.bat
```

Install the dependency and launch the app:
```sh
python -m pip install PySide6
python main.py
```

For future launches, activate the virtual environment and run `python main.py` from the project folder. Activities are saved locally to `data/activities.json`, created automatically.
