import sys
import os
import json
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QComboBox,
    QListView,
    QStyleFactory,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QProgressBar,
    QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF


class CategoryComboBox(QComboBox):
    """Draw a clear chevron without relying on the platform's dropdown icon."""

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#0c706e"), 2, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        x, y = self.width() - 18, self.height() / 2
        painter.drawPolyline(QPolygonF([
            QPointF(x - 5, y - 2), QPointF(x, y + 3), QPointF(x + 5, y - 2)
        ]))
        painter.end()


class ActivityCard(QWidget):
    """One timeline entry, showing the activity's duration within this day."""

    CATEGORY_COLORS = {
        "rest": "#5b8fc9",
        "study": "#8270cf",
        "work": "#b88b35",
        "productivity": "#739447",
        "social": "#ba6aa0",
        "not being productive": "#cb7467",
        "eat": "#ce934f",
        "hygiene": "#b56b45",
        "void": "#9295a3",
    }

    def __init__(self, activity, day_start, day_end, now, parent=None,
                 *, is_first=False, is_last=False):
        super().__init__(parent)
        self.activity = activity
        # First/last refer to each continuous stretch of tracked time.
        self.is_first = is_first
        self.is_last = is_last
        self.dot_color = QColor(self.CATEGORY_COLORS.get(activity["category"], "#9295a3"))
        self.start = datetime.fromisoformat(activity["start"])
        self.end = (
            datetime.fromisoformat(activity["end"])
            if activity["end"] is not None else None
        )
        self.day_start = day_start
        self.day_end = day_end
        self.setObjectName("ActivityCard")
        self.setProperty("running", self.end is None)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#ActivityCard { background: #ffffff; border: none; border-radius: 0; }
            QWidget#ActivityCard[running="true"] { background: #edf9f6; }
            QWidget#ActivityCard QLabel { background: transparent; border: none; }
            QLabel#timelineTime { color: #6b817e; font-size: 12px; padding-top: 19px; }
            QLabel#activityName { color: #243b38; font-size: 14px; font-weight: 600; }
            QLabel#activityDetails { color: #6b817e; font-size: 12px; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(14)

        time_text = self.start.strftime("%I:%M %p")
        if self.start.date() < day_start.date():
            time_text += self.start.strftime("\n%b %d")
            if self.start.year != day_start.year:
                time_text += self.start.strftime("\n%Y")
        time_label = QLabel(time_text)
        time_label.setToolTip(self.start.strftime("%A, %B %d, %Y at %I:%M %p"))
        time_label.setObjectName("timelineTime")
        time_label.setFixedWidth(76)
        layout.addWidget(time_label, 0, Qt.AlignmentFlag.AlignTop)

        # Reserve a full-height rail so adjacent entries connect without gaps.
        self.rail = QWidget()
        self.rail.setFixedWidth(12)
        layout.addWidget(self.rail)

        content = QVBoxLayout()
        content.setSpacing(6)
        content.setContentsMargins(0, 16, 0, 18)
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

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        x = self.rail.geometry().x() + self.rail.width() / 2
        dot_y = 25
        painter.setPen(QPen(QColor("#cfe4e1"), 2))
        painter.drawLine(
            QPointF(x, dot_y if self.is_first else 0),
            QPointF(x, dot_y if self.is_last else self.height()),
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.dot_color)
        painter.drawEllipse(QPointF(x, dot_y), 7, 7)
        painter.end()

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


class CategoryBreakdownBar(QWidget):
    """A daily bar split into category colors, scaled against the busiest day."""

    def __init__(self, category_seconds, maximum, parent=None):
        super().__init__(parent)
        self.category_seconds = category_seconds
        self.maximum = maximum
        self.setFixedHeight(8)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        shape = QPainterPath()
        shape.addRoundedRect(QRectF(self.rect()), 4, 4)
        painter.fillPath(shape, QColor("#e7f1ef"))
        total = sum(self.category_seconds.values())
        if self.maximum > 0 and total > 0:
            fill = QPainterPath()
            fill.addRoundedRect(QRectF(0, 0, self.width() * total / self.maximum,
                                      self.height()), 4, 4)
            painter.setClipPath(fill)
            x = 0.0
            for category, seconds in self.category_seconds.items():
                width = self.width() * seconds / self.maximum
                color = ActivityCard.CATEGORY_COLORS.get(category, "#9295a3")
                painter.fillRect(QRectF(x, 0, width, self.height()), QColor(color))
                x += width
        painter.end()


class LifeAudit(QWidget):
    def __init__(self):
        super().__init__()

        self.start_time = None
        self.on_void = False
        current_category = None
        self.task_label = QLabel("Ready when you are")
        self.task_label.setObjectName("currentActivity")
        self.task_label.setTextFormat(Qt.TextFormat.PlainText)
        self.task_label.setWordWrap(True)
        self.setWindowTitle("LifeAudit")

        if os.path.exists("data/activities.json"):
            with open("data/activities.json", "r") as f:
                data = json.load(f)
            self.on_void = bool(
                data and data[-1]["end"] is None and data[-1]["category"] == "void"
            )
            if data and data[-1]["end"] is None and data[-1]["category"] != "void":
                current_category = data[-1]["category"]
                self.start_time = datetime.fromisoformat(data[-1]["start"])
                self.task_label.setText(data[-1]['activity'])
                self.setWindowTitle(f"Currently: {data[-1]['activity']}")
            elif data:
                self.task_label.setText("Tracking paused")
        
        self.resize(1040, 600)
        self.setMinimumSize(900, 560)
        self.setObjectName("LifeAudit")
        self.setStyleSheet("""
            QWidget { color: #243b38; font-size: 13px; }
            QWidget#LifeAudit { background: #f5f9f8; }
            QWidget#timelineContent { background: #ffffff; }
            QLabel { background: transparent; }
            QLabel#brand { font-size: 26px; font-weight: 700; }
            QLabel#subtitle, QLabel#dateLabel, QLabel#timelineCount { color: #6b817e; }
            QLabel#sectionTitle { font-size: 15px; font-weight: 600; }
            QLabel#fieldLabel { color: #6b817e; font-size: 12px; }
            QFrame#composer { background: #ffffff; border: 1px solid #cfe4e1; border-radius: 4px; }
            QFrame#currentPanel { background: #e5f4f1; border: 1px solid #c8e5df; border-radius: 4px; }
            QLabel#eyebrow { color: #547f77; font-size: 11px; font-weight: 600; letter-spacing: 1px; }
            QLabel#currentActivity { font-size: 20px; font-weight: 600; }
            QLabel#elapsedTime { font-size: 34px; font-weight: 600; letter-spacing: 1px; }
            QLabel#startTime { color: #547f77; font-size: 12px; }
            QLabel#statusBadge { color: #366a59; background: #deeee6; border-radius: 4px; padding: 4px 10px; font-size: 11px; }
            QLineEdit, QComboBox {
                background: #f9fcfb; border: 1px solid #d5e4e0;
                border-radius: 9px; padding: 11px 12px; selection-background-color: #0f7e7b;
            }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #18a5a0; background: #ffffff; }
            QLineEdit:disabled { background: #edf3f1; color: #9295a3; border-color: #dfeae6; }
            QComboBox { padding-right: 42px; }
            QComboBox:hover { border-color: #89cec3; }
            QComboBox::drop-down {
                subcontrol-origin: padding; subcontrol-position: top right; width: 34px;
                background: #e5f4f1; border-left: 1px solid #d5e4e0;
                border-top-right-radius: 8px; border-bottom-right-radius: 8px;
            }
            QComboBox::down-arrow { image: none; }
            QComboBox QAbstractItemView {
                background: #ffffff; color: #243b38; border: 1px solid #d5e4e0;
                selection-background-color: #e5f4f1; selection-color: #195f57;
                padding: 4px; outline: none;
            }
            QComboBox QAbstractItemView::item { min-height: 28px; padding: 4px 10px; }
            QPushButton {
                background: #0f7e7b; color: #ffffff; border: none; border-radius: 9px;
                padding: 12px 20px; font-weight: 600;
            }
            QPushButton:hover { background: #0c706e; }
            QPushButton:pressed { background: #0a615f; }
            QPushButton:focus { border: 2px solid #89cec3; padding: 10px 18px; }
            QPushButton:disabled { background: #dfebe7; color: #8aa29b; }
            QScrollArea { background: transparent; border: none; }
            QScrollArea#timelineScroll {
                background: #ffffff; border: 1px solid #cfe4e1;
                border-radius: 4px; padding: 2px;
            }
            QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
            QScrollBar::handle:vertical { background: #c7dcd5; border-radius: 4px; min-height: 32px; }
            QScrollBar::handle:vertical:hover { background: #9bbfb4; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
            QLabel#emptyTimeline { color: #6b817e; padding: 28px; background: transparent; border: none; }
            QTabWidget::pane { border: none; }
            QTabBar::tab { background: transparent; color: #6b817e; padding: 12px 20px; border-bottom: 2px solid transparent; }
            QTabBar::tab:selected { color: #0c706e; border-bottom-color: #0f7e7b; }
            QTabBar::tab:hover { background: #e5f4f1; }
            QWidget#summaryContent { background: #f5f9f8; }
            QFrame#summaryPanel { background: #ffffff; border: 1px solid #cfe4e1; border-radius: 4px; }
            QLabel#summaryValue { font-size: 26px; font-weight: 600; }
            QProgressBar { background: #e7f1ef; border: none; border-radius: 4px; height: 8px; }
            QProgressBar::chunk { background: #18a5a0; border-radius: 4px; }
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs)
        main_tab = QWidget()
        self.tabs.addTab(main_tab, "Main")
        layout = QGridLayout(main_tab)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setHorizontalSpacing(24)
        layout.setVerticalSpacing(14)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(2, 1)

        title = QLabel("LifeAudit")
        title.setObjectName("brand")
        subtitle = QLabel("accountability engine, no minute left untracked")
        subtitle.setObjectName("subtitle")
        layout.addWidget(title, 0, 0)
        layout.addWidget(subtitle, 1, 0, Qt.AlignmentFlag.AlignVCenter)
        self.date_label = QLabel()
        self.date_label.setObjectName("dateLabel")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.date_label, 0, 1)

        controls_column = QVBoxLayout()
        controls_column.setSpacing(20)
        layout.addLayout(controls_column, 2, 0)

        composer = QFrame()
        composer.setObjectName("composer")
        form = QVBoxLayout(composer)
        form.setContentsMargins(20, 18, 20, 20)
        form.setSpacing(10)
        form_title = QLabel("What are you doing?")
        form_title.setObjectName("sectionTitle")
        form.addWidget(form_title)

        self.activity_input = QLineEdit()
        self.activity_input.setPlaceholderText("e.g. Doing calculus")
        self.activity_input.setClearButtonEnabled(True)
        self.activity_input.returnPressed.connect(self.start_activity)
        form.addWidget(self.activity_input)

        category_label = QLabel("Category")
        category_label.setObjectName("fieldLabel")
        form.addWidget(category_label)

        self.category_dropdown = CategoryComboBox()
        # Use the same popup presentation on every platform.
        self.category_style = QStyleFactory.create("Fusion")
        self.category_style.setParent(self.category_dropdown)
        self.category_dropdown.setStyle(self.category_style)
        self.category_dropdown.setView(QListView())
        self.category_dropdown.setCursor(Qt.CursorShape.PointingHandCursor)
        self.category_dropdown.addItems([
            "rest",
            "study",
            "work",
            "productivity",
            "social",
            "not being productive",
            "eat",
            "hygiene",
            "void"
            # void --> not tracked
        ])
        self.category_dropdown.currentTextChanged.connect(self.update_activity_input)
        actions = QHBoxLayout()
        actions.setSpacing(12)
        actions.addWidget(self.category_dropdown, 1)

        self.start_button = QPushButton("Start Activity")
        self.start_button.clicked.connect(self.start_activity)
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        actions.addWidget(self.start_button)
        form.addLayout(actions)
        controls_column.addWidget(composer)

        current_panel = QFrame()
        current_panel.setObjectName("currentPanel")
        current_layout = QVBoxLayout(current_panel)
        current_layout.setContentsMargins(22, 18, 22, 20)
        current_layout.setSpacing(10)
        current_header = QHBoxLayout()
        self.current_heading = QLabel(
            f"CURRENT ACTIVITY · {current_category}"
            if current_category else "CURRENT ACTIVITY"
        )
        self.current_heading.setObjectName("eyebrow")
        self.current_heading.setTextFormat(Qt.TextFormat.PlainText)
        self.current_heading.setWordWrap(True)
        current_header.addWidget(self.current_heading, 1)
        self.status_badge = QLabel()
        self.status_badge.setObjectName("statusBadge")
        current_header.addWidget(self.status_badge)
        current_layout.addLayout(current_header)
        current_layout.addWidget(self.task_label)
        self.elapsed_label = QLabel()
        self.elapsed_label.setObjectName("elapsedTime")
        self.start_label = QLabel()
        self.start_label.setObjectName("startTime")
        current_layout.addWidget(self.elapsed_label)
        current_layout.addWidget(self.start_label)
        controls_column.addWidget(current_panel)
        controls_column.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        timeline_header = QHBoxLayout()
        timeline_title = QLabel("Today's timeline")
        timeline_title.setObjectName("sectionTitle")
        timeline_header.addWidget(timeline_title, 1)
        self.timeline_count = QLabel()
        self.timeline_count.setObjectName("timelineCount")
        timeline_header.addWidget(self.timeline_count)
        layout.addLayout(timeline_header, 1, 1)

        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setObjectName("timelineScroll")
        self.timeline_scroll.setWidgetResizable(True)
        self.timeline_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.timeline_scroll.setMinimumHeight(180)
        timeline_content = QWidget()
        timeline_content.setObjectName("timelineContent")
        self.timeline_layout = QVBoxLayout(timeline_content)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline_layout.setSpacing(0)
        self.timeline_scroll.setWidget(timeline_content)
        layout.addWidget(self.timeline_scroll, 2, 1)

        if self.on_void:
            self.category_dropdown.setCurrentText("void")
        self.build_weekly_summary()
        self.tabs.currentChanged.connect(self.refresh_summary_tab)
        self.load_timeline()
        self.update_time()

    def build_weekly_summary(self):
        self.summary_week_offset = 0
        self.summary_tab = QScrollArea()
        self.summary_tab.setWidgetResizable(True)
        self.summary_tab.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("summaryContent")
        self.summary_tab.setWidget(content)
        self.tabs.addTab(self.summary_tab, "Weekly Summary")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        title = QLabel("Weekly summary")
        title.setObjectName("brand")
        heading.addWidget(title)
        self.summary_week_label = QLabel()
        self.summary_week_label.setObjectName("subtitle")
        heading.addWidget(self.summary_week_label)
        header.addLayout(heading, 1)
        self.previous_week_button = QPushButton("←")
        self.previous_week_button.setAccessibleName("Previous week")
        self.previous_week_button.clicked.connect(lambda: self.change_summary_week(-1))
        header.addWidget(self.previous_week_button)
        this_week = QPushButton("This week")
        this_week.clicked.connect(lambda: self.change_summary_week(None))
        header.addWidget(this_week)
        self.next_week_button = QPushButton("→")
        self.next_week_button.setAccessibleName("Next week")
        self.next_week_button.clicked.connect(lambda: self.change_summary_week(1))
        header.addWidget(self.next_week_button)
        layout.addLayout(header)

        stats = QHBoxLayout()
        self.summary_stats = []
        for caption in ("Tracked time", "Activities", "Days tracked"):
            panel = QFrame()
            panel.setObjectName("summaryPanel")
            panel_layout = QVBoxLayout(panel)
            panel_layout.setContentsMargins(18, 14, 18, 14)
            label = QLabel(caption)
            label.setObjectName("subtitle")
            value = QLabel()
            value.setObjectName("summaryValue")
            panel_layout.addWidget(label)
            panel_layout.addWidget(value)
            self.summary_stats.append(value)
            stats.addWidget(panel, 1)
        layout.addLayout(stats)

        breakdowns = QHBoxLayout()
        breakdowns.setSpacing(20)
        for title, attribute in (("By day", "summary_days_layout"),
                                 ("By category", "summary_categories_layout")):
            panel = QFrame()
            panel.setObjectName("summaryPanel")
            panel_layout = QVBoxLayout(panel)
            panel_layout.setContentsMargins(18, 16, 18, 16)
            panel_layout.setSpacing(14)
            label = QLabel(title)
            label.setObjectName("sectionTitle")
            panel_layout.addWidget(label)
            rows = QVBoxLayout()
            rows.setSpacing(12)
            setattr(self, attribute, rows)
            panel_layout.addLayout(rows)
            panel_layout.addStretch()
            breakdowns.addWidget(panel, 1)
        layout.addLayout(breakdowns)
        note = QLabel("Void is excluded. Overnight activities are split by day. Running time is included up to now.")
        note.setObjectName("subtitle")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        self.load_weekly_summary()

    def change_summary_week(self, offset):
        self.summary_week_offset = (
            0 if offset is None else min(0, self.summary_week_offset + offset)
        )
        self.load_weekly_summary()

    def refresh_summary_tab(self, index):
        if self.tabs.widget(index) is self.summary_tab:
            self.load_weekly_summary()

    def load_weekly_summary(self):
        now = datetime.now()
        self.summary_refreshed_minute = now.replace(second=0, microsecond=0)
        activities = []
        if os.path.exists("data/activities.json"):
            with open("data/activities.json", "r") as f:
                activities = json.load(f)
        ordered = sorted((datetime.fromisoformat(activity["start"]), index, activity)
                         for index, activity in enumerate(activities))

        current_week = now.replace(hour=0, minute=0, second=0, microsecond=0)
        current_week -= timedelta(days=(now.weekday() + 1) % 7)
        first_activity = ordered[0][0] if ordered else now
        first_week = first_activity.replace(hour=0, minute=0, second=0, microsecond=0)
        first_week -= timedelta(days=(first_activity.weekday() + 1) % 7)
        earliest_offset = min(0, (first_week - current_week).days // 7)
        self.summary_week_offset = max(earliest_offset, min(0, self.summary_week_offset))
        week_start = current_week + timedelta(weeks=self.summary_week_offset)
        week_end = week_start + timedelta(days=7)
        last_day = week_end - timedelta(days=1)
        self.summary_week_label.setText(
            f"{week_start:%b %d, %Y} – {last_day:%b %d, %Y} · Sunday–Saturday"
        )
        self.next_week_button.setEnabled(self.summary_week_offset < 0)
        self.previous_week_button.setEnabled(self.summary_week_offset > earliest_offset)

        days = [0.0] * 7
        day_categories = [{} for _ in range(7)]
        categories = {}
        count = 0
        for position, (activity_start, _, activity) in enumerate(ordered):
            if activity["category"] == "void":
                continue
            start = max(activity_start, week_start)
            end = min(datetime.fromisoformat(activity["end"])
                      if activity["end"] is not None else now, week_end, now)
            # A new activity (including void) supersedes the previous one.
            if position + 1 < len(ordered):
                end = min(end, ordered[position + 1][0])
            if end <= start:
                continue
            count += 1
            category = activity["category"]
            categories[category] = categories.get(category, 0) + (end - start).total_seconds()
            for index in range(7):
                day_start = week_start + timedelta(days=index)
                day_end = day_start + timedelta(days=1)
                seconds = max(0, (min(end, day_end) - max(start, day_start)).total_seconds())
                days[index] += seconds
                if seconds:
                    day_categories[index][category] = day_categories[index].get(category, 0) + seconds

        total = sum(days)
        self.summary_stats[0].setText(self.summary_duration(total))
        self.summary_stats[1].setText(str(count))
        self.summary_stats[2].setText(f"{sum(seconds > 0 for seconds in days)} / 7")
        for rows in (self.summary_days_layout, self.summary_categories_layout):
            while rows.count():
                widget = rows.takeAt(0).widget()
                widget.hide()
                widget.deleteLater()
        for index, seconds in enumerate(days):
            day = week_start + timedelta(days=index)
            shares = {category: day_categories[index][category]
                      for category in sorted(categories, key=categories.get, reverse=True)
                      if category in day_categories[index]}
            self.add_summary_row(self.summary_days_layout, day.strftime("%a %d"),
                                 seconds, max(days), "#18a5a0", shares)
        for category, seconds in sorted(categories.items(), key=lambda item: item[1], reverse=True):
            self.add_summary_row(self.summary_categories_layout, category, seconds, total,
                                 ActivityCard.CATEGORY_COLORS.get(category, "#9295a3"))
        if not categories:
            empty = QLabel("No tracked activities this week yet.")
            empty.setObjectName("subtitle")
            empty.setWordWrap(True)
            self.summary_categories_layout.addWidget(empty)

    @staticmethod
    def summary_duration(seconds):
        if 0 < seconds < 60:
            return "<1m"
        hours, minutes = divmod(int(seconds) // 60, 60)
        return f"{hours}h {minutes}m" if hours else f"{minutes}m"

    def add_summary_row(self, layout, title, seconds, maximum, color, category_seconds=None):
        row = QWidget()
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(5)
        labels = QHBoxLayout()
        name = QLabel(title)
        name.setTextFormat(Qt.TextFormat.PlainText)
        name.setWordWrap(True)
        labels.addWidget(name, 1)
        duration_text = self.summary_duration(seconds)
        if category_seconds is None:
            percentage = seconds / maximum * 100 if maximum else 0
            duration_text += f" · {percentage:.1f}%"
        duration = QLabel(duration_text)
        duration.setObjectName("subtitle")
        labels.addWidget(duration)
        row_layout.addLayout(labels)
        if category_seconds is not None:
            bar = CategoryBreakdownBar(category_seconds, maximum)
            tooltip = "\n".join(
                f"{category}: {self.summary_duration(value)} ({value / seconds:.1%})"
                for category, value in category_seconds.items()
            ) if seconds else "No tracked time"
            bar.setToolTip(tooltip)
            bar.setAccessibleDescription(tooltip)
        else:
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setValue(round(seconds / maximum * 1000) if maximum else 0)
            bar.setTextVisible(False)
            bar.setFixedHeight(8)
            bar.setStyleSheet(f"QProgressBar::chunk {{ background: {color}; }}")
        bar.setAccessibleName(f"{title}: {duration.text()}")
        row_layout.addWidget(bar)
        layout.addWidget(row)

    def update_activity_input(self, category):
        is_void = category == "void"
        self.activity_input.setEnabled(not is_void)
        self.start_button.setEnabled(not (is_void and self.on_void))
        self.activity_input.setPlaceholderText(
            "Untracked time" if is_void else "e.g. Doing calculus"
        )
        if is_void:
            self.activity_input.clear()

    def start_activity(self):
        activity = self.activity_input.text().strip()
        category = self.category_dropdown.currentText()
        if category == "void" and self.on_void:
            return
        if not activity and category != "void":
            return

        now = datetime.now()
        timestamp = now.isoformat()
        activities = []
        if os.path.exists("data/activities.json"):
            with open("data/activities.json", "r") as f:
                activities = json.load(f)

        # Close only a running activity, preserving any untracked gap.
        if activities and activities[-1]["end"] is None:
            activities[-1]["end"] = timestamp

        activities.append({
            "activity": "" if category == "void" else activity,
            "category": category,
            "start": timestamp,
            "end": None
        })

        os.makedirs("data", exist_ok=True)
        with open("data/activities.json", "w") as f:
            json.dump(activities, f, indent=4)

        self.on_void = category == "void"
        if category == "void":
            self.start_time = None
            self.current_heading.setText("CURRENT ACTIVITY")
            self.task_label.setText("Tracking paused")
            self.setWindowTitle("LifeAudit")
        else:
            self.start_time = now
            self.current_heading.setText(f"CURRENT ACTIVITY · {category}")
            self.task_label.setText(activity)
            self.setWindowTitle(f"Currently: {activity}")

        self.activity_input.clear()
        self.update_activity_input(category)
        self.load_timeline()
        self.load_weekly_summary()
        self.update_time()

    def load_timeline(self):
        now = datetime.now()
        self.timeline_date = now.date()
        self.date_label.setText(now.strftime("%A\n%b %d, %Y"))
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
            if activity["category"] == "void":
                continue
            start = datetime.fromisoformat(activity["start"])
            end = (
                datetime.fromisoformat(activity["end"])
                if activity["end"] is not None else now
            )
            # Overlap with [midnight, next midnight), including overnight work.
            if start < day_end and end > day_start:
                today_activities.append((start, activity))

        today_activities.sort(key=lambda entry: entry[0])
        count = len(today_activities)
        self.timeline_count.setText(f"{count} {'activity' if count == 1 else 'activities'}")
        # Void is hidden, so a gap between end and start marks a line break.
        breaks = {0, count}
        for index in range(1, count):
            previous_end = today_activities[index - 1][1]["end"]
            start = today_activities[index][0]
            if previous_end is not None and datetime.fromisoformat(previous_end) < start:
                breaks.add(index)

        for index, (_, activity) in enumerate(today_activities):
            card = ActivityCard(activity, day_start, day_end, now,
                                is_first=index in breaks, is_last=index + 1 in breaks)
            self.timeline_layout.addWidget(card)
            if card.end is None:
                self.running_cards.append(card)

        if not today_activities:
            empty_label = QLabel("Your day starts here.\nStart an activity to build your timeline.")
            empty_label.setObjectName("emptyTimeline")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setWordWrap(True)
            self.timeline_layout.addWidget(empty_label)
        self.timeline_layout.addStretch()

    def update_time(self):
        now = datetime.now()
        if (self.tabs.currentWidget() is self.summary_tab
                and now.replace(second=0, microsecond=0) != self.summary_refreshed_minute):
            self.load_weekly_summary()
        if now.date() != self.timeline_date:
            self.load_timeline()
        for card in self.running_cards:
            card.update_duration(now)

        if self.start_time:
            self.status_badge.setText("●  In progress")
            self.start_label.setText(f"Started at {self.start_time.strftime('%I:%M %p')} · elapsed time")

            elapsed = now - self.start_time

            total_seconds = int(elapsed.total_seconds())

            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            self.elapsed_label.setText(
                f"{hours:02}:{minutes:02}:{seconds:02}"
            )
        else:
            self.status_badge.setText("Not tracking")
            self.start_label.setText("Start an activity when you're ready.")
            self.elapsed_label.setText("00:00:00")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LifeAudit()
    window.show()
    sys.exit(app.exec())
