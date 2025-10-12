-- RunCoach AI Database Schema (Python/SQLite)

-- Training Plans
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

-- Baseline Runs
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

-- Workouts (Versioned)
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

CREATE INDEX IF NOT EXISTS idx_workouts_current ON workouts(plan_id, date, is_current_version);

-- Plan Constraints
CREATE TABLE IF NOT EXISTS plan_constraints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL,
    constraint_type TEXT NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- Status Snapshots
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

-- API Call Log
CREATE TABLE IF NOT EXISTS api_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER,
    call_type TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tokens_used INTEGER,
    cost_usd REAL,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- App Settings
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO app_settings (key, value) VALUES
    ('units', 'imperial'),
    ('theme', 'light'),
    ('api_key', '');