"""Main Window for RunCoach AI"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, QSettings

from ui.welcome_screen import WelcomeScreen
from ui.calendar_view import CalendarView


class MainWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.current_plan = None

        self.setWindowTitle("🏃 RunCoach AI")
        self.setMinimumSize(960, 640)
        self.resize(1200, 800)

        self.init_ui()
        self.apply_styles()
        self.restore_window_geometry()
        self.check_for_plans()

    # ---------- UI ----------

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.create_header()
        main_layout.addWidget(header)

        # Stacked views
        self.stack = QStackedWidget()
        self.welcome_screen = WelcomeScreen()
        self.calendar_view = CalendarView(self.db_manager)

        self.stack.addWidget(self.welcome_screen)
        self.stack.addWidget(self.calendar_view)
        main_layout.addWidget(self.stack)

        # Signals
        if hasattr(self.welcome_screen, "create_plan_clicked"):
            self.welcome_screen.create_plan_clicked.connect(self.show_plan_wizard)
        if hasattr(self.welcome_screen, "create_plan_requested"):
            self.welcome_screen.create_plan_requested.connect(self.show_plan_wizard)
        if hasattr(self.welcome_screen, "import_plan_requested"):
            self.welcome_screen.import_plan_requested.connect(self.show_import_dialog)

        central_widget.setLayout(main_layout)

    def create_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(70)

        layout = QHBoxLayout()
        layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("🏃 RunCoach AI")
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addStretch()

        # Export / Import buttons
        export_btn = QPushButton("Export")
        export_btn.setObjectName("headerButton")
        export_btn.clicked.connect(self.show_export_dialog)
        layout.addWidget(export_btn)

        import_btn = QPushButton("Import")
        import_btn.setObjectName("headerButton")
        import_btn.clicked.connect(self.show_import_dialog)
        layout.addWidget(import_btn)

        settings_btn = QPushButton("Settings")
        settings_btn.setObjectName("headerButton")
        settings_btn.clicked.connect(self.show_settings)
        layout.addWidget(settings_btn)

        header.setLayout(layout)
        return header

    # ---------- Plan routing ----------

    def _get_current_plan_id(self) -> int | None:
        val = self.db_manager.get_setting("current_plan_id")
        if not val:
            return None
        try:
            return int(val)
        except Exception:
            return None

    def _set_current_plan_id(self, pid: int):
        self.db_manager.set_setting("current_plan_id", str(pid))

    def check_for_plans(self):
        pid = self._get_current_plan_id()
        if not pid:
            plans = self.db_manager.get_all_plans()
            if plans:
                pid = plans[0]["id"]
                self._set_current_plan_id(pid)

        if not pid:
            self.stack.setCurrentWidget(self.welcome_screen)
            return

        plan = self.db_manager.get_plan(pid)
        if not plan:
            self.stack.setCurrentWidget(self.welcome_screen)
            return

        self.current_plan = plan
        self.calendar_view.set_current_plan(plan)
        self.stack.setCurrentWidget(self.calendar_view)

    # ---------- Plan creation ----------

    def show_plan_wizard(self):
        try:
            from ui.plan_wizard import PlanWizard
        except Exception as e:
            QMessageBox.critical(self, "Missing Wizard", f"Plan wizard UI not available:\n{e}")
            return

        wizard = PlanWizard(self)
        wizard.plan_created.connect(self.on_plan_created)
        wizard.exec()

    def on_plan_created(self, plan_data: dict):
        plan_id = self.db_manager.create_plan(plan_data)

        # Optional baseline (ignore if not implemented)
        try:
            baseline = {
                "plan_id": plan_id,
                "date": plan_data["start_date"],
                "distance": plan_data.get("baseline_distance"),
                "time_seconds": plan_data.get("baseline_time"),
                "rpe": plan_data.get("baseline_rpe"),
                "avg_hr": None,
                "elevation_gain": None,
                "notes": None,
            }
            if baseline["distance"] is not None:
                self.db_manager.create_baseline_run(baseline)
        except Exception:
            pass

        # Seed a simple first week
        from datetime import datetime, timedelta
        start_dt = datetime.fromisoformat(plan_data["start_date"])
        for i in range(7):
            self.db_manager.create_workout({
                "plan_id": plan_id,
                "date": (start_dt + timedelta(days=i)).strftime("%Y-%m-%d"),
                "workout_type": "easy" if i % 2 == 0 else "tempo",
                "planned_distance": 5.0,
                "planned_intensity": None,
                "description": f"Day {i + 1} (seed)",
                "notes": None,
                "modified_by": "initial_gen",
            })

        self._set_current_plan_id(plan_id)
        self.check_for_plans()

    # ---------- Import / Export ----------

    def show_export_dialog(self):
        pid = self._get_current_plan_id()
        if not pid:
            QMessageBox.information(self, "Export", "No plan to export.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Plan", "runcoach_plan.json", "JSON Files (*.json)"
        )
        if not filename:
            return

        try:
            self.db_manager.export_plan_to_file(pid, filename)
            QMessageBox.information(self, "Export", "Plan exported successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))

    def show_import_dialog(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Plan", "", "JSON Files (*.json)"
        )
        if not filename:
            return

        try:
            new_plan_id = self.db_manager.import_plan_from_file(filename)
            self._set_current_plan_id(new_plan_id)
            self.check_for_plans()
            QMessageBox.information(self, "Import", "Plan imported successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", str(e))

    # ---------- Settings / Window ----------

    def show_settings(self):
        QMessageBox.information(self, "Settings", "Settings dialog coming soon!")

    def restore_window_geometry(self):
        s = QSettings()
        geo = s.value("mainWindow/geometry", None)
        state = s.value("mainWindow/state", None)
        if geo is not None:
            self.restoreGeometry(geo)
        if state is not None:
            self.restoreState(state)

    def closeEvent(self, event):
        s = QSettings()
        s.setValue("mainWindow/geometry", self.saveGeometry())
        s.setValue("mainWindow/state", self.saveState())
        super().closeEvent(event)

    # ---------- Styles ----------

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f7fa; }
            QWidget#header { background-color: #2c3e50; }
            QLabel#title { color: white; font-size: 24px; font-weight: bold; }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:pressed { background-color: #21618c; }
            QPushButton#headerButton {
                background-color: white;
                color: #2c3e50;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            QPushButton#headerButton:hover { background-color: #ecf0f1; }
        """)
