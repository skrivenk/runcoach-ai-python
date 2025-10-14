"""Database Manager for RunCoach AI"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to database file. If None, uses %APPDATA%/RunCoach/runcoach.db on Windows,
                     or ~/.config/RunCoach/runcoach.db on other OSes.
        """
        if db_path is None:
            if Path.home().as_posix().startswith("/home") or Path.home().as_posix().startswith("/Users"):
                # macOS/Linux: use ~/.config/RunCoach
                app_data = Path.home() / ".config" / "RunCoach"
            else:
                # Windows default (matches your snippet)
                app_data = Path.home() / "AppData" / "Roaming" / "RunCoach"
            app_data.mkdir(parents=True, exist_ok=True)
            db_path = app_data / "runcoach.db"

        self.db_path = str(db_path)
        self.init_database()

    # ---------------------------
    # Core connection + bootstrap
    # ---------------------------

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection with dict-like rows and foreign keys enabled.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # dict-like rows
        # Safety/consistency tweaks
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def init_database(self) -> None:
        """
        Initialize database with schema.sql (idempotent if schema uses IF NOT EXISTS).
        """
        schema_path = Path(__file__).parent / "schema.sql"
        if not schema_path.exists():
            raise FileNotFoundError(
                f"schema.sql not found at {schema_path}. "
                "Make sure it lives next to db_manager.py."
            )

        with self.get_connection() as conn, open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        print(f"Database initialized at: {self.db_path}")

    def get_workouts_on_date(self, plan_id: int, date_str: str) -> list[dict]:
        """All workouts for a plan on a specific date."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM workouts
                WHERE plan_id = ? AND date = ? AND (is_current_version = 1 OR is_current_version IS NULL)
                ORDER BY id ASC
            """, (plan_id, date_str))
            return [dict(r) for r in cur.fetchall()]

    def update_workout(self, workout_id: int, fields: dict):
        """Generic partial update. fields keys must match column names."""
        if not fields:
            return
        cols = ", ".join([f"{k} = ?" for k in fields.keys()])
        vals = list(fields.values())
        vals.append(workout_id)
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE workouts SET {cols} WHERE id = ?", vals)

    def delete_workout(self, workout_id: int):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))



    # --------------
    # Plan operations
    # --------------

    def create_plan(self, plan_data: Dict[str, Any]) -> int:
        """
        Create a new training plan. Expects keys:
        name, goal_type, start_date, race_date?, duration_weeks,
        max_days_per_week?, long_run_day?, weekly_increase_cap?, long_run_cap?, guardrails_enabled?
        """
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO plans
                    (name, goal_type, start_date, race_date, duration_weeks,
                     max_days_per_week, long_run_day, weekly_increase_cap,
                     long_run_cap, guardrails_enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan_data["name"],
                    plan_data["goal_type"],
                    plan_data["start_date"],
                    plan_data.get("race_date"),
                    plan_data["duration_weeks"],
                    plan_data.get("max_days_per_week", 5),
                    plan_data.get("long_run_day", "Sunday"),
                    plan_data.get("weekly_increase_cap", 0.10),
                    plan_data.get("long_run_cap", 0.30),
                    plan_data.get("guardrails_enabled", True),
                ),
            )
            return c.lastrowid

    def get_plan(self, plan_id: int) -> Optional[Dict]:
        """Get a plan by ID."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
            row = c.fetchone()
            return dict(row) if row else None

    # Alias—handy when naming reads more clearly in calling code
    def get_plan_by_id(self, plan_id: int) -> Optional[Dict]:
        return self.get_plan(plan_id)

    def get_all_plans(self) -> List[Dict]:
        """Get all plans (most recent first)."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM plans ORDER BY created_at DESC")
            return [dict(row) for row in c.fetchall()]

    # --------------------
    # Baseline run helpers
    # --------------------

    def create_baseline_run(self, baseline: Dict[str, Any]) -> int:
        """
        Create a baseline run. Expects keys:
        plan_id, date (YYYY-MM-DD), distance, time_seconds,
        rpe?, avg_hr?, elevation_gain?, notes?
        """
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO baseline_runs
                    (plan_id, date, distance, time_seconds, rpe, avg_hr, elevation_gain, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    baseline["plan_id"],
                    baseline["date"],
                    baseline["distance"],
                    baseline["time_seconds"],
                    baseline.get("rpe"),
                    baseline.get("avg_hr"),
                    baseline.get("elevation_gain"),
                    baseline.get("notes"),
                ),
            )
            return c.lastrowid

    def get_baseline_runs(self, plan_id: int) -> List[Dict]:
        """Return all baseline runs for a plan."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT * FROM baseline_runs WHERE plan_id = ? ORDER BY date ASC",
                (plan_id,),
            )
            return [dict(r) for r in c.fetchall()]

    # ------------------
    # Settings / current
    # ------------------

    def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = c.fetchone()
            return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> None:
        """Set a setting value."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    # Convenience wrappers for the active plan the UI should show
    def set_current_plan_id(self, plan_id: int) -> None:
        self.set_setting("current_plan_id", str(plan_id))

    def get_current_plan_id(self) -> Optional[int]:
        val = self.get_setting("current_plan_id")
        try:
            return int(val) if val is not None else None
        except ValueError:
            return None

    # -------------------
    # Workout CRUD / read
    # -------------------

    def create_workout(self, workout_data: Dict[str, Any]) -> int:
        """
        Create a new workout. Expects keys:
        plan_id, date (YYYY-MM-DD), workout_type,
        version? (default 1), is_current_version? (default True),
        planned_distance?, planned_intensity?, description?, notes?, modified_by?
        """
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO workouts
                    (plan_id, date, version, is_current_version, workout_type,
                     planned_distance, planned_intensity, description, notes, modified_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workout_data["plan_id"],
                    workout_data["date"],
                    workout_data.get("version", 1),
                    1 if workout_data.get("is_current_version", True) else 0,
                    workout_data["workout_type"],
                    workout_data.get("planned_distance"),
                    workout_data.get("planned_intensity"),
                    workout_data.get("description"),
                    workout_data.get("notes"),
                    workout_data.get("modified_by", "initial_gen"),
                ),
            )
            return c.lastrowid

    def get_workouts_by_plan(self, plan_id: int, current_only: bool = True) -> List[Dict]:
        """Get all workouts for a plan (optionally only the current version)."""
        with self.get_connection() as conn:
            c = conn.cursor()
            query = "SELECT * FROM workouts WHERE plan_id = ?"
            params: List[Any] = [plan_id]
            if current_only:
                query += " AND is_current_version = 1"
            query += " ORDER BY date ASC"
            c.execute(query, params)
            return [dict(row) for row in c.fetchall()]

    def get_workouts_on_date(self, plan_id: int, date_str: str) -> List[Dict]:
        """Return workouts on a specific date for a plan."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT * FROM workouts
                WHERE plan_id = ? AND date = ? AND is_current_version = 1
                ORDER BY id ASC
                """,
                (plan_id, date_str),
            )
            return [dict(r) for r in c.fetchall()]

    def get_workouts_by_date_range(
        self, plan_id: int, start_date: str, end_date: str, current_only: bool = True
    ) -> List[Dict]:
        """
        Return workouts for plan within [start_date, end_date] inclusive.
        Dates should be 'YYYY-MM-DD'.
        """
        with self.get_connection() as conn:
            c = conn.cursor()
            query = """
                SELECT * FROM workouts
                WHERE plan_id = ? AND date >= ? AND date <= ?
            """
            params: List[Any] = [plan_id, start_date, end_date]
            if current_only:
                query += " AND is_current_version = 1"
            query += " ORDER BY date ASC"
            c.execute(query, params)
            return [dict(r) for r in c.fetchall()]

    def update_workout_fields(self, workout_id: int, fields: Dict[str, Any]) -> None:
        """
        Generic workout update. Example:
        update_workout_fields(5, {"planned_distance": 8.0, "notes": "Bump mileage"})
        """
        if not fields:
            return
        cols = ", ".join([f"{k} = ?" for k in fields.keys()])
        values = list(fields.values())
        values.append(workout_id)
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(f"UPDATE workouts SET {cols} WHERE id = ?", values)

    def delete_workout(self, workout_id: int) -> None:
        """Delete a workout by id."""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))

    def update_workout_completion(self, workout_id: int, completion_data: Dict[str, Any]) -> None:
        """
        Mark a workout as completed (and log actuals).
        Expects keys (all optional except the ones you want to store):
          actual_distance, actual_time_seconds, actual_rpe, avg_hr, elevation_gain, completion_notes
        """
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
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
                """,
                (
                    completion_data.get("actual_distance"),
                    completion_data.get("actual_time_seconds"),
                    completion_data.get("actual_rpe"),
                    completion_data.get("avg_hr"),
                    completion_data.get("elevation_gain"),
                    completion_data.get("completion_notes"),
                    datetime.now().isoformat(),
                    workout_id,
                ),
            )

    # -----------------
    # AI usage (optional)
    # -----------------

    def log_ai_usage(
        self,
        model: str,
        tokens_prompt: int,
        tokens_completion: int,
        usd_cost: float,
        purpose: Optional[str] = None,
        metadata: Optional[str] = None,
    ) -> int:
        """
        Record an AI call (handy when we wire OpenAI generation).
        """
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO ai_usage_log
                    (model, tokens_prompt, tokens_completion, usd_cost, purpose, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (model, tokens_prompt, tokens_completion, usd_cost, purpose, metadata),
            )
            return c.lastrowid
