# database/db_manager.py
"""Database Manager for RunCoach AI

- Uses %APPDATA%\RunCoach\runcoach.db on Windows, ~/.runcoach/runcoach.db elsewhere.
- Ensures PRAGMA foreign_keys=ON per connection.
- Provides helpers to store/read OpenAI API key with ENV override:
    - get_api_key(): returns OPENAI_API_KEY env if set, else app_settings['api_key']
    - set_api_key(key): persists to app_settings (plain text convenience; prefer ENV for real secrets)
"""

from __future__ import annotations

import os
import sys
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to database file. If None, uses:
                     - Windows: %APPDATA%\\RunCoach\\runcoach.db
                     - Others : ~/.runcoach/runcoach.db
        """
        if db_path is None:
            if sys.platform.startswith("win"):
                appdata = os.environ.get("APPDATA")
                base = Path(appdata) if appdata else (Path.home() / "AppData" / "Roaming")
                root = base / "RunCoach"
            else:
                root = Path.home() / ".runcoach"
            root.mkdir(parents=True, exist_ok=True)
            db_path = root / "runcoach.db"

        self.db_path = str(db_path)
        self.init_database()

    # ------------------------------------------------------------------ #
    # Core
    # ------------------------------------------------------------------ #

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory and foreign keys ON."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_database(self):
        """Initialize database using schema.sql if present (idempotent)."""
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            with self.get_connection() as conn:
                with open(schema_path, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
                # Seed defaults (harmless if already present in schema.sql)
                conn.executescript(
                    """
                    INSERT OR IGNORE INTO app_settings (key, value) VALUES
                        ('units', 'imperial'),
                        ('theme', 'light'),
                        ('api_key', '');
                    """
                )
        else:
            # Minimal fallback schema (kept small on purpose)
            with self.get_connection() as conn:
                conn.executescript(
                    """
                    PRAGMA foreign_keys = ON;

                    -- Training Plans
                    CREATE TABLE IF NOT EXISTS plans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        goal_type TEXT NOT NULL,
                        start_date TEXT NOT NULL,
                        race_date TEXT,
                        duration_weeks INTEGER NOT NULL,
                        max_days_per_week INTEGER DEFAULT 5,
                        long_run_day TEXT DEFAULT 'Sunday',
                        weekly_increase_cap REAL DEFAULT 0.10,
                        long_run_cap REAL DEFAULT 0.30,
                        guardrails_enabled INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT (datetime('now')),
                        last_modified TEXT DEFAULT (datetime('now'))
                    );

                    -- Workouts (Versioned)
                    CREATE TABLE IF NOT EXISTS workouts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plan_id INTEGER NOT NULL,
                        date TEXT NOT NULL,
                        version INTEGER DEFAULT 1,
                        is_current_version INTEGER DEFAULT 1,
                        workout_type TEXT NOT NULL,
                        planned_distance REAL,
                        planned_intensity TEXT,
                        description TEXT,
                        notes TEXT,
                        completed INTEGER DEFAULT 0,
                        actual_distance REAL,
                        actual_time_seconds INTEGER,
                        actual_rpe INTEGER,
                        avg_hr INTEGER,
                        elevation_gain REAL,
                        completion_notes TEXT,
                        completed_at TEXT,
                        created_at TEXT DEFAULT (datetime('now')),
                        modified_by TEXT,
                        FOREIGN KEY(plan_id) REFERENCES plans(id) ON DELETE CASCADE
                    );

                    CREATE INDEX IF NOT EXISTS idx_workouts_current
                      ON workouts(plan_id, date, is_current_version);

                    -- Baseline Runs
                    CREATE TABLE IF NOT EXISTS baseline_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plan_id INTEGER NOT NULL,
                        date TEXT NOT NULL,
                        distance REAL,
                        time_seconds INTEGER,
                        rpe INTEGER,
                        avg_hr INTEGER,
                        elevation_gain REAL,
                        notes TEXT,
                        FOREIGN KEY(plan_id) REFERENCES plans(id) ON DELETE CASCADE
                    );

                    -- App Settings (k/v)
                    CREATE TABLE IF NOT EXISTS app_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );

                    -- API Call Log
                    CREATE TABLE IF NOT EXISTS api_calls (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plan_id INTEGER,
                        call_type TEXT NOT NULL,
                        timestamp TEXT DEFAULT (datetime('now')),
                        tokens_used INTEGER,
                        cost_usd REAL,
                        FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
                    );

                    -- Workout templates (if your schema.sql also has this, harmless)
                    CREATE TABLE IF NOT EXISTS workout_templates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        workout_type TEXT NOT NULL,
                        planned_distance REAL,
                        planned_intensity TEXT,
                        description TEXT,
                        notes TEXT,
                        created_at TEXT DEFAULT (datetime('now'))
                    );

                    -- Defaults
                    INSERT OR IGNORE INTO app_settings (key, value) VALUES
                        ('units', 'imperial'),
                        ('theme', 'light'),
                        ('api_key', '');
                    """
                )

    # ------------------------------------------------------------------ #
    # Settings helpers
    # ------------------------------------------------------------------ #

    def get_setting(self, key: str) -> Optional[str]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cur.fetchone()
            return row["value"] if row else None

    def set_setting(self, key: str, value: str):
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    # ---------- OpenAI API key helpers ----------

    def get_api_key(self) -> Optional[str]:
        """
        Return the API key with precedence:
        1) Environment variable OPENAI_API_KEY (if set)
        2) value from app_settings['api_key'] (if present)
        """
        env_key = os.environ.get("OPENAI_API_KEY")
        if env_key:
            return env_key.strip()
        return self.get_setting("api_key")

    def set_api_key(self, key: str | None):
        """
        Persist the API key in app_settings. If key is None/empty, stores empty string.
        NOTE: SQLite is plain text; use ENV for sensitive deployments.
        """
        self.set_setting("api_key", (key or "").strip())

    # Convenience wrappers used by UI
    def get_current_plan_id(self) -> Optional[int]:
        val = self.get_setting("current_plan_id")
        try:
            return int(val) if val not in (None, "") else None
        except Exception:
            return None

    def set_current_plan_id(self, plan_id: int):
        self.set_setting("current_plan_id", str(plan_id))

    # ------------------------------------------------------------------ #
    # Plans
    # ------------------------------------------------------------------ #

    def create_plan(self, plan_data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO plans
                (name, goal_type, start_date, race_date, duration_weeks,
                 max_days_per_week, long_run_day, weekly_increase_cap, long_run_cap, guardrails_enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan_data["name"],
                    plan_data["goal_type"],
                    plan_data["start_date"],
                    plan_data.get("race_date"),
                    int(plan_data["duration_weeks"]),
                    int(plan_data.get("max_days_per_week", 5)),
                    plan_data.get("long_run_day", "Sunday"),
                    float(plan_data.get("weekly_increase_cap", 0.10)),
                    float(plan_data.get("long_run_cap", 0.30)),
                    1 if plan_data.get("guardrails_enabled", True) else 0,
                ),
            )
            return cur.lastrowid

    def get_plan_by_id(self, plan_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_plans(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM plans ORDER BY created_at DESC")
            return [dict(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------ #
    # Baseline runs
    # ------------------------------------------------------------------ #

    def create_baseline_run(self, baseline: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO baseline_runs
                (plan_id, date, distance, time_seconds, rpe, avg_hr, elevation_gain, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    baseline["plan_id"],
                    baseline["date"],
                    baseline.get("distance"),
                    baseline.get("time_seconds"),
                    baseline.get("rpe"),
                    baseline.get("avg_hr"),
                    baseline.get("elevation_gain"),
                    baseline.get("notes"),
                ),
            )
            return cur.lastrowid

    # ------------------------------------------------------------------ #
    # Workouts (CRUD)
    # ------------------------------------------------------------------ #

    def create_workout(self, workout_data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO workouts
                (plan_id, date, version, is_current_version, workout_type, planned_distance,
                 planned_intensity, description, notes, modified_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workout_data["plan_id"],
                    workout_data["date"],
                    int(workout_data.get("version", 1)),
                    1 if workout_data.get("is_current_version", True) else 0,
                    workout_data["workout_type"],
                    workout_data.get("planned_distance"),
                    workout_data.get("planned_intensity"),
                    workout_data.get("description"),
                    workout_data.get("notes"),
                    workout_data.get("modified_by", "user"),
                ),
            )
            return cur.lastrowid

    def update_workout(self, workout_id: int, data: Dict[str, Any]):
        """
        Update fields for a workout (current version). Supports changing 'date' for rescheduling.
        Only fields present in 'data' are updated.
        """
        allowed_keys = {
            "date",
            "workout_type",
            "planned_distance",
            "planned_intensity",
            "description",
            "notes",
            "version",
            "is_current_version",
            "modified_by",
        }
        kv = [(k, v) for k, v in data.items() if k in allowed_keys]
        if not kv:
            return
        set_clause = ", ".join([f"{k} = ?" for k, _ in kv])
        values = [v for _, v in kv]
        values.append(workout_id)
        with self.get_connection() as conn:
            conn.execute(f"UPDATE workouts SET {set_clause} WHERE id = ?", values)

    def delete_workout(self, workout_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))

    def get_workouts_by_plan(self, plan_id: int, current_only: bool = True) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            if current_only:
                cur = conn.execute(
                    "SELECT * FROM workouts WHERE plan_id = ? AND is_current_version = 1 ORDER BY date ASC, id ASC",
                    (plan_id,),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM workouts WHERE plan_id = ? ORDER BY date ASC, id ASC",
                    (plan_id,),
                )
            return [dict(r) for r in cur.fetchall()]

    def get_workouts_on_date(self, plan_id: int, date_str: str, current_only: bool = True) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            if current_only:
                cur = conn.execute(
                    """
                    SELECT * FROM workouts
                    WHERE plan_id = ? AND date = ? AND is_current_version = 1
                    ORDER BY id ASC
                    """,
                    (plan_id, date_str),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT * FROM workouts
                    WHERE plan_id = ? AND date = ?
                    ORDER BY id ASC
                    """,
                    (plan_id, date_str),
                )
            return [dict(r) for r in cur.fetchall()]

    def get_workouts_between_dates(
        self, plan_id: int, start_date: str, end_date: str, current_only: bool = True
    ) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            sql = """
                SELECT * FROM workouts
                WHERE plan_id = ?
                  AND date >= ?
                  AND date <= ?
            """
            params = [plan_id, start_date, end_date]
            if current_only:
                sql += " AND is_current_version = 1"
            sql += " ORDER BY date ASC, id ASC"
            cur = conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def update_workout_completion(self, workout_id: int, completion_data: Dict[str, Any]):
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE workouts
                   SET completed = 1,
                       actual_distance = ?,
                       actual_time_seconds = ?,
                       actual_rpe = ?,
                       avg_hr = ?,
                       elevation_gain = ?,
                       completion_notes = ?,
                       completed_at = ?
                 WHERE id = ?
                """,
                (
                    completion_data.get("actual_distance"),
                    completion_data.get("actual_time_seconds"),
                    completion_data.get("actual_rpe"),
                    completion_data.get("avg_hr"),
                    completion_data.get("elevation_gain"),
                    completion_data.get("completion_notes"),
                    datetime.now().isoformat(timespec="seconds"),
                    workout_id,
                ),
            )

    # ------------------------------------------------------------------ #
    # Templates (workout_templates)
    # ------------------------------------------------------------------ #

    def get_all_templates(self) -> List[Dict[str, Any]]:
        """Return all workout templates sorted by name."""
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, name, workout_type, planned_distance, planned_intensity, description, notes, created_at
                FROM workout_templates
                ORDER BY name COLLATE NOCASE ASC
                """
            )
            return [dict(r) for r in cur.fetchall()]

    def get_template_by_id(self, template_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, name, workout_type, planned_distance, planned_intensity, description, notes, created_at
                FROM workout_templates
                WHERE id = ?
                """,
                (template_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def create_template(self, tpl: Dict[str, Any]) -> int:
        """
        Create or upsert a workout template (unique on name).
        Returns the template id.
        """
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO workout_templates
                    (name, workout_type, planned_distance, planned_intensity, description, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    workout_type      = excluded.workout_type,
                    planned_distance  = excluded.planned_distance,
                    planned_intensity = excluded.planned_intensity,
                    description       = excluded.description,
                    notes             = excluded.notes
                """,
                (
                    tpl["name"],
                    tpl["workout_type"],
                    tpl.get("planned_distance"),
                    tpl.get("planned_intensity"),
                    tpl.get("description"),
                    tpl.get("notes"),
                ),
            )
            # Return current id (works for both insert & update)
            cur = conn.execute("SELECT id FROM workout_templates WHERE name = ?", (tpl["name"],))
            row = cur.fetchone()
            return row["id"] if row else 0

    def delete_template(self, template_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM workout_templates WHERE id = ?", (template_id,))

    # --- OpenAI settings (helpers) ---
    def get_openai_settings(self) -> dict:
        return {
            "use_openai": (self.get_setting("use_openai") or "0") == "1",
            "api_key": self.get_setting("openai_api_key") or "",
            "model": self.get_setting("openai_model") or "gpt-4o-mini",
        }

    def set_openai_settings(self, use_openai: bool, api_key: str, model: str):
        self.set_setting("use_openai", "1" if use_openai else "0")
        self.set_setting("openai_api_key", api_key or "")
        self.set_setting("openai_model", model or "gpt-4o-mini")


    # ------------------------------------------------------------------ #
    # Status / AI usage
    # ------------------------------------------------------------------ #

    def get_next_key_workout(self, plan_id: int, from_date: str) -> Optional[Dict[str, Any]]:
        """
        Return the next upcoming 'key' workout on/after from_date.
        Bias to non-rest types and prefer long/tempo/intervals.
        """
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT *
                  FROM workouts
                 WHERE plan_id = ?
                   AND is_current_version = 1
                   AND date >= ?
                   AND (workout_type IS NOT NULL AND workout_type <> 'rest')
                 ORDER BY
                    CASE workout_type
                        WHEN 'long' THEN 1
                        WHEN 'tempo' THEN 2
                        WHEN 'intervals' THEN 3
                        WHEN 'easy' THEN 4
                        ELSE 5
                    END,
                    date ASC,
                    id ASC
                 LIMIT 1
                """,
                (plan_id, from_date),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def log_api_call(self, call_type: str, plan_id: int | None, tokens_used: int | None, cost_usd: float | None):
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO api_calls (plan_id, call_type, tokens_used, cost_usd) VALUES (?, ?, ?, ?)",
                (plan_id, call_type, tokens_used, cost_usd),
            )

    def get_api_totals(self) -> dict:
        with self.get_connection() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) AS n, COALESCE(SUM(tokens_used),0) AS tokens, "
                "COALESCE(SUM(cost_usd),0.0) AS cost FROM api_calls"
            )
            row = cur.fetchone()
            return {"calls": row["n"], "tokens": row["tokens"], "cost": float(row["cost"])}
