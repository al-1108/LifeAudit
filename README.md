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

To correct a late activity switch, click **Edit times** beside today's timeline. Select a transition (including earlier days), enter the actual date and time down to the second, and save. The earlier activity's end and the next activity's start move together, so no tracked time is lost or counted twice. The new time must fall within the two activities. If you forgot to switch, start the next activity first, then correct its transition time.
