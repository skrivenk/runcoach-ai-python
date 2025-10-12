"""Database Manager for RunCoach AI"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager

        Args:
            db_path: Path to database file. If None, uses AppData folder.
        """
        if db_path is None:
            # Store in user's AppData on Windows
            app_data = Path.home() / "AppData" / "Roaming" / "RunCoach"
            app_data.mkdir(parents=True, exist_ok=True)
            db_path = app_data / "runcoach.db"

        self.db_path = str(db_path)
        self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return dict-like rows
        return conn

    def init_database(self):
        """Initialize database with schema"""
        schema_path = Path(__file__).parent / "schema.sql"

        with self.get_connection() as conn:
            with open(schema_path, 'r') as f:
                conn.executescript(f.read())
            print(f"Database initialized at: {self.db_path}")

    # ========================================
    # PLAN OPERATIONS
    # ========================================

    def create_plan(self, plan_data: Dict[str, Any]) -> int:
        """Create a new training plan"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           INSERT INTO plans (name, goal_type, start_date, race_date, duration_weeks,
                                              max_days_per_week, long_run_day, weekly_increase_cap,
                                              long_run_cap, guardrails_enabled)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           """, (
                               plan_data['name'],
                               plan_data['goal_type'],
                               plan_data['start_date'],
                               plan_data.get('race_date'),
                               plan_data['duration_weeks'],
                               plan_data.get('max_days_per_week', 5),
                               plan_data.get('long_run_day', 'Sunday'),
                               plan_data.get('weekly_increase_cap', 0.10),
                               plan_data.get('long_run_cap', 0.30),
                               plan_data.get('guardrails_enabled', True)
                           ))
            return cursor.lastrowid

    def get_plan(self, plan_id: int) -> Optional[Dict]:
        """Get a plan by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_plans(self) -> List[Dict]:
        """Get all plans"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM plans ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    # ========================================
    # WORKOUT OPERATIONS
    # ========================================

    def create_workout(self, workout_data: Dict[str, Any]) -> int:
        """Create a new workout"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           INSERT INTO workouts (plan_id, date, version, is_current_version, workout_type,
                                                 planned_distance, planned_intensity, description, notes,
                                                 modified_by)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           """, (
                               workout_data['plan_id'],
                               workout_data['date'],
                               workout_data.get('version', 1),
                               workout_data.get('is_current_version', True),
                               workout_data['workout_type'],
                               workout_data.get('planned_distance'),
                               workout_data.get('planned_intensity'),
                               workout_data.get('description'),
                               workout_data.get('notes'),
                               workout_data.get('modified_by', 'initial_gen')
                           ))
            return cursor.lastrowid

    def get_workouts_by_plan(self, plan_id: int, current_only: bool = True) -> List[Dict]:
        """Get all workouts for a plan"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM workouts WHERE plan_id = ?"
            params = [plan_id]

            if current_only:
                query += " AND is_current_version = 1"

            query += " ORDER BY date ASC"

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def update_workout_completion(self, workout_id: int, completion_data: Dict[str, Any]):
        """Mark a workout as completed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           UPDATE workouts
                           SET completed           = 1,
                               actual_distance     = ?,
                               actual_time_seconds = ?,
                               actual_rpe          = ?,
                               avg_hr              = ?,
                               elevation_gain      = ?,
                               completion_notes    = ?,
                               completed_at        = ?
                           WHERE id = ?
                           """, (
                               completion_data.get('actual_distance'),
                               completion_data.get('actual_time_seconds'),
                               completion_data.get('actual_rpe'),
                               completion_data.get('avg_hr'),
                               completion_data.get('elevation_gain'),
                               completion_data.get('completion_notes'),
                               datetime.now().isoformat(),
                               workout_id
                           ))

    # ========================================
    # SETTINGS
    # ========================================

    def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else None

    def set_setting(self, key: str, value: str):
        """Set a setting value"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           INSERT INTO app_settings (key, value)
                           VALUES (?, ?) ON CONFLICT(key) DO
                           UPDATE SET value = ?
                           """, (key, value, value))