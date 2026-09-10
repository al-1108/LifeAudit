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
    QPushButton,
)


class LifeAudit(QWidget):
    def __init__(self):
        super().__init__()

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
            "goon"
        ])
        layout.addWidget(self.category_dropdown)

        self.start_button = QPushButton("Start Activity")
        self.start_button.clicked.connect(self.start_activity)
        

        layout.addWidget(self.start_button)

        self.setLayout(layout)

    def start_activity(self):
        activity = self.activity_input.text().strip()

        if not activity:
            return
    
        activity = self.activity_input.text()
        category = self.category_dropdown.currentText()
        timestamp = datetime.now().isoformat()
        print(f"Activity: {activity}")
        print(f"Category: {category}")
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
            




app = QApplication(sys.argv)

window = LifeAudit()
window.show()

sys.exit(app.exec())