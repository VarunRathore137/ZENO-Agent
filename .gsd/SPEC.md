# ZENO — Product Specification

> Status: FINALIZED
> Version: 1.0
> Date: 2026-04-30

---

## Product Summary

ZENO (Just A Rather Very Intelligent System) is a **voice-first, locally-running personal AI assistant** for developers and knowledge workers. It runs as a native Windows desktop application (Tauri shell) with a Python backend daemon.

ZENO listens for a configurable wake word ("Hey Zeno"), transcribes speech via OpenAI Whisper, classifies intent using a rule-based NLP parser (falling back to the Claude API for ambiguous or complex tasks), and dispatches structured actions against a local SQLite database. Passive monitoring (app activity, browser tabs) feeds an analytics pipeline that generates morning briefings and focus insights.

**Privacy-first:** All data stays local. External calls limited to Claude API (reasoning/generation) and optionally ElevenLabs (premium TTS).

---

## Core Requirements

### R1 — Voice Pipeline
- Wake word detection: "Hey Zeno" (10s timeout) and "Zeno, <command>" (session mode)
- Hotkey fallbacks: `Ctrl+Shift+Space` (brain dump overlay), `Ctrl+Shift+J` held (push-to-talk)
- STT via OpenAI Whisper (`whisper-base` configurable)
- Output: raw transcript → NLP Intent Parser

### R2 — NLP Intent Parser
- 10 intent categories, 52 named intents
- 31 slot types: temporal (date, duration, range), entity (task_ref, project_ref, app_name), scalar/enum (priority, mood, block_type)
- Confidence threshold: 0.75 — below this triggers clarification dialog (max 2 rounds)
- Multi-intent splitting via conjunctions
- Output: structured JSON intent object `{intent_category, intent_name, slots, confidence, raw_transcript}`

### R3 — Action Dispatcher
- Routes resolved intent objects to handler functions:
  - `task_*` → SQLite `tasks` CRUD
  - `session_*` → SQLite `sessions` + file writes
  - `workspace_*` → Macro Engine
  - `reminder_*` → APScheduler + SQLite `reminders`
  - `analytics_*` → SQLite views / analytics tables
  - `rubber_duck_*` → Claude API Engine + file writes
  - `notes_*` → SQLite `notes` + FTS5

### R4 — SQLite Database (`Zeno.db`)
- WAL mode, foreign keys ON, 256MB mmap
- 14 schema sections, 22 concrete tables + 1 FTS5 virtual table
- 4 convenience views: `v_todays_tasks`, `v_todays_schedule`, `v_morning_brief_tasks`, `v_weekly_activity`
- 7 auto-maintenance triggers, 25+ indexes
- Schema version: 1.0 (source: `zeno_schema.sql`)

### R5 — Claude API Engine
- Model: `claude-sonnet-4` (configurable in `user_profile`)
- Powers: morning briefings, rubber duck PRD generation, weekly insight narratives, slot inference, clarification disambiguation
- Input context sourced from: session files, SQLite queries, `behaviour_patterns`
- Output: Markdown text, task lists, PRD documents, JSON

### R6 — Macro Engine
- Executes workspace setup sequences
- Step types: `open_app`, `open_url`, `focus_window`, `arrange_windows`, `toggle_dnd`, `announce`, `wait_ms`
- Safety: all actions filtered through `app_classifications` whitelist — no arbitrary shell commands

### R7 — TTS Engine
- Default: `pyttsx3` (offline)
- Optional: `elevenlabs` (premium cloud), `coqui` (offline alternative)
- Configurable per `user_profile.tts_engine`

### R8 — Activity Monitor
- 30-second passive sampling of active window
- Captures: `app_name`, `window_title`, `input_level`, `wpm_bucket`, `is_off_task`
- Privacy: window titles redacted per `privacy_exclusions` before storage
- Writes to: `activity_log`, `context_switches`

### R9 — Browser Extension
- Tracks active tabs, domain dwell time, URL categories
- Communicates via WebSocket to Python daemon
- Supported browsers: Chrome, Firefox, Edge, Safari
- Writes to: `browser_sessions`

### R10 — Tauri UI Shell
- System tray icon + right-click quick capture
- Hotkey-triggered brain dump overlay (non-focus-stealing)
- Analytics dashboard (deep work charts, distraction breakdown)
- Morning briefing display
- Task and schedule management UI
- Settings panel

### R11 — Scheduler (APScheduler)
- Morning briefing delivery (startup or configurable time)
- Reminder firing (`reminders.trigger_at`)
- Weekly analytics regeneration (Sunday night)
- Focus timer check-ins (Pomodoro mid-point + end)

### R12 — Session Lifecycle
**Startup:** Load last session → query pending items → generate morning briefing (Claude) → offer workspace setup
**Shutdown:** Snapshot active context → prompt for shutdown notes (up to 3 exchanges) → write session row → save DB snapshot

### R13 — Rubber Duck Mode
- 6-state conversation: `PROBLEM → CONSTRAINTS → EDGE_CASES → DEPS → CRITERIA → GENERATING`
- Builds `rubber_duck_sessions` row incrementally
- Generates PRD.md via Claude API written to `~/Zeno/projects/<slug>/`
- Extracts tasks from PRD and inserts into `tasks` table

### R14 — Multi-Turn Dialogue Flows
| Flow | Entry | States | Exit |
|------|-------|--------|------|
| Day Planning | `start_day_planning` | LOADING → PRESENTING → BLOCKING → CONFIRMING → DONE | User confirms or cancels |
| Rubber Duck | `start_rubber_duck` | PROBLEM → CONSTRAINTS → EDGE_CASES → DEPS → CRITERIA → GENERATING | Files written |
| Shutdown Ritual | `initiate_shutdown` | CAPTURING → PROMPTING → SAVING → DONE | "done" or 90s timeout |
| Re-routing | `rebalance_schedule` | ANALYSING → PROPOSING → AWAITING → APPLYING | All items resolved |
| Clarification | *(auto)* | CLARIFYING → RESOLVED / ABANDONED | Max 2 rounds |

---

## Non-Functional Requirements

- **Privacy:** All window/browser data checked against `privacy_exclusions` before storage
- **Performance:** Voice round-trip (wake word → TTS response) target < 3 seconds on local hardware
- **Offline-first:** All core features work without internet; Claude API and ElevenLabs are optional enhancements
- **Platform:** Windows primary target (Windows 10/11); macOS stretch goal
- **Config duality:** Runtime config in `user_profile` SQLite singleton + `config.yaml` for human editing
- **No arbitrary shell execution:** Macro Engine restricted to `app_classifications` whitelist

---

## File System Layout

```
~/Zeno/
├── Zeno.db                   # SQLite database (WAL)
├── config.yaml               # User preferences
├── workspaces.yaml           # Workspace macro definitions
├── calendar.ics              # Local calendar
├── sessions/YYYY-MM-DD.md    # Daily session files
├── projects/<slug>/          # Per-project PRDs + notes
├── voice/                    # STT/wake word Python module
├── nlp/                      # Intent parser Python module
├── ai/                       # Claude API wrapper Python module
├── dispatcher/               # Action dispatcher Python module
├── macros/                   # Macro engine Python module
├── tts/                      # TTS engine Python module
├── monitor/                  # Activity monitor Python module
├── scheduler/                # APScheduler jobs Python module
└── extension/                # Browser extension source
```

---

## Environment Variables Required

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API authentication |
| `ELEVENLABS_API_KEY` | ElevenLabs TTS (optional) |

---

## Source Artifacts

- `zeno_schema.sql` — Full 720-line SQLite schema (source of truth for DB)
- `gen_grammar.js` — Voice grammar document generator (48KB, Node.js)
- `ARCHITECTURE.md` — System architecture reference
- `STACK.md` — Technology stack reference
- `Zeno_component_interaction.svg` — Component interaction diagram
- `ZENO_PRD.docx` — Original product requirements document
