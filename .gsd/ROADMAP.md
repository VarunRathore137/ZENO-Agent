# ZENO — Project Roadmap

> Last updated: 2026-04-30
> Total phases: 9

---

## Milestone 1 — Foundation & Core Backend

### Phase 1: Project Scaffold & Database Bootstrap
Set up the Python project structure, virtual environment, dependency manifest (`requirements.txt`, `pyproject.toml`), and initialize the SQLite database by running `zeno_schema.sql`. Create the `config.yaml` loader and `user_profile` singleton initializer. Establish the `~/Zeno/` directory layout.

**Deliverables:**
- `pyproject.toml` + `requirements.txt` with all planned Python deps
- `zeno/db.py` — SQLite connection factory (WAL mode, FK ON, mmap)
- `zeno/config.py` — YAML config loader + `user_profile` sync
- `~/Zeno/Zeno.db` initialized from schema
- `~/Zeno/config.yaml` default template

---

### Phase 2: Voice Pipeline — Wake Word & STT
Implement the voice input pipeline: continuous microphone capture, wake word detection ("Hey Zeno"), and Whisper-based speech-to-text transcription. Support hotkey fallbacks (`Ctrl+Shift+Space`, `Ctrl+Shift+J`). Output raw transcript strings for downstream processing.

**Deliverables:**
- `zeno/voice/capture.py` — Microphone capture (sounddevice)
- `zeno/voice/wake_word.py` — Wake word detection loop
- `zeno/voice/transcriber.py` — Whisper STT wrapper
- `zeno/voice/hotkeys.py` — Global hotkey registration
- Unit tests for transcriber mock

---

### Phase 3: NLP Intent Parser
Build the rule-based NLP intent classifier supporting all 10 categories and 52 named intents. Implement 31 slot extractors (temporal, entity, scalar/enum). Add multi-intent splitting via conjunctions. Implement confidence scoring (threshold 0.75 → clarification trigger). Output structured JSON intent objects.

**Deliverables:**
- `zeno/nlp/classifier.py` — Intent classification engine
- `zeno/nlp/slots.py` — Slot extractor (all 31 types)
- `zeno/nlp/splitter.py` — Multi-intent conjunction splitter
- `zeno/nlp/intent_schema.py` — Pydantic intent object schema
- Unit tests covering all 52 intents with sample utterances

---

### Phase 4: Action Dispatcher & Core Task/Session Handlers
Implement the action dispatcher that routes intent objects to handler functions. Build handlers for `task_*` (full CRUD on `tasks` table) and `session_*` (session lifecycle: startup load, shutdown write, pending items). This is the backbone that connects voice input to database state.

**Deliverables:**
- `zeno/dispatcher/router.py` — Intent → handler routing table
- `zeno/handlers/tasks.py` — Task CRUD handlers
- `zeno/handlers/sessions.py` — Session lifecycle handlers
- `zeno/handlers/notes.py` — Notes + FTS5 handlers
- `zeno/handlers/reminders.py` — Reminder CRUD handlers
- Integration tests: voice command → DB state verified

---

## Milestone 2 — AI, Scheduling & Productivity Features

### Phase 5: Claude API Engine & Rubber Duck Mode
Integrate the Claude API wrapper for AI-powered features. Implement the rubber duck mode 6-state conversation machine (`PROBLEM → CONSTRAINTS → EDGE_CASES → DEPS → CRITERIA → GENERATING`), PRD generation written to project directories, and task extraction from generated PRDs. Also implement morning briefing generation.

**Deliverables:**
- `zeno/ai/claude_client.py` — Anthropic API wrapper with retry logic
- `zeno/ai/briefing.py` — Morning briefing prompt + parser
- `zeno/ai/rubber_duck.py` — 6-state conversation machine
- `zeno/ai/prd_writer.py` — PRD.md file writer + task extractor
- `rubber_duck_sessions` and `projects/<slug>/PRD.md` wiring

---

### Phase 6: TTS Engine & Scheduler
Implement the TTS engine (pyttsx3 default, ElevenLabs/Coqui optional) switchable per `user_profile.tts_engine`. Implement APScheduler-based job management: morning briefing delivery, reminder firing, weekly analytics regeneration, Pomodoro focus timer callbacks.

**Deliverables:**
- `zeno/tts/engine.py` — Unified TTS interface + provider factory
- `zeno/tts/providers/pyttsx3_provider.py`
- `zeno/tts/providers/elevenlabs_provider.py`
- `zeno/scheduler/jobs.py` — All scheduled job definitions
- `zeno/scheduler/runner.py` — APScheduler setup + lifecycle

---

### Phase 7: Macro Engine & Workspace Management
Build the macro engine that executes workspace setup sequences. Implement all 7 step types (`open_app`, `open_url`, `focus_window`, `arrange_windows`, `toggle_dnd`, `announce`, `wait_ms`). Load workspace definitions from `workspaces.yaml`. Enforce `app_classifications` whitelist for safety.

**Deliverables:**
- `zeno/macros/engine.py` — Macro execution runtime
- `zeno/macros/steps.py` — All 7 step type executors (Windows API)
- `zeno/macros/loader.py` — `workspaces.yaml` parser
- `zeno/macros/safety.py` — Whitelist enforcement
- Handler wiring: `workspace_*` intents → Macro Engine

---

## Milestone 3 — Passive Monitoring & UI

### Phase 8: Activity Monitor & Browser Extension
Implement the 30-second passive activity monitor (window sampling, `app_name`, `window_title`, `input_level`, `wpm_bucket`, `is_off_task`). Build the browser extension (Chrome/Firefox/Edge) with WebSocket client sending tab URL and dwell time to the Python daemon. Implement privacy redaction via `privacy_exclusions`.

**Deliverables:**
- `zeno/monitor/activity.py` — 30-second sampling loop
- `zeno/monitor/privacy.py` — `privacy_exclusions` redaction
- `zeno/extension/manifest.json` + `background.js` + `content.js`
- WebSocket server in Python daemon for extension messages
- Writes verified to `activity_log` and `browser_sessions`

---

### Phase 9: Tauri UI Shell & Analytics Dashboard
Scaffold the Tauri desktop application with React/TypeScript frontend. Implement: system tray icon + quick capture, brain dump hotkey overlay, analytics dashboard with charts (deep work, distraction breakdown), morning briefing display, task/schedule management UI, and settings panel.

**Deliverables:**
- `src-tauri/` — Tauri Rust shell (tray, IPC, window management)
- `frontend/` — React/TypeScript app (vite scaffold)
- `frontend/components/Dashboard.tsx` — Analytics charts
- `frontend/components/BriefingPanel.tsx` — Morning briefing
- `frontend/components/Overlay.tsx` — Brain dump hotkey overlay
- `frontend/components/Settings.tsx` — Settings panel
- Full IPC bridge between Tauri and Python daemon

---

## Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 1 | Project Scaffold & Database Bootstrap | ⬜ Not planned |
| 2 | Voice Pipeline — Wake Word & STT | ⬜ Not planned |
| 3 | NLP Intent Parser | ⬜ Not planned |
| 4 | Action Dispatcher & Core Handlers | ⬜ Not planned |
| 5 | Claude API Engine & Rubber Duck Mode | ⬜ Not planned |
| 6 | TTS Engine & Scheduler | ⬜ Not planned |
| 7 | Macro Engine & Workspace Management | ⬜ Not planned |
| 8 | Activity Monitor & Browser Extension | ⬜ Not planned |
| 9 | Tauri UI Shell & Analytics Dashboard | ⬜ Not planned |
