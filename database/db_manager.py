"""Database Manager for RunCoach AI"""

import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager.

        Args:
            db_path: Path to database file. If None, uses AppData folder on Windows.
        """
        if db_path is None:
            app_data = Path.home() / "AppData" / "Roaming" / "RunCoach"
            app_data.mkdir(parents=True, exist_ok=True)
            db_path = app_data / "runcoach.db"

        self.db_path = str(db_path)
        self.init_database()

    # ---------- Core ----------

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Initialize database with schema.sql (idempotent)."""
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            with self.get_connection() as conn, open(schema_path, "r", encoding="utf-8") as f:
                conn.executescript(f.read())

    # ========================================
    # PLAN OPERATIONS
    # ========================================

    def create_plan(self, plan_data: Dict[str, Any]) -> int:
        """Create a new training plan."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO plans (
                    name, goal_type, start_date, race_date, duration_weeks,
                    max_days_per_week, long_run_day, weekly_increase_cap,
                    long_run_cap, guardrails_enabled
                )
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
            return cur.lastrowid

    def get_workouts_between_dates(
        self,
        plan_id: int,
        start_date: str,
        end_date: str,
        current_only: bool = True,
    ) -> list[dict]:
        """Return workouts between start_date and end_date (inclusive)."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            query = """
                SELECT * FROM workouts
                WHERE plan_id = ?
                  AND date >= ? AND date <= ?
            """
            params = [plan_id, start_date, end_date]
            if current_only:
                query += " AND (is_current_version = 1 OR is_current_version IS NULL)"
            query += " ORDER BY date ASC, id ASC"
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]

    def get_next_key_workout(self, plan_id: int, after_date: str) -> dict | None:
        """Return the next 'key' workout (tempo/intervals/long) after a given date."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM workouts
                WHERE plan_id = ?
                  AND date > ?
                  AND (is_current_version = 1 OR is_current_version IS NULL)
                  AND LOWER(COALESCE(workout_type,'')) IN ('tempo','intervals','long')
                ORDER BY date ASC, id ASC
                LIMIT 1
                """,
                (plan_id, after_date),
            )
            row = cur.fetchone()
            return dict(row) if row else None



    def get_plan(self, plan_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_plans(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM plans ORDER BY created_at DESC")
            return [dict(r) for r in cur.fetchall()]

    # ========================================
    # WORKOUT OPERATIONS
    # ========================================

    def create_workout(self, workout_data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO workouts (
                    plan_id, date, version, is_current_version, workout_type,
                    planned_distance, planned_intensity, description, notes,
                    modified_by, completed, actual_distance, actual_time_seconds,
                    actual_rpe, avg_hr, elevation_gain, completion_notes, completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workout_data["plan_id"],
                    workout_data["date"],
                    workout_data.get("version", 1),
                    workout_data.get("is_current_version", 1 if workout_data.get("is_current_version", True) else 0),
                    workout_data["workout_type"],
                    workout_data.get("planned_distance"),
                    workout_data.get("planned_intensity"),
                    workout_data.get("description"),
                    workout_data.get("notes"),
                    workout_data.get("modified_by", "initial_gen"),
                    workout_data.get("completed", 0),
                    workout_data.get("actual_distance"),
                    workout_data.get("actual_time_seconds"),
                    workout_data.get("actual_rpe"),
                    workout_data.get("avg_hr"),
                    workout_data.get("elevation_gain"),
                    workout_data.get("completion_notes"),
                    workout_data.get("completed_at"),
                ),
            )
            return cur.lastrowid

    def get_workouts_by_plan(self, plan_id: int, current_only: bool = True) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM workouts WHERE plan_id = ?"
            params = [plan_id]
            if current_only:
                query += " AND (is_current_version = 1 OR is_current_version IS NULL)"
            query += " ORDER BY date ASC, id ASC"
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]

    def get_workouts_on_date(self, plan_id: int, date_str: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM workouts
                WHERE plan_id = ? AND date = ? AND (is_current_version = 1 OR is_current_version IS NULL)
                ORDER BY id ASC
                """,
                (plan_id, date_str),
            )
            return [dict(r) for r in cur.fetchall()]

    def update_workout(self, workout_id: int, fields: Dict[str, Any]):
        if not fields:
            return
        cols = ", ".join([f"{k} = ?" for k in fields.keys()])
        vals = list(fields.values()) + [workout_id]
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE workouts SET {cols} WHERE id = ?", vals)

    def delete_workout(self, workout_id: int):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))

    def update_workout_completion(self, workout_id: int, completion_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
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

    # ========================================
    # SETTINGS (simple k/v)
    # ========================================

    def get_setting(self, key: str) -> Optional[str]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cur.fetchone()
            return row["value"] if row else None

    def set_setting(self, key: str, value: str):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    # ========================================
    # IMPORT / EXPORT
    # ========================================

    def export_plan_to_file(self, plan_id: int, filepath: str) -> None:
        """Write a JSON file containing the plan and all workouts."""
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        workouts = self.get_workouts_by_plan(plan_id, current_only=False)

        export = {
            "schema_version": 1,
            "exported_at": datetime.now().isoformat(),
            "plan": plan,
            "workouts": workouts,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=2)

    def import_plan_from_file(self, filepath: str) -> int:
        """Read plan JSON and create a new plan+workouts. Returns new plan_id."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        plan_src = data["plan"]
        # Build a clean plan payload (ignore id/created_at/etc.)
        plan_payload = {
            "name": plan_src.get("name", "Imported Plan"),
            "goal_type": plan_src.get("goal_type", "general"),
            "start_date": plan_src.get("start_date"),
            "race_date": plan_src.get("race_date"),
            "duration_weeks": plan_src.get("duration_weeks", 12),
            "max_days_per_week": plan_src.get("max_days_per_week", 5),
            "long_run_day": plan_src.get("long_run_day", "Sunday"),
            "weekly_increase_cap": plan_src.get("weekly_increase_cap", 0.10),
            "long_run_cap": plan_src.get("long_run_cap", 0.30),
            "guardrails_enabled": bool(plan_src.get("guardrails_enabled", True)),
        }
        new_plan_id = self.create_plan(plan_payload)

        # Insert workouts for the new plan
        for w in data.get("workouts", []):
            self.create_workout({
                "plan_id": new_plan_id,
                "date": w.get("date"),
                "version": w.get("version", 1),
                "is_current_version": w.get("is_current_version", 1 if w.get("is_current_version", True) else 0),
                "workout_type": w.get("workout_type", "easy"),
                "planned_distance": w.get("planned_distance"),
                "planned_intensity": w.get("planned_intensity"),
                "description": w.get("description"),
                "notes": w.get("notes"),
                "modified_by": "import",
                "completed": w.get("completed", 0),
                "actual_distance": w.get("actual_distance"),
                "actual_time_seconds": w.get("actual_time_seconds"),
                "actual_rpe": w.get("actual_rpe"),
                "avg_hr": w.get("avg_hr"),
                "elevation_gain": w.get("elevation_gain"),
                "completion_notes": w.get("completion_notes"),
                "completed_at": w.get("completed_at"),
            })

        return new_plan_id
