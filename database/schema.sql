-- =========================================================
-- RunCoach AI Database Schema (SQLite, Python build)
-- Safe to re-run on startup (IF NOT EXISTS + OR IGNORE)
-- =========================================================

PRAGMA foreign_keys = ON;

-- -----------------------
-- Training Plans
-- -----------------------
CREATE TABLE IF NOT EXISTS plans (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    goal_type           TEXT NOT NULL CHECK(goal_type IN ('5K','10K','half','marathon','fitness','maintenance')),
    start_date          DATE NOT NULL,
    race_date           DATE,
    duration_weeks      INTEGER NOT NULL,
    max_days_per_week   INTEGER DEFAULT 5,
    long_run_day        TEXT DEFAULT 'Sunday',
    weekly_increase_cap REAL DEFAULT 0.10,
    long_run_cap        REAL DEFAULT 0.30,
    guardrails_enabled  INTEGER DEFAULT 1,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------
-- Baseline Runs
-- -----------------------
CREATE TABLE IF NOT EXISTS baseline_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id         INTEGER NOT NULL,
    date            DATE NOT NULL,
    distance        REAL NOT NULL,
    time_seconds    INTEGER NOT NULL,
    rpe             INTEGER,
    avg_hr          INTEGER,
    elevation_gain  REAL,
    notes           TEXT,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- -----------------------
-- Workouts (versioned)
-- -----------------------
CREATE TABLE IF NOT EXISTS workouts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id             INTEGER NOT NULL,
    date                DATE NOT NULL,
    version             INTEGER DEFAULT 1,
    is_current_version  INTEGER DEFAULT 1,
    workout_type        TEXT NOT NULL CHECK(workout_type IN ('easy','tempo','intervals','long','recovery','rest','crosstrain')),
    planned_distance    REAL,
    planned_intensity   TEXT,
    description         TEXT,
    notes               TEXT,
    completed           INTEGER DEFAULT 0,
    actual_distance     REAL,
    actual_time_seconds INTEGER,
    actual_rpe          INTEGER,
    avg_hr              INTEGER,
    elevation_gain      REAL,
    splits              TEXT,
    shoes               TEXT,
    completion_notes    TEXT,
    completed_at        TIMESTAMP,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_by         TEXT,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
    UNIQUE(plan_id, date, version)
);

CREATE INDEX IF NOT EXISTS idx_workouts_current
    ON workouts(plan_id, date, is_current_version);

-- -----------------------
-- Plan Constraints
-- -----------------------
CREATE TABLE IF NOT EXISTS plan_constraints (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id         INTEGER NOT NULL,
    constraint_type TEXT NOT NULL,
    value           TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- -----------------------
-- Status Snapshots
-- -----------------------
CREATE TABLE IF NOT EXISTS status_snapshots (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id                 INTEGER NOT NULL,
    snapshot_date           DATE NOT NULL,
    week_number             INTEGER,
    attainability           REAL,
    status                  TEXT,
    status_label            TEXT,
    weekly_mileage_actual   REAL,
    weekly_mileage_target   REAL,
    training_load_actual    REAL,
    training_load_target    REAL,
    coach_notes             TEXT,
    recommendations         TEXT,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- -----------------------
-- API Call Log
-- -----------------------
CREATE TABLE IF NOT EXISTS api_calls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id     INTEGER,
    call_type   TEXT NOT NULL,
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tokens_used INTEGER,
    cost_usd    REAL,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- -----------------------
-- App Settings (key/value)
-- -----------------------
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Seed defaults (split inserts; each has 2 values matching 2 columns)
INSERT OR IGNORE INTO app_settings (key, value) VALUES ('units', 'imperial');
INSERT OR IGNORE INTO app_settings (key, value) VALUES ('theme', 'light');
INSERT OR IGNORE INTO app_settings (key, value) VALUES ('api_key', '');

-- =========================================================
-- Workout Templates
-- =========================================================
CREATE TABLE IF NOT EXISTS workout_templates (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL UNIQUE,
    workout_type      TEXT NOT NULL CHECK(workout_type IN ('easy','tempo','intervals','long','recovery','rest','crosstrain')),
    planned_distance  REAL,
    planned_intensity TEXT,
    description       TEXT,
    notes             TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_templates_type ON workout_templates(workout_type);

-- Starter templates (each statement = 6 columns → 6 values)
INSERT OR IGNORE INTO workout_templates (name, workout_type, planned_distance, planned_intensity, description, notes)
VALUES ('Easy Run 5mi',      'easy',       5.0,  NULL, 'Steady conversational pace',                     NULL);

INSERT OR IGNORE INTO workout_templates (name, workout_type, planned_distance, planned_intensity, description, notes)
VALUES ('Tempo 4mi',         'tempo',      4.0,  NULL, 'Comfortably hard, controlled',                   NULL);

INSERT OR IGNORE INTO workout_templates (name, workout_type, planned_distance, planned_intensity, description, notes)
VALUES ('Intervals 8x400m',  'intervals',  NULL, '8x400m @ 5K pace, 200m jog',                           'Track session', NULL);

INSERT OR IGNORE INTO workout_templates (name, workout_type, planned_distance, planned_intensity, description, notes)
VALUES ('Long Run 10mi',     'long',       10.0, NULL, 'Keep it aerobic; gel around 45–60 min',          NULL);

INSERT OR IGNORE INTO workout_templates (name, workout_type, planned_distance, planned_intensity, description, notes)
VALUES ('Recovery Day',      'recovery',   NULL, NULL, 'Short, easy; focus on form and cadence',         NULL);

INSERT OR IGNORE INTO workout_templates (name, workout_type, planned_distance, planned_intensity, description, notes)
VALUES ('Cross-Train 45min', 'crosstrain', NULL, '45 min bike or swim @ easy effort',                    'Cross-training session', NULL);

INSERT OR IGNORE INTO workout_templates (name, workout_type, planned_distance, planned_intensity, description, notes)
VALUES ('Rest Day',          'rest',       NULL, NULL, 'Recovery day',                                   NULL);
