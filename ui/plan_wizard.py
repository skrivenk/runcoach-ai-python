"""Plan Creation Wizard"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QStackedWidget, QWidget, QFrame,
                               QRadioButton, QButtonGroup, QDateEdit, QSpinBox,
                               QComboBox, QLineEdit, QCheckBox, QDoubleSpinBox,
                               QTextEdit)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QCursor
from datetime import datetime, timedelta


class PlanWizard(QDialog):
    """Multi-step wizard for creating training plans"""

    plan_created = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Training Plan")
        self.setModal(True)
        self.resize(700, 600)

        # Store wizard data
        self.plan_data = {}

        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        """Initialize the wizard UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = self.create_header()
        layout.addWidget(header)

        # Stacked widget for wizard pages
        self.stack = QStackedWidget()

        # Create wizard pages
        self.page_goal = self.create_goal_page()
        self.page_timeline = self.create_timeline_page()
        self.page_baseline = self.create_baseline_page()
        self.page_schedule = self.create_schedule_page()
        self.page_guardrails = self.create_guardrails_page()
        self.page_review = self.create_review_page()

        self.stack.addWidget(self.page_goal)
        self.stack.addWidget(self.page_timeline)
        self.stack.addWidget(self.page_baseline)
        self.stack.addWidget(self.page_schedule)
        self.stack.addWidget(self.page_guardrails)
        self.stack.addWidget(self.page_review)

        layout.addWidget(self.stack)

        # Footer with navigation
        footer = self.create_footer()
        layout.addWidget(footer)

        self.setLayout(layout)

        # Update navigation buttons
        self.update_navigation()

    def create_header(self) -> QWidget:
        """Create wizard header"""
        header = QFrame()
        header.setObjectName("wizardHeader")

        layout = QVBoxLayout()

        self.title_label = QLabel("Step 1: Choose Your Goal")
        self.title_label.setObjectName("wizardTitle")

        self.subtitle_label = QLabel("Select what you're training for")
        self.subtitle_label.setObjectName("wizardSubtitle")

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)

        header.setLayout(layout)
        return header

    def create_footer(self) -> QWidget:
        """Create wizard footer with navigation"""
        footer = QFrame()
        footer.setObjectName("wizardFooter")

        layout = QHBoxLayout()

        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("secondaryButton")
        self.back_btn.clicked.connect(self.previous_page)

        layout.addWidget(self.back_btn)
        layout.addStretch()

        self.next_btn = QPushButton("Next →")
        self.next_btn.setObjectName("primaryButton")
        self.next_btn.clicked.connect(self.next_page)

        self.create_btn = QPushButton("Create Plan")
        self.create_btn.setObjectName("primaryButton")
        self.create_btn.clicked.connect(self.create_plan)
        self.create_btn.hide()

        layout.addWidget(self.next_btn)
        layout.addWidget(self.create_btn)

        footer.setLayout(layout)
        return footer

    # ========================================
    # WIZARD PAGES
    # ========================================

    def create_goal_page(self) -> QWidget:
        """Page 1: Goal Selection"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(16)

        # Goal options
        self.goal_group = QButtonGroup()

        goals = [
            ("5K", "5 kilometer race (3.1 miles)"),
            ("10K", "10 kilometer race (6.2 miles)"),
            ("half", "Half Marathon (13.1 miles)"),
            ("marathon", "Marathon (26.2 miles)"),
            ("fitness", "General Fitness - Build aerobic base"),
            ("maintenance", "Maintenance - Keep current fitness level")
        ]

        for i, (value, description) in enumerate(goals):
            radio = QRadioButton(description)
            radio.setProperty("goal_value", value)
            self.goal_group.addButton(radio, i)
            layout.addWidget(radio)

        # Set default
        self.goal_group.button(0).setChecked(True)

        layout.addStretch()
        page.setLayout(layout)
        return page

    def create_timeline_page(self) -> QWidget:
        """Page 2: Timeline"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(24)

        # Start date
        start_layout = QHBoxLayout()
        start_label = QLabel("Start Date:")
        start_label.setFixedWidth(150)
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_date)
        start_layout.addStretch()
        layout.addLayout(start_layout)

        # Race date OR duration
        race_label = QLabel("Choose one:")
        race_label.setObjectName("sectionLabel")
        layout.addWidget(race_label)

        # Race date option
        race_layout = QHBoxLayout()
        self.has_race_date = QCheckBox("I have a race date:")
        self.has_race_date.setChecked(True)
        self.race_date = QDateEdit()
        self.race_date.setDate(QDate.currentDate().addDays(84))  # 12 weeks
        self.race_date.setCalendarPopup(True)
        self.has_race_date.toggled.connect(lambda checked: self.race_date.setEnabled(checked))
        race_layout.addWidget(self.has_race_date)
        race_layout.addWidget(self.race_date)
        race_layout.addStretch()
        layout.addLayout(race_layout)

        # Duration option
        duration_layout = QHBoxLayout()
        self.has_duration = QCheckBox("Train for a specific duration:")
        self.duration_weeks = QSpinBox()
        self.duration_weeks.setRange(4, 52)
        self.duration_weeks.setValue(12)
        self.duration_weeks.setSuffix(" weeks")
        self.duration_weeks.setEnabled(False)
        self.has_duration.toggled.connect(lambda checked: self.duration_weeks.setEnabled(checked))
        self.has_duration.toggled.connect(lambda checked: self.has_race_date.setChecked(not checked))
        duration_layout.addWidget(self.has_duration)
        duration_layout.addWidget(self.duration_weeks)
        duration_layout.addStretch()
        layout.addLayout(duration_layout)

        layout.addStretch()
        page.setLayout(layout)
        return page

    def create_baseline_page(self) -> QWidget:
        """Page 3: Baseline Fitness"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(24)

        # Baseline selection
        baseline_label = QLabel("How would you like to set your baseline?")
        baseline_label.setObjectName("sectionLabel")
        layout.addWidget(baseline_label)

        self.baseline_group = QButtonGroup()

        single_run = QRadioButton("Single recent run + self-assessment")
        single_run.setChecked(True)
        self.baseline_group.addButton(single_run, 0)
        layout.addWidget(single_run)

        multiple_runs = QRadioButton("Analyze last N runs (coming soon)")
        multiple_runs.setEnabled(False)
        self.baseline_group.addButton(multiple_runs, 1)
        layout.addWidget(multiple_runs)

        layout.addSpacing(16)

        # Recent run data
        run_label = QLabel("Recent Run:")
        run_label.setObjectName("sectionLabel")
        layout.addWidget(run_label)

        # Distance
        dist_layout = QHBoxLayout()
        dist_label = QLabel("Distance:")
        dist_label.setFixedWidth(150)
        self.baseline_distance = QDoubleSpinBox()
        self.baseline_distance.setRange(0.1, 50.0)
        self.baseline_distance.setValue(5.0)
        self.baseline_distance.setSuffix(" miles")
        self.baseline_distance.setDecimals(1)
        dist_layout.addWidget(dist_label)
        dist_layout.addWidget(self.baseline_distance)
        dist_layout.addStretch()
        layout.addLayout(dist_layout)

        # Time
        time_layout = QHBoxLayout()
        time_label = QLabel("Time:")
        time_label.setFixedWidth(150)
        self.baseline_time = QSpinBox()
        self.baseline_time.setRange(10, 300)
        self.baseline_time.setValue(45)
        self.baseline_time.setSuffix(" minutes")
        time_layout.addWidget(time_label)
        time_layout.addWidget(self.baseline_time)
        time_layout.addStretch()
        layout.addLayout(time_layout)

        # RPE
        rpe_layout = QHBoxLayout()
        rpe_label = QLabel("Effort (RPE):")
        rpe_label.setFixedWidth(150)
        self.baseline_rpe = QSpinBox()
        self.baseline_rpe.setRange(1, 10)
        self.baseline_rpe.setValue(6)
        self.baseline_rpe.setSuffix(" / 10")
        rpe_layout.addWidget(rpe_label)
        rpe_layout.addWidget(self.baseline_rpe)
        rpe_layout.addStretch()
        layout.addLayout(rpe_layout)

        layout.addStretch()
        page.setLayout(layout)
        return page

    def create_schedule_page(self) -> QWidget:
        """Page 4: Schedule Preferences"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(24)

        # Max days per week
        days_layout = QHBoxLayout()
        days_label = QLabel("Max running days/week:")
        days_label.setFixedWidth(200)
        self.max_days = QSpinBox()
        self.max_days.setRange(3, 7)
        self.max_days.setValue(5)
        self.max_days.setSuffix(" days")
        days_layout.addWidget(days_label)
        days_layout.addWidget(self.max_days)
        days_layout.addStretch()
        layout.addLayout(days_layout)

        # Long run day
        long_run_layout = QHBoxLayout()
        long_run_label = QLabel("Preferred long run day:")
        long_run_label.setFixedWidth(200)
        self.long_run_day = QComboBox()
        self.long_run_day.addItems(["Sunday", "Saturday", "Friday", "Thursday", "Wednesday", "Tuesday", "Monday"])
        long_run_layout.addWidget(long_run_label)
        long_run_layout.addWidget(self.long_run_day)
        long_run_layout.addStretch()
        layout.addLayout(long_run_layout)

        # Do-not-run days
        dnr_label = QLabel("Do-not-run days: (coming soon)")
        dnr_label.setObjectName("sectionLabel")
        layout.addWidget(dnr_label)

        layout.addStretch()
        page.setLayout(layout)
        return page

    def create_guardrails_page(self) -> QWidget:
        """Page 5: Safety Guardrails"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(24)

        # Enable guardrails
        self.guardrails_enabled = QCheckBox("Enable safety guardrails (recommended)")
        self.guardrails_enabled.setChecked(True)
        layout.addWidget(self.guardrails_enabled)

        layout.addSpacing(16)

        # Weekly increase cap
        increase_layout = QHBoxLayout()
        increase_label = QLabel("Weekly mileage increase cap:")
        increase_label.setFixedWidth(220)
        self.weekly_increase = QSpinBox()
        self.weekly_increase.setRange(5, 20)
        self.weekly_increase.setValue(10)
        self.weekly_increase.setSuffix("%")
        increase_layout.addWidget(increase_label)
        increase_layout.addWidget(self.weekly_increase)
        increase_layout.addStretch()
        layout.addLayout(increase_layout)

        # Long run cap
        long_run_cap_layout = QHBoxLayout()
        long_run_cap_label = QLabel("Long run cap (% of weekly):")
        long_run_cap_label.setFixedWidth(220)
        self.long_run_cap = QSpinBox()
        self.long_run_cap.setRange(20, 40)
        self.long_run_cap.setValue(30)
        self.long_run_cap.setSuffix("%")
        long_run_cap_layout.addWidget(long_run_cap_label)
        long_run_cap_layout.addWidget(self.long_run_cap)
        long_run_cap_layout.addStretch()
        layout.addLayout(long_run_cap_layout)

        layout.addStretch()
        page.setLayout(layout)
        return page

    def create_review_page(self) -> QWidget:
        """Page 6: Review & Create"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(16)

        review_label = QLabel("Review Your Training Plan:")
        review_label.setObjectName("sectionLabel")
        layout.addWidget(review_label)

        self.review_text = QTextEdit()
        self.review_text.setReadOnly(True)
        self.review_text.setMaximumHeight(400)
        layout.addWidget(self.review_text)

        layout.addStretch()
        page.setLayout(layout)
        return page

    # ========================================
    # NAVIGATION
    # ========================================

    def update_navigation(self):
        """Update navigation buttons and header"""
        current_index = self.stack.currentIndex()
        total_pages = self.stack.count()

        # Update header
        titles = [
            ("Step 1: Choose Your Goal", "Select what you're training for"),
            ("Step 2: Timeline", "When do you start and finish?"),
            ("Step 3: Baseline Fitness", "Tell us about your current fitness level"),
            ("Step 4: Schedule", "Set your training schedule preferences"),
            ("Step 5: Safety Guardrails", "Configure safety limits"),
            ("Step 6: Review", "Review and create your plan")
        ]

        self.title_label.setText(titles[current_index][0])
        self.subtitle_label.setText(titles[current_index][1])

        # Update buttons
        self.back_btn.setEnabled(current_index > 0)

        if current_index == total_pages - 1:
            # Last page - show Create button
            self.next_btn.hide()
            self.create_btn.show()
            self.update_review()
        else:
            self.next_btn.show()
            self.create_btn.hide()

    def previous_page(self):
        """Go to previous page"""
        current = self.stack.currentIndex()
        if current > 0:
            self.stack.setCurrentIndex(current - 1)
            self.update_navigation()

    def next_page(self):
        """Go to next page"""
        current = self.stack.currentIndex()
        if current < self.stack.count() - 1:
            self.stack.setCurrentIndex(current + 1)
            self.update_navigation()

    def update_review(self):
        """Update the review page with plan summary"""
        # Get selected goal
        goal_button = self.goal_group.checkedButton()
        goal_value = goal_button.property("goal_value")
        goal_text = goal_button.text()

        # Get timeline
        start = self.start_date.date().toString("MM/dd/yyyy")
        if self.has_race_date.isChecked():
            race = self.race_date.date().toString("MM/dd/yyyy")
            timeline = f"Start: {start}\nRace Date: {race}"
        else:
            duration = self.duration_weeks.value()
            timeline = f"Start: {start}\nDuration: {duration} weeks"

        # Build summary
        summary = f"""
<h3>Goal</h3>
<p>{goal_text}</p>

<h3>Timeline</h3>
<p>{timeline.replace(chr(10), '<br>')}</p>

<h3>Baseline Fitness</h3>
<p>Recent run: {self.baseline_distance.value()} miles in {self.baseline_time.value()} minutes (RPE: {self.baseline_rpe.value()}/10)</p>

<h3>Schedule</h3>
<p>Max {self.max_days.value()} running days per week<br>
Long run on {self.long_run_day.currentText()}</p>

<h3>Safety Settings</h3>
<p>Guardrails: {'Enabled' if self.guardrails_enabled.isChecked() else 'Disabled'}<br>
Weekly increase cap: {self.weekly_increase.value()}%<br>
Long run cap: {self.long_run_cap.value()}% of weekly mileage</p>
        """

        self.review_text.setHtml(summary)

    def create_plan(self):
        """Collect data and create the plan"""
        # Get selected goal
        goal_button = self.goal_group.checkedButton()
        goal_value = goal_button.property("goal_value")

        # Build plan data
        self.plan_data = {
            'name': f"{goal_button.text().split(' -')[0]} Training Plan",
            'goal_type': goal_value,
            'start_date': self.start_date.date().toString("yyyy-MM-dd"),
            'max_days_per_week': self.max_days.value(),
            'long_run_day': self.long_run_day.currentText(),
            'weekly_increase_cap': self.weekly_increase.value() / 100.0,
            'long_run_cap': self.long_run_cap.value() / 100.0,
            'guardrails_enabled': self.guardrails_enabled.isChecked(),
            'baseline_distance': self.baseline_distance.value(),
            'baseline_time': self.baseline_time.value() * 60,  # Convert to seconds
            'baseline_rpe': self.baseline_rpe.value()
        }

        # Add race date or duration
        if self.has_race_date.isChecked():
            self.plan_data['race_date'] = self.race_date.date().toString("yyyy-MM-dd")
            # Calculate duration
            start = self.start_date.date()
            race = self.race_date.date()
            days = start.daysTo(race)
            self.plan_data['duration_weeks'] = max(4, days // 7)
        else:
            self.plan_data['duration_weeks'] = self.duration_weeks.value()
            self.plan_data['race_date'] = None

        # Emit signal and close
        self.plan_created.emit(self.plan_data)
        self.accept()

    def apply_styles(self):
        """Apply custom styles"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f7fa;
            }

            QFrame#wizardHeader {
                background-color: #2c3e50;
                padding: 24px;
            }

            QLabel#wizardTitle {
                color: white;
                font-size: 24px;
                font-weight: bold;
            }

            QLabel#wizardSubtitle {
                color: #ecf0f1;
                font-size: 14px;
                margin-top: 4px;
            }

            QLabel#sectionLabel {
                font-size: 16px;
                font-weight: 600;
                color: #2c3e50;
                margin-top: 8px;
            }

            QFrame#wizardFooter {
                background-color: white;
                padding: 16px 24px;
                border-top: 1px solid #ecf0f1;
            }

            QPushButton#primaryButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 500;
                min-width: 120px;
            }

            QPushButton#primaryButton:hover {
                background-color: #2980b9;
            }

            QPushButton#secondaryButton {
                background-color: white;
                color: #7f8c8d;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
            }

            QPushButton#secondaryButton:hover {
                background-color: #ecf0f1;
            }

            QPushButton#secondaryButton:disabled {
                opacity: 0.5;
            }

            QRadioButton, QCheckBox {
                font-size: 14px;
                padding: 8px;
            }

            QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background: white;
                min-width: 150px;
            }

            QTextEdit {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 12px;
                background: white;
            }
        """)