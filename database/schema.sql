-- RunCoach AI Database Schema (Python/SQLite)

PRAGMA foreign_keys = ON;

-- =========================================
-- Training Plans
-- =========================================
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    goal_type TEXT NOT NULL CHECK(goal_type IN ('5K', '10K', 'half', 'marathon', 'fitness', 'maintenance')),
    start_date DATE NOT NULL,
    race_date DATE,
    duration_weeks INTEGER NOT NULL,
    max_days_per_week INTEGER DEFAULT 5,
    long_run_day TEXT DEFAULT 'Sunday',
    weekly_increase_cap REAL DEFAULT 0.10,
    long_run_cap REAL DEFAULT 0.30,
    guardrails_enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Touch last_modified on plan updates
CREATE TRIGGER IF NOT EXISTS trg_plans_touch_last_modified
AFTER UPDATE ON plans
BEGIN
    UPDATE plans
       SET last_modified = CURRENT_TIMESTAMP
     WHERE id = NEW.id;
END;

-- =========================================
-- Baseline Runs
-- =========================================
CREATE TABLE IF NOT EXISTS baseline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL,
    date DATE NOT NULL,
    distance REAL NOT NULL,
    time_seconds INTEGER NOT NULL,
    rpe INTEGER,
    avg_hr INTEGER,
    elevation_gain REAL,
    notes TEXT,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- =========================================
-- Workouts (Versioned)
-- =========================================
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL,
    date DATE NOT NULL,
    version INTEGER DEFAULT 1,
    is_current_version BOOLEAN DEFAULT 1,
    workout_type TEXT NOT NULL CHECK(workout_type IN ('easy', 'tempo', 'intervals', 'long', 'recovery', 'rest', 'crosstrain')),
    planned_distance REAL,
    planned_intensity TEXT,
    description TEXT,
    notes TEXT,
    completed BOOLEAN DEFAULT 0,
    actual_distance REAL,
    actual_time_seconds INTEGER,
    actual_rpe INTEGER,
    avg_hr INTEGER,
    elevation_gain REAL,
    splits TEXT,
    shoes TEXT,
    completion_notes TEXT,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_by TEXT,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
    UNIQUE(plan_id, date, version)
);

-- Speed up "current" queries
CREATE INDEX IF NOT EXISTS idx_workouts_current ON workouts(plan_id, date, is_current_version);

-- View for "current version only"
CREATE VIEW IF NOT EXISTS v_workouts_current AS
SELECT *
  FROM workouts
 WHERE is_current_version = 1;

-- Ensure only one current version per (plan_id, date)
CREATE TRIGGER IF NOT EXISTS trg_workouts_current_exclusive_ins
AFTER INSERT ON workouts
WHEN NEW.is_current_version = 1
BEGIN
    UPDATE workouts
       SET is_current_version = 0
     WHERE plan_id = NEW.plan_id
       AND date    = NEW.date
       AND id     != NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_workouts_current_exclusive_upd
AFTER UPDATE OF is_current_version ON workouts
WHEN NEW.is_current_version = 1
BEGIN
    UPDATE workouts
       SET is_current_version = 0
     WHERE plan_id = NEW.plan_id
       AND date    = NEW.date
       AND id     != NEW.id;
END;

-- =========================================
-- Plan Constraints
-- =========================================
CREATE TABLE IF NOT EXISTS plan_constraints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL,
    constraint_type TEXT NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- =========================================
-- Status Snapshots
-- =========================================
CREATE TABLE IF NOT EXISTS status_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL,
    snapshot_date DATE NOT NULL,
    week_number INTEGER,
    attainability REAL,
    status TEXT,
    status_label TEXT,
    weekly_mileage_actual REAL,
    weekly_mileage_target REAL,
    training_load_actual REAL,
    training_load_target REAL,
    coach_notes TEXT,
    recommendations TEXT,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- =========================================
-- API Call Log
-- =========================================
CREATE TABLE IF NOT EXISTS api_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER,
    call_type TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tokens_used INTEGER,
    cost_usd REAL,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- =========================================
-- App Settings
-- =========================================
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO app_settings (key, value) VALUES
    ('units', 'imperial'),
    ('theme', 'light'),
    ('api_key', '');

-- =========================================
-- Workout Templates (presets)
-- =========================================
CREATE TABLE IF NOT EXISTS workout_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    workout_type TEXT NOT NULL CHECK(workout_type IN ('easy', 'tempo', 'intervals', 'long', 'recovery', 'rest', 'crosstrain')),
    planned_distance REAL,
    planned_intensity TEXT,
    description TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Optional starter templates
INSERT OR IGNORE INTO workout_templates (name, workout_type, planned_distance, planned_intensity, description, notes)
VALUES
  ('Easy Run 5mi', 'easy', 5.0, NULL, 'Steady conversational pace', NULL),
  ('Tempo 4mi', 'tempo', 4.0, NULL, 'Comfortably hard, controlled', NULL),
  ('Intervals 8x400m', 'intervals', NULL, '8x400m @ 5K pace, 200m jog', 'Track session'),
  ('Long Run 10mi', 'long', 10.0, NULL, 'Keep it aerobic; gel around 45–60 min', NULL),
  ('Rest Day', 'rest', NULL, NULL, 'Recovery day', NULL);
