import sys
import os
import json
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QScrollArea
)
from PySide6.QtCore import Qt, QTimer


class ActivityCard(QWidget):
    """One timeline entry, showing the activity's duration within this day."""

    def __init__(self, activity, day_start, day_end, now, parent=None):
        super().__init__(parent)
        self.activity = activity
        self.start = datetime.fromisoformat(activity["start"])
        self.end = (
            datetime.fromisoformat(activity["end"])
            if activity["end"] is not None else None
        )
        self.day_start = day_start
        self.day_end = day_end
        self.setObjectName("ActivityCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#ActivityCard { background: #ffffff; border-radius: 10px; }
            QWidget#ActivityCard QLabel { background: transparent; border: none; }
            QLabel#timelineTime { color: #64748b; font-size: 12px; }
            QLabel#timelineDot { color: #6366f1; font-size: 16px; }
            QFrame#timelineLine { background: #e2e8f0; border: none; }
            QLabel#activityName { color: #0f172a; font-size: 14px; font-weight: 600; }
            QLabel#activityDetails { color: #64748b; font-size: 12px; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 0)
        layout.setSpacing(12)

        time_label = QLabel(self.start.strftime("%I:%M %p"))
        time_label.setObjectName("timelineTime")
        layout.addWidget(time_label, 0, Qt.AlignmentFlag.AlignTop)

        rail = QVBoxLayout()
        rail.setSpacing(4)
        dot = QLabel("●")
        dot.setObjectName("timelineDot")
        rail.addWidget(dot, 0, Qt.AlignmentFlag.AlignHCenter)
        line = QFrame()
        line.setObjectName("timelineLine")
        line.setFixedWidth(2)
        line.setMinimumHeight(26)
        rail.addWidget(line, 1, Qt.AlignmentFlag.AlignHCenter)
        layout.addLayout(rail)

        content = QVBoxLayout()
        content.setSpacing(4)
        content.setContentsMargins(0, 0, 0, 14)
        name = QLabel(activity["activity"])
        name.setTextFormat(Qt.TextFormat.PlainText)
        name.setObjectName("activityName")
        name.setWordWrap(True)
        content.addWidget(name)
        self.details_label = QLabel()
        self.details_label.setTextFormat(Qt.TextFormat.PlainText)
        self.details_label.setObjectName("activityDetails")
        self.details_label.setWordWrap(True)
        content.addWidget(self.details_label)
        content.addStretch()
        layout.addLayout(content, 1)
        self.update_duration(now)

    def update_duration(self, now):
        # Only count the part of this activity inside the displayed day.
        start = max(self.start, self.day_start)
        end = min(self.end if self.end is not None else now, self.day_end)
        minutes = max(0, int((end - start).total_seconds()) // 60)
        hours, minutes = divmod(minutes, 60)
        duration = f"{hours}h {minutes}m" if hours else f"{minutes}m"
        running = " · currently doing" if self.end is None else ""
        self.details_label.setText(
            f"{self.activity['category']} · {duration}{running}"
        )


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
        
        self.resize(500, 650)

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
            "hygiene"
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

        timeline_title = QLabel("Today's timeline")
        timeline_title.setStyleSheet("font-size: 16px; font-weight: 600; margin-top: 16px;")
        layout.addWidget(timeline_title)

        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(True)
        self.timeline_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.timeline_scroll.setMinimumHeight(180)
        timeline_content = QWidget()
        timeline_content.setObjectName("timelineContent")
        timeline_content.setStyleSheet("QWidget#timelineContent { background: #f1f5f9; }")
        self.timeline_layout = QVBoxLayout(timeline_content)
        self.timeline_layout.setContentsMargins(8, 8, 8, 8)
        self.timeline_layout.setSpacing(6)
        self.timeline_scroll.setWidget(timeline_content)
        layout.addWidget(self.timeline_scroll, 1)

        self.load_timeline()
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
        self.load_timeline()
        self.update_time()

    def load_timeline(self):
        now = datetime.now()
        self.timeline_date = now.date()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        # Remove both cards/labels and the trailing layout spacer.
        while self.timeline_layout.count():
            item = self.timeline_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()
        self.running_cards = []

        activities = []
        if os.path.exists("data/activities.json"):
            with open("data/activities.json", "r") as f:
                activities = json.load(f)

        today_activities = []
        for activity in activities:
            start = datetime.fromisoformat(activity["start"])
            end = (
                datetime.fromisoformat(activity["end"])
                if activity["end"] is not None else now
            )
            # Overlap with [midnight, next midnight), including overnight work.
            if start < day_end and end > day_start:
                today_activities.append((start, activity))

        today_activities.sort(key=lambda entry: entry[0])
        for _, activity in today_activities:
            card = ActivityCard(activity, day_start, day_end, now)
            self.timeline_layout.addWidget(card)
            if card.end is None:
                self.running_cards.append(card)

        if not today_activities:
            empty_label = QLabel("No activities today yet.")
            empty_label.setStyleSheet("color: #64748b; padding: 12px;")
            self.timeline_layout.addWidget(empty_label)
        self.timeline_layout.addStretch()

    def update_time(self):
        now = datetime.now()
        if now.date() != self.timeline_date:
            self.load_timeline()
        for card in self.running_cards:
            card.update_duration(now)

        if self.start_time:
            self.start_label.setText(f"Time started: {self.start_time.strftime('%H:%M:%S')}")

            elapsed = now - self.start_time

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LifeAudit()
    window.show()
    sys.exit(app.exec())
