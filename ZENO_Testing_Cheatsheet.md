# ZENO Testing Cheatsheet
> Built from actual source code — every command, port, hotkey, and intent is real.

---

## 1. ⚡ HOW TO ACTIVATE ZENO

### A. Manual CLI Start (2 Terminals)

**Terminal 1 — Python Daemon (voice + API)**
```powershell
# from project root
cd d:\Codes\Projects\ZENO-My-Personal-Assisstant

# Optional: enable verbose debug logs
$env:ZENO_DEBUG = "1"
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # if not already set

python -m zeno
```
> ✅ Listens on:
> - `localhost:8766` — FastAPI REST (dashboard data)
> - `localhost:8765` — WebSocket (browser extension IPC)
> - Global hotkeys active immediately

**Terminal 2 — React Frontend (browser UI)**
```powershell
cd d:\Codes\Projects\ZENO-My-Personal-Assisstant\frontend
npm run dev
# → open http://localhost:5173 in your browser
```

---

### B. Tauri Desktop App (Single Binary)
```powershell
cd d:\Codes\Projects\ZENO-My-Personal-Assisstant
# Dev mode (hot reload)
npm run tauri dev

# OR build & install
npm run tauri build
# Installer lands in: src-tauri/target/release/bundle/
```
> The Tauri app embeds the React UI and manages the system tray icon automatically.

---

### C. Auto-Start on PC Boot (Windows Task Scheduler)
```powershell
# Run once to register (as Admin)
schtasks /Create /TN "ZENO Daemon" /TR "python -m zeno" /SC ONLOGON /RU "%USERNAME%" /RL HIGHEST /F

# Verify it's registered
schtasks /Query /TN "ZENO Daemon"

# Manual trigger (for testing without reboot)
schtasks /Run /TN "ZENO Daemon"

# Remove it
schtasks /Delete /TN "ZENO Daemon" /F
```
> 💡 Set `ANTHROPIC_API_KEY` as a **System** environment variable so the scheduled task inherits it.

---

### D. System Tray (Tauri App)
Once the Tauri app is running, ZENO lives in the system tray (bottom-right).

| Tray Action | What It Does |
|---|---|
| **Left-click icon** | Show/raise the main window |
| **Right-click → Focus Mode ON/OFF** | POSTs `/daemon/focus` → toggles distraction blocking |
| **Right-click → Mute Voice** | POSTs `/daemon/tts/mute` → silences TTS responses |
| **Right-click → Quit** | POSTs `/daemon/shutdown` → graceful stop |

---

### E. Global Hotkeys (Always Active Once Daemon Runs)

| Hotkey | Action | Code Reference |
|---|---|---|
| `Ctrl + Shift + Space` | **Brain Dump Overlay** — pops the quick-capture overlay window | `hotkeys.py:60` |
| `Ctrl + Shift + J` | **Push-to-Talk** — hold to speak, release to process | `hotkeys.py:61` |

---

### F. Wake Word (Voice, Any Interface)

> ZENO uses `openwakeword` with the `hey_jarvis` model (threshold: 0.5).
> The microphone is always open when the daemon is running.

**Configured wake phrases** (from `config.py`):
```
Hey Zeno          Okay Zeno         Yo Zeno
Hey Zeno wake up  Wake up Zeno      Zen wake up
Hey Zen           Hello Zeno        Yo Zen          Hi Zen
```

**How to trigger from ANY app/interface:**
- Just say the wake phrase out loud — ZENO's mic capture runs in the background
- Works while: coding in VS Code, watching YouTube, on a video call (use headset mic)
- After the wake word fires → ZENO starts recording your command → auto-stops on silence

---

### G. Browser Extension IPC (WebSocket `ws://localhost:8765`)
The browser extension connects to ZENO's WebSocket server. ZENO can receive the current page title and URL from the browser.

**Test the raw WebSocket connection:**
```javascript
// In browser DevTools console
const ws = new WebSocket('ws://localhost:8765');
ws.onmessage = e => console.log(JSON.parse(e.data));
ws.send(JSON.stringify({ type: 'ping' }));
```

---

### H. Direct REST API (Test Without Voice)
```powershell
# Check system vitals
Invoke-RestMethod http://localhost:8766/system

# Get today's tasks
Invoke-RestMethod http://localhost:8766/tasks

# Get today's briefing (session markdown)
Invoke-RestMethod http://localhost:8766/briefing

# Get 7-day analytics
Invoke-RestMethod http://localhost:8766/analytics

# Get user settings
Invoke-RestMethod http://localhost:8766/settings

# Toggle focus mode
Invoke-RestMethod -Method POST http://localhost:8766/daemon/focus

# Mute TTS
Invoke-RestMethod -Method POST http://localhost:8766/daemon/tts/mute

# Shutdown
Invoke-RestMethod -Method POST http://localhost:8766/daemon/shutdown
```

---

### I. Live Log Monitor
```powershell
# Stream logs in real-time
Get-Content -Path "$env:USERPROFILE\Zeno\logs\zeno.log" -Wait

# Or watch with tail equivalent
Get-Content "$env:USERPROFILE\Zeno\logs\zeno.log" -Tail 50 -Wait
```

---

## 2. 🎙️ FUNCTIONALITIES TO TEST

### Voice Commands → Intent Handlers

> Say wake word first, then the command. Confidence threshold: 75%.

#### 📋 Task Management

| Say This | Maps to Intent | Handler |
|---|---|---|
| `"Add task fix the login bug"` | `add_task` | `handlers/tasks.py` |
| `"New task: write unit tests"` | `add_task` | Creates DB row with `source='voice'` |
| `"Create a task to review PR 47 high priority"` | `add_task` | Extracts `priority=high` slot |
| `"Add task deploy staging due tomorrow"` | `add_task` | Extracts `due_date` slot |
| `"What are my tasks for today?"` | `query_tasks` | Reads `v_todays_tasks` view |
| `"Show me everything blocked"` | `query_tasks` | Lists today's tasks (top 5) |
| `"What high priority tasks are pending?"` | `query_tasks` | |
| `"Mark the login bug as done"` | `complete_task` | `UPDATE tasks SET status='completed'` |
| `"I finished writing the API docs"` | `complete_task` | Fuzzy matches task title |
| `"Change the deadline on the report to Thursday"` | `update_task` | (classified, handler TBD) |

#### 📝 Notes & Ideas

| Say This | Maps to Intent | Handler |
|---|---|---|
| `"Capture idea: use Redis for session caching"` | `capture_idea` | `handlers/notes.py` → `notes` table |
| `"Note this down: the API rate limit is 1000/day"` | `capture_idea` | Stored as `note_type='idea'` |
| `"Search my notes for authentication"` | `search_notes` | FTS5 full-text search |
| `"Find notes about Redis"` | `search_notes` | Returns top 3 matches |

#### ⏰ Reminders

| Say This | Maps to Intent | Handler |
|---|---|---|
| `"Set a reminder to push the code in 2 hours"` | `set_reminder` | `handlers/reminders.py` |
| `"Remind me to check the build tomorrow"` | `set_reminder` | Extracts date slot |
| `"What reminders do I have?"` | `list_reminders` | Lists active reminders |

#### 🏢 Workspace Control

| Say This | Maps to Intent | Handler |
|---|---|---|
| `"Start dev mode"` | `activate_workspace` / `setup_workspace` | `handlers/workspaces.py` → MacroEngine |
| `"Set up coding workspace"` | `setup_workspace` | Opens VS Code + GitHub + enables DND |
| `"Switch to writing workspace"` | `setup_workspace` | Opens Notion + enables DND |
| `"List my workspaces"` | `list_workspaces` | Reads `~/Zeno/workspaces.yaml` |
| `"Allow VS Code in macros"` | `register_workspace_app` | Adds to allowed apps allowlist |
| `"Enable DND"` | `enable_focus_mode` | (classified, wired to focus toggle) |
| `"Focus mode for 45 minutes"` | `enable_focus_mode` | Extracts `45` → `estimated_minutes` slot |
| `"Don't disturb me for an hour"` | `enable_focus_mode` | Extracts `60` → `estimated_minutes` |

#### 📅 Sessions & Day Planning

| Say This | Maps to Intent | Handler |
|---|---|---|
| `"Let's plan my day"` | `start_day_planning` | (classified) |
| `"Start new session"` | `start_new_session` | `INSERT INTO sessions` |
| `"What's my schedule for today?"` | `query_schedule` | (classified) |
| `"Shut down for today"` | `initiate_shutdown` | Updates `sessions.ended_at` |
| `"Good work, ending session"` | `initiate_shutdown` | "Good work today" response |

#### 🦆 Rubber Duck Debugging (AI-Assisted)
| Say This | Effect |
|---|---|
| `"Let's rubber duck the auth bug"` | Starts `RubberDuckSession` for project slug `auth-bug` |
| `"Resume rubber duck on ZENO project"` | Resumes latest in-progress session |

---

### UI Interactive Actions (Frontend)

| Panel | What To Test |
|---|---|
| **Sidebar → DASHBOARD** | System vitals load (CPU, RAM, Battery, GPU) — polls `/system` |
| **Sidebar → BRIEFING** | Today's markdown session file renders |
| **Sidebar → TASKS** | Shows task list from DB; placeholder shows voice hint |
| **Sidebar → SETTINGS** | User profile from DB: wake word, TTS engine, STT model, working hours |
| **System Bar** (top) | Realtime CPU/RAM stats, date/time, TTS active indicator |
| **Arc Reactor** | ZENO logo animation — pulses when TTS is active |
| **Overlay** (hotkey) | Press `Ctrl+Shift+Space` → overlay window appears over any app |
| **Focus Mode toggle** | Tray → Focus Mode / REST POST → watch `focus_mode` flip in `/system` |
| **TTS mute toggle** | Tray → Mute Voice / REST POST → watch `tts_muted` flip in `/system` |

---

### Go to Background / System Tray (Hide UI Mid-Task)

| Method | Command / Action |
|---|---|
| **Voice → minimize** | Say: `"Hey Zeno, go to background"` → (maps to `initiate_shutdown` or tray hide) |
| **Voice → hide UI** | Say: `"Hey Zeno, hide yourself"` / `"minimize the window"` |
| **Tray click** | Click anywhere outside Tauri window or click tray icon to toggle |
| **Keyboard** | `Win + D` to show desktop (Tauri window minimizes like any app) |
| **REST API** | `POST /daemon/focus` — activates focus mode, window can hide |
| **Task Scheduler** | Run daemon headless (no Tauri), open frontend only when needed |

> **Power pattern**: Start daemon via Task Scheduler (no window), work all day, access UI only when needed via tray icon. ZENO operates 100% in background with voice.

---

## 3. 🔧 USEFUL ENGINEERING TASKS TO AUTOMATE WITH ZENO

These create **real value** — things you love handing off:

### Code & Project Workflow
```
"Hey Zeno, set up coding workspace"
→ Opens VS Code, GitHub, enables DND, maximizes VS Code

"Add task: review PR 23 for the auth refactor — high priority due tomorrow"
→ Persisted in DB, shows in dashboard tomorrow morning

"Note this: learned that SQLite WAL mode prevents read lock contention"
→ Captured idea, searchable later

"Search notes for WAL"
→ Finds your note instantly
```

### Focus & Deep Work Sessions
```
"Hey Zeno, focus mode for 2 hours"
→ Enables DND, blocks distractions, logs session start

"Hey Zeno, what tasks are pending?"
→ ZENO reads out today's task list while you keep eyes on screen

"Hey Zeno, mark PR review as done"
→ Marks complete without touching keyboard
```

### End of Day / Session
```
"Hey Zeno, shut down for today"
→ Closes session, timestamps it, ready for tomorrow's briefing

"Hey Zeno, add task: write standup update"
→ Creates reminder for tomorrow morning
```

### Rubber Duck Debugging (Most Underrated Feature)
```
"Hey Zeno, let's rubber duck the memory leak in the monitor module"
→ Starts structured AI-guided debug session
→ ZENO asks: What is the problem? What did you try? What's the expected behavior?
→ All answers saved in session for context continuity
```

### Notes During Coding (No Context Switch)
```
While in VS Code, without switching windows:
"Hey Zeno, capture idea: move the scheduler polling interval to config"
"Hey Zeno, capture idea: the FTS5 query needs escaping for special chars"
"Hey Zeno, note this: Tauri's invoke bridge has a 4MB payload limit"
```

### Workspace Switching
```
"Hey Zeno, switch to writing workspace"
→ Opens Notion, enables DND

"Hey Zeno, list my workspaces"
→ ZENO reads available workspaces from workspaces.yaml
```

### System Awareness
```
# In browser, dashboard auto-refreshes every ~5s:
- CPU/RAM/Battery/GPU % live
- Deep work vs distraction time (7-day chart)
- Today's session briefing (markdown rendered)
```

---

## 4. 🧠 KEEPING ZENO CONVERSATIONAL (Context-Aware)

### Current Context Mechanism
ZENO maintains context through:
1. **Sessions table** — open session = active context window
2. **Briefing files** — `~/Zeno/sessions/YYYY-MM-DD.md` is today's running log
3. **RubberDuckSession state** — multi-turn problem-solving state machine
4. **Browser extension** — current page title/URL sent to daemon via WS

### How To Make It Conversational NOW

**Pattern 1 — Open a session at start of day:**
```
"Hey Zeno, start new session"
→ All subsequent tasks/notes auto-tagged to this session
→ View: BRIEFING tab shows everything captured today
```

**Pattern 2 — Use rubber duck for problem context:**
```
"Hey Zeno, let's rubber duck the Tauri IPC bug"
→ ZENO tracks: problem statement, hypotheses, what was tried
→ Next day: "Resume rubber duck on Tauri IPC" → gets full context back
```

**Pattern 3 — Brain dump before switching context:**
```
Press Ctrl+Shift+Space → Overlay appears
Type or speak everything on your mind
→ Captures to notes DB → ZENO can reference it
```

**Pattern 4 — Query your own context:**
```
"Hey Zeno, search notes for Tauri"
"Hey Zeno, what are my tasks today?"
"Hey Zeno, show today's briefing"
→ ZENO answers from your own stored context, not generic AI
```

### Conversational Loop Best Practices
```
Morning:   "Hey Zeno, start new session"
           → ZENO reads morning briefing (yesterday's summary + today's tasks)

Working:   Say commands hands-free, ZENO confirms each one
           Tasks/notes accumulate in DB throughout the day

Thinking:  "Hey Zeno, let's rubber duck [problem]"
           → Multi-turn dialogue, ZENO guides you through the problem

Switching: "Hey Zeno, switch to writing workspace"
           → Environment resets, context preserved in DB

Evening:   "Hey Zeno, shut down for today"
           → Session closes, briefing file finalized for tomorrow
```

---

## 5. 🔮 PLANNING FOR FUTURE ZENO MODES

### Proposed Mode Architecture

Each mode = a named profile with: different wake word sensitivity, TTS verbosity, active workspaces, focus level, and intent priority.

```yaml
# Future: ~/Zeno/modes.yaml
modes:
  deep_work:
    description: "Maximum focus, minimal interruptions"
    focus_mode: true
    tts_verbosity: minimal        # only critical responses
    wake_word_sensitivity: low    # harder to accidentally trigger
    active_workspaces: [coding]
    allowed_intents: [add_task, capture_idea, query_tasks]
    blocked_intents: [set_reminder, start_day_planning]  # avoid rabbit holes
    activity_monitor: strict      # flags off-task apps immediately

  planning:
    description: "Strategic thinking, task organization"
    focus_mode: false
    tts_verbosity: full           # ZENO is chatty, reads lists aloud
    wake_word_sensitivity: high
    active_workspaces: []
    allowed_intents: [all]
    rubber_duck_mode: true        # AI-guided thinking enabled

  presentation:
    description: "Demos, standups, screen sharing"
    focus_mode: false
    tts_verbosity: silent         # no voice output (embarrassing in meetings)
    wake_word_sensitivity: off    # don't accidentally trigger
    ui_compact: true              # minimized dashboard
    overlay_disabled: true

  learning:
    description: "Reading docs, studying, exploring new tech"
    focus_mode: partial           # DND on, but notes allowed
    tts_verbosity: medium
    browser_context: true         # ZENO reads page titles → topic-aware notes
    active_workspaces: []
    rubber_duck_mode: true

  creative:
    description: "Writing, design, brainstorming"
    focus_mode: true
    tts_verbosity: medium
    active_workspaces: [writing]
    brain_dump_hotkey: enhanced   # extra quick capture
    idea_capture_priority: high
```

### How To Trigger Modes (Future Voice Commands)
```
"Hey Zeno, enter deep work mode"
"Hey Zeno, switch to planning mode"
"Hey Zeno, presentation mode"
"Hey Zeno, learning mode"
"Hey Zeno, go creative"
```

### Implementation Roadmap for Modes
```
Phase A: Mode config file (modes.yaml) + mode switcher handler
Phase B: Mode-aware intent filter (block/allow intents per mode)
Phase C: Mode-aware TTS verbosity (minimal/medium/full/silent)
Phase D: Auto-mode detection (time of day, calendar events, active app)
Phase E: Mode transition announcements + session tagging
Phase F: Mode analytics (how many hours in each mode per week)
```

### Auto-Mode Ideas (Triggered Automatically)
| Trigger | Suggested Mode |
|---|---|
| Calendar event = "standup" | → `presentation` mode auto-activates |
| Calendar event = "deep work block" | → `deep_work` mode |
| Active app = Notion/Obsidian | → `writing` mode |
| Active app = VS Code + no meetings | → `deep_work` mode |
| Time = 8:00–8:30 AM | → `planning` mode (morning briefing window) |
| Time = after 6 PM | → `learning` mode (wind-down) |
| Browser = YouTube/Reddit for 10+ min | → ZENO flags off-task, suggests mode |

---

## 🗂️ Quick Reference Card

```
PORTS:        Backend REST → :8766    |    WS/Extension → :8765
DB:           ~/Zeno/Zeno.db          |    Config: ~/Zeno/config.yaml
Logs:         ~/Zeno/logs/zeno.log    |    Sessions: ~/Zeno/sessions/YYYY-MM-DD.md
Workspaces:   workspaces.yaml (project root or ~/Zeno/)

HOTKEYS:      Ctrl+Shift+Space → Overlay    |    Ctrl+Shift+J → Push-To-Talk (hold)
WAKE WORDS:   "Hey Zeno" / "Okay Zeno" / "Hey Zen" / "Hi Zen"
TRAY ACTIONS: Focus Mode  |  Mute Voice  |  Quit

CONFIDENCE THRESHOLD: 75% (fuzzy NLP — flexible phrasing works)
```
