-- =============================================================================
-- Zeno — Just A Rather Very Intelligent System
-- SQLite Database Schema v1.0
-- File: ~/Zeno/Zeno.db
-- Mode: WAL (Write-Ahead Logging) for crash safety
-- =============================================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456; -- 256MB memory map


-- =============================================================================
-- SECTION 1: CORE IDENTITY & CONFIGURATION
-- =============================================================================

-- User profile and global preferences
CREATE TABLE IF NOT EXISTS user_profile (
    id                  INTEGER PRIMARY KEY CHECK (id = 1), -- singleton row
    name                TEXT    NOT NULL DEFAULT 'User',
    wake_word           TEXT    NOT NULL DEFAULT 'Hey Zeno',
    working_hours_start TEXT    NOT NULL DEFAULT '09:00',   -- HH:MM (24h)
    working_hours_end   TEXT    NOT NULL DEFAULT '19:00',
    energy_peak_start   TEXT             DEFAULT '09:00',   -- derived from analytics
    energy_peak_end     TEXT             DEFAULT '11:00',
    tts_engine          TEXT    NOT NULL DEFAULT 'pyttsx3' CHECK (tts_engine IN ('pyttsx3', 'elevenlabs', 'coqui')),
    stt_model           TEXT    NOT NULL DEFAULT 'whisper-base',
    claude_model        TEXT    NOT NULL DEFAULT 'claude-sonnet-4',
    timezone            TEXT    NOT NULL DEFAULT 'UTC',
    onboarding_complete INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Privacy exclusion rules (apps/domains Zeno must not log)
CREATE TABLE IF NOT EXISTS privacy_exclusions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    exclusion_type  TEXT NOT NULL CHECK (exclusion_type IN ('app_name', 'window_title_pattern', 'browser_domain')),
    value           TEXT NOT NULL,   -- e.g. '1Password', '*.bank.com', 'chase.com'
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO privacy_exclusions (exclusion_type, value) VALUES
    ('app_name',             '1Password'),
    ('app_name',             'Keychain Access'),
    ('browser_domain',       'banking.com'),
    ('window_title_pattern', '%password%'),
    ('window_title_pattern', '%incognito%');


-- =============================================================================
-- SECTION 2: PROJECTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    slug            TEXT    NOT NULL UNIQUE,   -- used in file paths, e.g. 'api-refactor'
    description     TEXT,
    status          TEXT    NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'paused', 'completed', 'archived')),
    color           TEXT    NOT NULL DEFAULT '#1E6FA8', -- hex, used in UI
    icon            TEXT             DEFAULT '🧩',
    workspace_id    INTEGER,         -- FK → workspaces.id (nullable — project may have no workspace)
    prd_path        TEXT,            -- path to ~/Zeno/projects/<slug>/PRD.md
    notes_path      TEXT,            -- path to ~/Zeno/projects/<slug>/notes.md
    deadline        TEXT,            -- ISO 8601 date
    estimated_hours REAL,
    actual_hours    REAL    NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    completed_at    TEXT,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_deadline ON projects(deadline);


-- =============================================================================
-- SECTION 3: TASKS
-- =============================================================================

CREATE TABLE IF NOT EXISTS tasks (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER,         -- NULL = inbox (uncategorised)
    parent_task_id      INTEGER,         -- self-ref for subtasks
    title               TEXT    NOT NULL,
    notes               TEXT,
    status              TEXT    NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'in_progress', 'blocked', 'completed', 'cancelled', 'deferred')),
    priority            TEXT    NOT NULL DEFAULT 'medium'
                                CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    source              TEXT    NOT NULL DEFAULT 'manual'
                                CHECK (source IN ('manual', 'voice', 'rubber_duck', 'imported')),
    due_date            TEXT,            -- ISO 8601 date
    due_time            TEXT,            -- HH:MM if time-specific
    estimated_minutes   INTEGER,         -- user estimate
    actual_minutes      INTEGER,         -- tracked actuals
    started_at          TEXT,
    completed_at        TEXT,
    deferred_to         TEXT,            -- ISO 8601 date (set when status = deferred)
    blocker_description TEXT,            -- what is blocking (status = blocked)
    capture_context     TEXT,            -- active project/app at capture time
    tags                TEXT,            -- JSON array e.g. '["bug","frontend"]'
    recurrence_rule     TEXT,            -- iCal RRULE string for recurring tasks
    next_occurrence     TEXT,            -- ISO 8601 — next due date for recurring tasks
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id)     REFERENCES projects(id) ON DELETE SET NULL,
    FOREIGN KEY (parent_task_id) REFERENCES tasks(id)   ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tasks_status       ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date     ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_project      ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_priority     ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_parent       ON tasks(parent_task_id);

-- Task dependency graph (task A must finish before task B can start)
CREATE TABLE IF NOT EXISTS task_dependencies (
    depends_on_task_id  INTEGER NOT NULL,
    blocked_task_id     INTEGER NOT NULL,
    PRIMARY KEY (depends_on_task_id, blocked_task_id),
    FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (blocked_task_id)    REFERENCES tasks(id) ON DELETE CASCADE
);

-- Audit log of all task status changes
CREATE TABLE IF NOT EXISTS task_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL,
    field       TEXT    NOT NULL,   -- e.g. 'status', 'priority', 'due_date'
    old_value   TEXT,
    new_value   TEXT,
    changed_by  TEXT    NOT NULL DEFAULT 'user' CHECK (changed_by IN ('user', 'Zeno', 'scheduler')),
    changed_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_history_task ON task_history(task_id);


-- =============================================================================
-- SECTION 4: SESSIONS (MEMORY)
-- =============================================================================

-- One row per work session (typically one per day, but multi-session days possible)
CREATE TABLE IF NOT EXISTS sessions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    session_date        TEXT    NOT NULL,   -- YYYY-MM-DD
    session_index       INTEGER NOT NULL DEFAULT 1, -- 1st, 2nd session of day
    started_at          TEXT    NOT NULL,
    ended_at            TEXT,
    last_active_task_id INTEGER,
    last_active_app     TEXT,
    last_active_file    TEXT,
    last_browser_tabs   TEXT,            -- JSON array of {title, url} objects
    user_notes          TEXT,            -- free-form shutdown note
    energy_level        INTEGER CHECK (energy_level BETWEEN 1 AND 10),
    focus_quality       TEXT    CHECK (focus_quality IN ('excellent', 'good', 'ok', 'scattered', 'poor')),
    mood                TEXT    CHECK (mood IN ('great', 'good', 'neutral', 'tired', 'stressed')),
    briefing_delivered  INTEGER NOT NULL DEFAULT 0, -- 0/1 flag
    markdown_path       TEXT,            -- path to ~/Zeno/sessions/YYYY-MM-DD.md
    UNIQUE (session_date, session_index),
    FOREIGN KEY (last_active_task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(session_date);

-- Pending items captured at shutdown (restored at startup)
CREATE TABLE IF NOT EXISTS session_pending_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL,
    item_type       TEXT    NOT NULL CHECK (item_type IN ('task', 'blocker', 'open_question', 'follow_up')),
    description     TEXT    NOT NULL,
    task_id         INTEGER,             -- link to tasks table if resolved
    resolved        INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id)    REFERENCES tasks(id)    ON DELETE SET NULL
);


-- =============================================================================
-- SECTION 5: TIME BLOCKS & CALENDAR
-- =============================================================================

CREATE TABLE IF NOT EXISTS time_blocks (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id             INTEGER,
    project_id          INTEGER,
    title               TEXT    NOT NULL,
    block_type          TEXT    NOT NULL DEFAULT 'work'
                                CHECK (block_type IN ('work', 'meeting', 'break', 'buffer', 'focus', 'admin')),
    date                TEXT    NOT NULL,   -- YYYY-MM-DD
    start_time          TEXT    NOT NULL,   -- HH:MM
    end_time            TEXT    NOT NULL,   -- HH:MM
    duration_minutes    INTEGER NOT NULL,
    status              TEXT    NOT NULL DEFAULT 'planned'
                                CHECK (status IN ('planned', 'active', 'completed', 'overrun', 'cancelled', 'deferred')),
    overrun_minutes     INTEGER NOT NULL DEFAULT 0,
    ical_uid            TEXT    UNIQUE,     -- link to .ics file entry
    auto_generated      INTEGER NOT NULL DEFAULT 0,  -- 1 if created by scheduler
    created_by          TEXT    NOT NULL DEFAULT 'user' CHECK (created_by IN ('user', 'Zeno')),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (task_id)    REFERENCES tasks(id)    ON DELETE SET NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_time_blocks_date   ON time_blocks(date);
CREATE INDEX IF NOT EXISTS idx_time_blocks_task   ON time_blocks(task_id);
CREATE INDEX IF NOT EXISTS idx_time_blocks_status ON time_blocks(status);

-- Rerouting decisions made by the scheduler
CREATE TABLE IF NOT EXISTS schedule_reroutings (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    triggered_at            TEXT    NOT NULL DEFAULT (datetime('now')),
    trigger_reason          TEXT    NOT NULL, -- e.g. 'task_overrun', 'new_urgent_task'
    original_block_id       INTEGER,
    action                  TEXT    NOT NULL CHECK (action IN ('deferred', 'shortened', 'swapped', 'cancelled')),
    deferred_to_date        TEXT,
    user_accepted           INTEGER,          -- NULL=not yet, 1=accepted, 0=rejected
    user_response_at        TEXT,
    FOREIGN KEY (original_block_id) REFERENCES time_blocks(id) ON DELETE SET NULL
);


-- =============================================================================
-- SECTION 6: REMINDERS
-- =============================================================================

CREATE TABLE IF NOT EXISTS reminders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         INTEGER,
    title           TEXT    NOT NULL,
    reminder_type   TEXT    NOT NULL DEFAULT 'one_time'
                            CHECK (reminder_type IN ('one_time', 'recurring', 'contextual')),
    trigger_at      TEXT,            -- ISO 8601 datetime for one_time/recurring
    recurrence_rule TEXT,            -- iCal RRULE string
    context_trigger TEXT,            -- e.g. 'on_app_open:VSCode' or 'on_project_switch:api'
    delivery_method TEXT    NOT NULL DEFAULT 'voice'
                            CHECK (delivery_method IN ('voice', 'notification', 'both')),
    message         TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'delivered', 'snoozed', 'dismissed', 'cancelled')),
    snoozed_until   TEXT,
    delivered_at    TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reminders_trigger_at ON reminders(trigger_at);
CREATE INDEX IF NOT EXISTS idx_reminders_status     ON reminders(status);


-- =============================================================================
-- SECTION 7: ACTIVITY MONITORING
-- =============================================================================

-- Raw 30-second activity samples
CREATE TABLE IF NOT EXISTS activity_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sampled_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    app_name        TEXT,
    window_title    TEXT,   -- redacted per privacy_exclusions
    project_id      INTEGER,             -- inferred from window context
    task_id         INTEGER,             -- inferred from active task
    input_level     TEXT    NOT NULL DEFAULT 'idle'
                            CHECK (input_level IN ('idle', 'light', 'moderate', 'heavy')),
    wpm_bucket      INTEGER,             -- 0, 10, 20, 30, 40, 50+ words-per-minute bucket
    is_off_task     INTEGER NOT NULL DEFAULT 0,  -- 1 if app classified as non-work
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
    FOREIGN KEY (task_id)    REFERENCES tasks(id)    ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_activity_sampled_at  ON activity_log(sampled_at);
CREATE INDEX IF NOT EXISTS idx_activity_app         ON activity_log(app_name);
CREATE INDEX IF NOT EXISTS idx_activity_project     ON activity_log(project_id);

-- Browser tab tracking (from extension via WebSocket)
CREATE TABLE IF NOT EXISTS browser_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    browser         TEXT    NOT NULL CHECK (browser IN ('chrome', 'firefox', 'edge', 'safari')),
    domain          TEXT    NOT NULL,    -- redacted per privacy_exclusions
    page_title      TEXT,
    url_category    TEXT    NOT NULL DEFAULT 'unknown'
                            CHECK (url_category IN ('work', 'research', 'social', 'video', 'news', 'email', 'unknown')),
    project_id      INTEGER,
    started_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    ended_at        TEXT,
    dwell_seconds   INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_browser_domain     ON browser_sessions(domain);
CREATE INDEX IF NOT EXISTS idx_browser_started_at ON browser_sessions(started_at);

-- Context switches (app-to-app or project-to-project)
CREATE TABLE IF NOT EXISTS context_switches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    switched_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    from_app        TEXT,
    to_app          TEXT,
    from_project_id INTEGER,
    to_project_id   INTEGER,
    switch_type     TEXT    NOT NULL CHECK (switch_type IN ('app', 'project', 'task')),
    FOREIGN KEY (from_project_id) REFERENCES projects(id) ON DELETE SET NULL,
    FOREIGN KEY (to_project_id)   REFERENCES projects(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_context_switches_at ON context_switches(switched_at);


-- =============================================================================
-- SECTION 8: ANALYTICS & INSIGHTS
-- =============================================================================

-- Pre-computed weekly analytics (regenerated every Sunday night)
CREATE TABLE IF NOT EXISTS analytics_weekly (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start                  TEXT    NOT NULL UNIQUE,  -- YYYY-MM-DD (Monday)
    week_end                    TEXT    NOT NULL,
    total_active_minutes        INTEGER NOT NULL DEFAULT 0,
    total_deep_work_minutes     INTEGER NOT NULL DEFAULT 0,  -- input_level = heavy, consecutive > 25min
    total_off_task_minutes      INTEGER NOT NULL DEFAULT 0,
    avg_context_switches_per_hr REAL,
    tasks_completed             INTEGER NOT NULL DEFAULT 0,
    tasks_deferred              INTEGER NOT NULL DEFAULT 0,
    estimation_accuracy_pct     REAL,    -- (actual / estimated) * 100
    peak_focus_hour_start       TEXT,    -- HH:MM — hour with highest sustained focus
    top_domain_off_task         TEXT,    -- most visited off-task domain
    top_project_by_time         INTEGER, -- project_id
    schedule_adherence_pct      REAL,    -- % of time blocks completed on time
    insight_summary             TEXT,    -- AI-generated narrative summary (Markdown)
    generated_at                TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (top_project_by_time) REFERENCES projects(id) ON DELETE SET NULL
);

-- Daily digest (lighter, generated each morning for briefing)
CREATE TABLE IF NOT EXISTS analytics_daily (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    date                    TEXT    NOT NULL UNIQUE,  -- YYYY-MM-DD
    active_minutes          INTEGER NOT NULL DEFAULT 0,
    deep_work_minutes       INTEGER NOT NULL DEFAULT 0,
    off_task_minutes        INTEGER NOT NULL DEFAULT 0,
    tasks_completed         INTEGER NOT NULL DEFAULT 0,
    context_switches        INTEGER NOT NULL DEFAULT 0,
    longest_focus_streak_min INTEGER NOT NULL DEFAULT 0,
    briefing_text           TEXT,    -- cached morning briefing text
    generated_at            TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Long-term behavioural patterns (updated incrementally)
CREATE TABLE IF NOT EXISTS behaviour_patterns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_key     TEXT    NOT NULL UNIQUE,
    pattern_value   TEXT    NOT NULL,    -- JSON value
    confidence      REAL    NOT NULL DEFAULT 0.5,  -- 0–1
    sample_count    INTEGER NOT NULL DEFAULT 0,
    last_updated    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Seed known pattern keys
INSERT OR IGNORE INTO behaviour_patterns (pattern_key, pattern_value, confidence) VALUES
    ('peak_focus_window',          '{"start":"09:00","end":"11:00"}', 0.5),
    ('estimation_bias_multiplier', '1.0',                             0.5),
    ('avg_pomodoro_break_minutes', '5',                               0.5),
    ('typical_session_length_min', '120',                             0.5),
    ('distraction_onset_minutes',  '45',                              0.5);


-- =============================================================================
-- SECTION 9: WORKSPACES & MACROS
-- =============================================================================

CREATE TABLE IF NOT EXISTS workspaces (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    slug            TEXT    NOT NULL UNIQUE,
    description     TEXT,
    icon            TEXT    DEFAULT '💻',
    hotkey          TEXT,            -- e.g. 'ctrl+shift+1'
    voice_trigger   TEXT,            -- e.g. 'start dev mode'
    dnd_enabled     INTEGER NOT NULL DEFAULT 1,
    dnd_minutes     INTEGER NOT NULL DEFAULT 90,
    announcement    TEXT,            -- spoken when workspace activates
    yaml_path       TEXT,            -- path to workspaces.yaml definition
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Individual steps within a workspace macro
CREATE TABLE IF NOT EXISTS workspace_steps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id    INTEGER NOT NULL,
    step_order      INTEGER NOT NULL,
    step_type       TEXT    NOT NULL CHECK (step_type IN ('open_app', 'open_url', 'focus_window', 'arrange_windows', 'toggle_dnd', 'announce', 'wait_ms')),
    target          TEXT,            -- app name, URL, or window title pattern
    params          TEXT,            -- JSON for complex params (e.g. window layout)
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_workspace_steps_workspace ON workspace_steps(workspace_id, step_order);

-- Log of workspace activations (for analytics)
CREATE TABLE IF NOT EXISTS workspace_activations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id    INTEGER NOT NULL,
    triggered_by    TEXT    NOT NULL CHECK (triggered_by IN ('voice', 'hotkey', 'auto_detect', 'morning_briefing')),
    activated_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    duration_minutes INTEGER,        -- how long this workspace was active
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);


-- =============================================================================
-- SECTION 10: VOICE & CONVERSATION
-- =============================================================================

-- Every voice utterance and its parsed intent
CREATE TABLE IF NOT EXISTS voice_interactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER,
    interacted_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    raw_transcript  TEXT    NOT NULL,
    intent_category TEXT,            -- e.g. 'task_creation', 'day_planning'
    intent_name     TEXT,            -- e.g. 'add_task', 'start_day_planning'
    slots           TEXT,            -- JSON key-value of extracted slots
    confidence      REAL,            -- STT/NLP confidence 0–1
    action_taken    TEXT,            -- what Zeno did in response
    response_text   TEXT,            -- what Zeno said back
    was_successful  INTEGER,         -- 1=success, 0=failed, NULL=no action needed
    error_message   TEXT,
    latency_ms      INTEGER,         -- end-to-end response time
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_voice_interacted_at     ON voice_interactions(interacted_at);
CREATE INDEX IF NOT EXISTS idx_voice_intent_category   ON voice_interactions(intent_category);

-- Long-running planning conversations (rubber duck mode, day planning)
CREATE TABLE IF NOT EXISTS conversations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_type TEXT  NOT NULL CHECK (conversation_type IN ('day_planning', 'rubber_duck', 'project_review', 'general')),
    project_id      INTEGER,
    started_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    ended_at        TEXT,
    turn_count      INTEGER NOT NULL DEFAULT 0,
    summary         TEXT,            -- AI-generated conversation summary
    artifacts_path  TEXT,            -- JSON array of generated file paths
    claude_thread   TEXT,            -- JSON array of {role, content} for continuity
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_conversations_type ON conversations(conversation_type);


-- =============================================================================
-- SECTION 11: NOTES & BRAIN DUMPS
-- =============================================================================

CREATE TABLE IF NOT EXISTS notes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER,
    task_id         INTEGER,
    note_type       TEXT    NOT NULL DEFAULT 'general'
                            CHECK (note_type IN ('general', 'idea', 'decision', 'question', 'reference', 'blocker')),
    title           TEXT,
    content         TEXT    NOT NULL,
    source          TEXT    NOT NULL DEFAULT 'voice'
                            CHECK (source IN ('voice', 'manual', 'rubber_duck', 'imported')),
    capture_app     TEXT,            -- active app at time of capture
    tags            TEXT,            -- JSON array
    is_pinned       INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
    FOREIGN KEY (task_id)    REFERENCES tasks(id)    ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_notes_project    ON notes(project_id);
CREATE INDEX IF NOT EXISTS idx_notes_type       ON notes(note_type);
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at);

-- FTS (Full-Text Search) for notes
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    title,
    content,
    tags,
    content='notes',
    content_rowid='id'
);

-- Keep FTS in sync
CREATE TRIGGER IF NOT EXISTS notes_fts_insert AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, title, content, tags)
    VALUES (new.id, new.title, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS notes_fts_update AFTER UPDATE ON notes BEGIN
    UPDATE notes_fts SET title=new.title, content=new.content, tags=new.tags
    WHERE rowid=new.id;
END;

CREATE TRIGGER IF NOT EXISTS notes_fts_delete AFTER DELETE ON notes BEGIN
    DELETE FROM notes_fts WHERE rowid=old.id;
END;


-- =============================================================================
-- SECTION 12: RUBBER DUCK MODE OUTPUT
-- =============================================================================

-- Projects planned via the rubber duck interrogation protocol
CREATE TABLE IF NOT EXISTS rubber_duck_sessions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER NOT NULL,
    conversation_id     INTEGER,
    problem_statement   TEXT,
    constraints         TEXT,            -- JSON array
    edge_cases          TEXT,            -- JSON array
    dependencies        TEXT,            -- JSON array
    success_criteria    TEXT,            -- JSON array
    generated_prd_path  TEXT,            -- path to generated PRD.md
    generated_risks     TEXT,            -- JSON array of {risk, likelihood, mitigation}
    milestones          TEXT,            -- JSON array of {title, target_date, tasks[]}
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id)     REFERENCES projects(id)     ON DELETE CASCADE,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
);


-- =============================================================================
-- SECTION 13: APP CLASSIFICATION (for off-task detection)
-- =============================================================================

CREATE TABLE IF NOT EXISTS app_classifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    app_name        TEXT    NOT NULL,
    domain_pattern  TEXT,            -- for browser entries
    category        TEXT    NOT NULL CHECK (category IN ('work', 'research', 'communication', 'social', 'video', 'news', 'utility', 'unknown')),
    is_work_app     INTEGER NOT NULL DEFAULT 1,
    user_override   INTEGER NOT NULL DEFAULT 0,  -- 1 = user manually set this
    confidence      REAL    NOT NULL DEFAULT 1.0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_app_class_unique ON app_classifications(app_name, COALESCE(domain_pattern, ''));

-- Seed common app classifications
INSERT OR IGNORE INTO app_classifications (app_name, category, is_work_app) VALUES
    ('Code',            'work',     1),
    ('Cursor',          'work',     1),
    ('Terminal',        'work',     1),
    ('iTerm2',          'work',     1),
    ('Xcode',           'work',     1),
    ('Figma',           'work',     1),
    ('Slack',           'communication', 1),
    ('Notion',          'work',     1),
    ('Obsidian',        'work',     1),
    ('YouTube',         'video',    0),
    ('Spotify',         'utility',  1),
    ('Twitter',         'social',   0),
    ('Reddit',          'social',   0);


-- =============================================================================
-- SECTION 14: SYSTEM EVENTS & AUDIT LOG
-- =============================================================================

CREATE TABLE IF NOT EXISTS system_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type      TEXT    NOT NULL,   -- e.g. 'startup', 'shutdown', 'macro_executed', 'api_error'
    severity        TEXT    NOT NULL DEFAULT 'info' CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),
    component       TEXT    NOT NULL,   -- e.g. 'voice_pipeline', 'macro_engine', 'scheduler'
    message         TEXT    NOT NULL,
    payload         TEXT,               -- JSON for structured data
    occurred_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_system_events_type     ON system_events(event_type);
CREATE INDEX IF NOT EXISTS idx_system_events_severity ON system_events(severity);
CREATE INDEX IF NOT EXISTS idx_system_events_time     ON system_events(occurred_at);


-- =============================================================================
-- VIEWS — Convenience queries used by the Python daemon
-- =============================================================================

-- Today's task list with project context
CREATE VIEW IF NOT EXISTS v_todays_tasks AS
SELECT
    t.id,
    t.title,
    t.status,
    t.priority,
    t.estimated_minutes,
    t.actual_minutes,
    t.due_date,
    t.due_time,
    t.blocker_description,
    p.name   AS project_name,
    p.color  AS project_color,
    p.icon   AS project_icon,
    tb.start_time AS scheduled_start,
    tb.end_time   AS scheduled_end
FROM tasks t
LEFT JOIN projects   p  ON t.project_id = p.id
LEFT JOIN time_blocks tb ON tb.task_id  = t.id AND tb.date = date('now')
WHERE t.status NOT IN ('completed','cancelled')
  AND (t.due_date IS NULL OR t.due_date >= date('now'))
ORDER BY
    CASE t.priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
    t.due_date ASC NULLS LAST;

-- Today's time blocks with task context
CREATE VIEW IF NOT EXISTS v_todays_schedule AS
SELECT
    tb.id,
    tb.start_time,
    tb.end_time,
    tb.duration_minutes,
    tb.block_type,
    tb.status,
    tb.title,
    tb.overrun_minutes,
    t.title  AS task_title,
    p.name   AS project_name,
    p.color  AS project_color
FROM time_blocks tb
LEFT JOIN tasks    t ON tb.task_id    = t.id
LEFT JOIN projects p ON tb.project_id = p.id
WHERE tb.date = date('now')
ORDER BY tb.start_time;

-- Pending tasks grouped by priority for morning briefing
CREATE VIEW IF NOT EXISTS v_morning_brief_tasks AS
SELECT
    t.id,
    t.title,
    t.priority,
    t.status,
    t.due_date,
    t.estimated_minutes,
    t.blocker_description,
    p.name AS project_name,
    CASE
        WHEN t.due_date = date('now')         THEN 'due_today'
        WHEN t.due_date = date('now','+1 day') THEN 'due_tomorrow'
        WHEN t.due_date <= date('now','+7 days') THEN 'due_this_week'
        ELSE 'upcoming'
    END AS urgency_bucket
FROM tasks t
LEFT JOIN projects p ON t.project_id = p.id
WHERE t.status IN ('pending', 'in_progress', 'blocked')
ORDER BY
    CASE WHEN t.due_date IS NOT NULL AND t.due_date <= date('now') THEN 0 ELSE 1 END,
    CASE t.priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
    t.due_date ASC NULLS LAST;

-- Weekly activity summary
CREATE VIEW IF NOT EXISTS v_weekly_activity AS
SELECT
    date(sampled_at) AS day,
    COUNT(*) * 0.5   AS active_minutes,  -- each sample = 30 seconds
    SUM(CASE WHEN input_level = 'heavy' THEN 0.5 ELSE 0 END) AS heavy_focus_minutes,
    SUM(CASE WHEN is_off_task = 1 THEN 0.5 ELSE 0 END)       AS off_task_minutes,
    COUNT(DISTINCT app_name) AS unique_apps
FROM activity_log
WHERE sampled_at >= datetime('now', '-7 days')
GROUP BY date(sampled_at)
ORDER BY day;


-- =============================================================================
-- TRIGGERS — Auto-maintenance
-- =============================================================================

-- Auto-update updated_at timestamps
CREATE TRIGGER IF NOT EXISTS trg_tasks_updated    AFTER UPDATE ON tasks    BEGIN UPDATE tasks    SET updated_at = datetime('now') WHERE id = new.id; END;
CREATE TRIGGER IF NOT EXISTS trg_projects_updated AFTER UPDATE ON projects BEGIN UPDATE projects SET updated_at = datetime('now') WHERE id = new.id; END;
CREATE TRIGGER IF NOT EXISTS trg_user_updated     AFTER UPDATE ON user_profile BEGIN UPDATE user_profile SET updated_at = datetime('now') WHERE id = new.id; END;

-- Log task status changes to history
CREATE TRIGGER IF NOT EXISTS trg_task_status_history
AFTER UPDATE OF status ON tasks
WHEN old.status != new.status
BEGIN
    INSERT INTO task_history (task_id, field, old_value, new_value, changed_by)
    VALUES (new.id, 'status', old.status, new.status, 'user');
END;

-- Auto-compute dwell_seconds on browser session close
CREATE TRIGGER IF NOT EXISTS trg_browser_dwell
AFTER UPDATE OF ended_at ON browser_sessions
WHEN new.ended_at IS NOT NULL AND old.ended_at IS NULL
BEGIN
    UPDATE browser_sessions
    SET dwell_seconds = CAST((julianday(new.ended_at) - julianday(new.started_at)) * 86400 AS INTEGER)
    WHERE id = new.id;
END;

-- =============================================================================
-- SCHEMA VERSION
-- =============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT
);

INSERT OR IGNORE INTO schema_version (version, description) VALUES
    (1, 'Initial schema — all 14 sections, views, triggers, FTS');

-- End of schema
