import sys
import os
import json
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton
)
from PySide6.QtCore import QTimer


class LifeAudit(QWidget):
    def __init__(self):
        super().__init__()

        self.start_time = None
        self.task_label = QLabel("Currently: ---")

        if os.path.exists("data/activities.json"):
            with open("data/activities.json", "r") as f:
                data = json.load(f)
            if data:
                self.start_time = datetime.fromisoformat(data[-1]["start"])
                self.task_label.setText(f"Currently: {data[-1]['activity']}")
                self.setWindowTitle(f"Currently: {data[-1]['activity']}")
            else:
                self.setWindowTitle("LifeAudit")
        else:
            self.setWindowTitle("LifeAudit")
        
        self.resize(400, 250)

        layout = QVBoxLayout()

        title = QLabel("What are you doing?")
        layout.addWidget(title)

        self.activity_input = QLineEdit()
        self.activity_input.setPlaceholderText("e.g. Doing calculus")
        layout.addWidget(self.activity_input)

        category_label = QLabel("Category")
        layout.addWidget(category_label)

        self.category_dropdown = QComboBox()
        self.category_dropdown.addItems([
            "rest",
            "study",
            "work",
            "productivity",
            "social",
            "not being productive",
            "eat",
            "void"
            # void --> not tracked
        ])
        layout.addWidget(self.category_dropdown)

        self.start_button = QPushButton("Start Activity")
        self.start_button.clicked.connect(self.start_activity)
        layout.addWidget(self.start_button)

        self.start_label = QLabel("Time started: ---")
        self.elapsed_label = QLabel("Time elapsed: ---")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        layout.addWidget(self.task_label)
        layout.addWidget(self.start_label)
        layout.addWidget(self.elapsed_label)

        self.update_time()

        self.setLayout(layout)

    def start_activity(self):
        activity = self.activity_input.text().strip()
        if not activity:
            return

        category = self.category_dropdown.currentText()

        self.start_time = datetime.now()
        self.task_label.setText(f"Currently: {activity}")
        self.setWindowTitle(f"Currently: {activity}")

        timestamp = self.start_time.isoformat()

        data = {
            "activity": activity,
            "category": category,
            "start": timestamp,
            "end": None
        }

        if not os.path.exists("data/activities.json"):
            os.makedirs("data", exist_ok=True)
            with open("data/activities.json", "w") as f:
                json.dump([], f)

        with open("data/activities.json", "r") as f:
            activities = json.load(f)

        activities.append(data)
        if len(activities) > 1:
            activities[-2]["end"] = timestamp

        with open("data/activities.json", "w") as f:
            json.dump(activities, f, indent=4)

        self.activity_input.clear()

    def update_time(self):
        if self.start_time:
            self.start_label.setText(f"Time started: {self.start_time.strftime('%H:%M:%S')}")

            elapsed = datetime.now() - self.start_time

            total_seconds = int(elapsed.total_seconds())

            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            self.elapsed_label.setText(
                f"Time elapsed: {hours:02}:{minutes:02}:{seconds:02}"
            )
        else:
            self.start_label.setText("Time started: ---")
            self.elapsed_label.setText("Time elapsed: ---")




app = QApplication(sys.argv)

window = LifeAudit()
window.show()

sys.exit(app.exec())