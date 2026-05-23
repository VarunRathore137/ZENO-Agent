const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, LevelFormat, PageBreak, PageNumber
} = require('docx');
const fs = require('fs');

const NAVY   = "0D2137";
const BLUE   = "1565C0";
const BLUE2  = "1E88E5";
const SLATE  = "37474F";
const LIGHT  = "E8F4FD";
const LIGHT2 = "F0F4F8";
const WHITE  = "FFFFFF";
const GREEN  = "1B5E20";
const GLIGHT = "E8F5E9";
const AMBER  = "E65100";
const ALIGHT = "FFF3E0";
const PURPLE = "4A148C";
const PLIGHT = "F3E5F5";
const RED    = "B71C1C";
const RLIGHT = "FFEBEE";

const b1 = { style: BorderStyle.SINGLE, size: 1, color: "D0D7DE" };
const brd = { top: b1, bottom: b1, left: b1, right: b1 };
const noBrd = {
  top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE },
  left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE }
};

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: BLUE2, space: 6 } },
    children: [new TextRun({ text, font: "Arial", size: 32, bold: true, color: NAVY })]
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 100 },
    children: [new TextRun({ text, font: "Arial", size: 26, bold: true, color: BLUE })]
  });
}
function h3(text, color = SLATE) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 80 },
    children: [new TextRun({ text, font: "Arial", size: 22, bold: true, color })]
  });
}
function body(text, opts = {}) {
  return new Paragraph({
    spacing: { before: 60, after: 80 },
    children: [new TextRun({ text, font: "Arial", size: 20, color: NAVY, ...opts })]
  });
}
function code(text) {
  return new Paragraph({
    spacing: { before: 40, after: 40 },
    indent: { left: 360 },
    children: [new TextRun({ text, font: "Courier New", size: 18, color: SLATE })]
  });
}
function bullet(text, bold = false, color = NAVY) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 }, spacing: { before: 40, after: 60 },
    children: [new TextRun({ text, font: "Arial", size: 20, color, bold })]
  });
}
function spacer(n = 1) {
  return new Paragraph({ spacing: { before: 0, after: n * 80 }, children: [new TextRun("")] });
}
function pb() { return new Paragraph({ children: [new PageBreak()] }); }

function cell(text, fill = WHITE, textColor = NAVY, bold = false, w = 1440) {
  return new TableCell({
    borders: brd, width: { size: w, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      children: [new TextRun({ text, font: "Arial", size: 18, color: textColor, bold })]
    })]
  });
}

function headerRow(cols, widths) {
  return new TableRow({
    tableHeader: true,
    children: cols.map((c, i) => new TableCell({
      borders: brd, width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: NAVY, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({
        children: [new TextRun({ text: c, font: "Arial", size: 18, bold: true, color: WHITE })]
      })]
    }))
  });
}

function intentTable(rows, widths) {
  const cols = ["Intent", "Example Utterances", "Required Slots", "Optional Slots", "Action Taken", "Response Pattern"];
  return new Table({
    width: { size: widths.reduce((a,b)=>a+b,0), type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      headerRow(cols, widths),
      ...rows.map((row, ri) => new TableRow({
        children: row.map((c, ci) => {
          const isEven = ri % 2 === 0;
          return new TableCell({
            borders: brd,
            width: { size: widths[ci], type: WidthType.DXA },
            shading: { fill: isEven ? WHITE : LIGHT2, type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            verticalAlign: "top",
            children: c.split('\n').map(line =>
              new Paragraph({ spacing: { before: 0, after: 40 },
                children: [new TextRun({ text: line, font: "Arial", size: 17, color: NAVY })]
              })
            )
          });
        })
      }))
    ]
  });
}

function slotTable(rows) {
  const ws = [1600, 1400, 1600, 4760];
  return new Table({
    width: { size: 9360, type: WidthType.DXA }, columnWidths: ws,
    rows: [
      headerRow(["Slot Name", "Type", "Examples", "Notes"], ws),
      ...rows.map((row, ri) => new TableRow({
        children: row.map((c, ci) => new TableCell({
          borders: brd, width: { size: ws[ci], type: WidthType.DXA },
          shading: { fill: ri%2===0 ? WHITE : LIGHT2, type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({ children: [
            new TextRun({ text: c, font: ci===0 ? "Courier New" : "Arial", size: 17, color: NAVY })
          ]})]
        }))
      }))
    ]
  });
}

function badgeBlock(label, color, bg) {
  return new Paragraph({
    spacing: { before: 160, after: 80 },
    shading: { fill: bg, type: ShadingType.CLEAR },
    border: { left: { style: BorderStyle.SINGLE, size: 20, color, space: 0 } },
    indent: { left: 180 },
    children: [new TextRun({ text: `  ${label}`, font: "Arial", size: 20, bold: true, color })]
  });
}

// =============================================================
const iw = [900, 1600, 1200, 1200, 1900, 2560]; // Intent table col widths = 9360

const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }
      ]}
    ]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: NAVY },
        paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: BLUE },
        paragraph: { spacing: { before: 280, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: SLATE },
        paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 } }
    ]
  },
  sections: [{
    properties: {
      page: { size: { width: 15840, height: 12240 }, // Landscape Letter
        margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } }
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: BLUE2, space: 4 } },
        spacing: { after: 80 },
        children: [
          new TextRun({ text: "Zeno  |  Voice Command Grammar & Intent Taxonomy  |  v1.0", font: "Arial", size: 16, color: SLATE }),
          new TextRun({ text: "     April 2026", font: "Arial", size: 16, color: SLATE, italics: true })
        ]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        border: { top: { style: BorderStyle.SINGLE, size: 6, color: BLUE2, space: 4 } },
        alignment: AlignmentType.CENTER, spacing: { before: 80 },
        children: [new TextRun({ text: "Confidential — Internal Reference  |  Zeno NLP Specification", font: "Arial", size: 16, color: SLATE })]
      })] })
    },
    children: [

      // ─── COVER ─────────────────────────────────────────────
      spacer(1),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 60 },
        children: [new TextRun({ text: "Zeno", font: "Arial", size: 72, bold: true, color: NAVY })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 80 },
        children: [new TextRun({ text: "Voice Command Grammar & Intent Taxonomy", font: "Arial", size: 32, bold: true, color: BLUE })] }),
      new Paragraph({
        alignment: AlignmentType.CENTER, spacing: { before: 80, after: 80 },
        border: { top: { style: BorderStyle.SINGLE, size: 10, color: BLUE2 }, bottom: { style: BorderStyle.SINGLE, size: 10, color: BLUE2 } },
        children: [new TextRun({ text: "Complete NLP Specification — 10 Intent Categories — 52 Named Intents — 31 Slot Types", font: "Arial", size: 22, color: SLATE })]
      }),
      spacer(1),
      new Table({
        width: { size: 9360, type: WidthType.DXA }, columnWidths: [2400, 6960],
        rows: [
          ["Version", "1.0 — Initial Specification"],
          ["Date", "April 2026"],
          ["Status", "Draft — Ready for NLP Engineering"],
          ["Covers", "STT pipeline, intent parsing, slot extraction, action dispatch, response patterns"],
          ["Categories", "10 intent categories with 52 named intents"],
          ["Slot Types", "31 typed slots (temporal, entity, boolean, enum, free-text)"],
        ].map(([l, v], ri) => new TableRow({
          children: [
            new TableCell({ borders: brd, width: { size: 2400, type: WidthType.DXA },
              shading: { fill: NAVY, type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 120, right: 120 },
              children: [new Paragraph({ children: [new TextRun({ text: l, font: "Arial", size: 18, bold: true, color: WHITE })] })] }),
            new TableCell({ borders: brd, width: { size: 6960, type: WidthType.DXA },
              shading: { fill: ri%2===0?WHITE:LIGHT2, type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 120, right: 120 },
              children: [new Paragraph({ children: [new TextRun({ text: v, font: "Arial", size: 18, color: NAVY })] })] })
          ]
        }))
      }),
      spacer(2),

      pb(),

      // ─── SECTION 1: OVERVIEW ──────────────────────────────────
      h1("1. Overview & Grammar Design Principles"),
      body("Every voice command Zeno receives passes through a 4-stage pipeline: Speech-to-Text → Utterance Normalisation → Intent Classification → Slot Extraction. The output is a structured intent object that drives the action dispatcher."),
      spacer(1),
      h2("1.1 Intent Object Schema"),
      code("{"),
      code('  "intent_category": "task_management",'),
      code('  "intent_name":     "add_task",'),
      code('  "slots": {'),
      code('    "title":    "fix WebSocket reconnect bug",'),
      code('    "due_date": "2026-05-02",'),
      code('    "priority": "high"'),
      code("  },"),
      code('  "confidence":    0.94,'),
      code('  "raw_transcript":"add a high priority task fix the websocket reconnect bug due friday"'),
      code("}"),
      spacer(1),
      h2("1.2 Grammar Conventions"),
      bullet("Square brackets [ ] indicate optional words: 'add [a] task' matches 'add task' and 'add a task'"),
      bullet("Angle brackets < > indicate a slot value placeholder: 'due <date>' captures the date expression"),
      bullet("Pipe | separates synonyms: 'add | create | new' means any of these words activates the intent"),
      bullet("Asterisk * means zero or more additional words: 'remind me * in <duration>' is flexible in phrasing"),
      bullet("Intent confidence threshold: 0.75 minimum. Below this, Zeno asks for clarification."),
      bullet("Multi-intent utterances are split at conjunctions: 'Add task X and remind me in 30 minutes' produces two intent objects."),
      spacer(1),
      h2("1.3 Wake Word & Activation"),
      new Table({
        width: { size: 9360, type: WidthType.DXA }, columnWidths: [2400, 2400, 4560],
        rows: [
          headerRow(["Activation Mode", "Trigger", "Behaviour"], [2400, 2400, 4560]),
          ...[
            ["Primary wake word", '"Hey Zeno" (configurable)', "Activates microphone for full command; 10s timeout"],
            ["Session mode", '"Zeno, <command>"', "Single command in active session; no timeout"],
            ["Brain dump hotkey", "Ctrl+Shift+Space", "Non-intrusive overlay; no focus steal; auto-dismiss"],
            ["Push-to-talk fallback", "Ctrl+Shift+J held", "Records while held; releases on key-up"],
            ["Keyword trigger", "Configurable secondary word", "E.g. 'Atlas' or 'Assistant' as alternate wake word"],
          ].map((row, ri) => new TableRow({
            children: row.map((c, ci) => new TableCell({
              borders: brd, width: { size: [2400,2400,4560][ci], type: WidthType.DXA },
              shading: { fill: ri%2===0?WHITE:LIGHT2, type: ShadingType.CLEAR },
              margins: { top: 60, bottom: 60, left: 120, right: 120 },
              children: [new Paragraph({ children: [new TextRun({ text: c, font: "Arial", size: 18, color: NAVY })] })]
            }))
          }))
        ]
      }),
      spacer(1),

      pb(),

      // ─── SECTION 2: TASK MANAGEMENT ──────────────────────────
      badgeBlock("CATEGORY 01  |  Task Management", BLUE, LIGHT),
      h2("2. Task Management"),
      body("Intent group covering creation, modification, querying, and closure of tasks. This is the most frequently used category and supports the richest set of natural language variations."),
      spacer(1),
      intentTable([
        [
          "add_task",
          '"Add task fix the login bug due Friday high priority"\n"New task: write unit tests for the parser"\n"Create a task to review PR 47 for tomorrow"',
          "title",
          "due_date\npriority\nproject\nestimate",
          "INSERT tasks; infer project from active window; notify confirmation",
          '"Task added: [title] — due [date], [priority] priority."'
        ],
        [
          "query_tasks",
          '"What are my tasks for today?"\n"Show me everything blocked"\n"What high priority tasks are pending?"',
          "—",
          "status_filter\npriority_filter\ndate_filter\nproject_filter",
          "SELECT from v_todays_tasks; read results aloud",
          '"You have [N] tasks today: [list of titles with priority]."'
        ],
        [
          "complete_task",
          '"Mark the login bug as done"\n"Complete the unit test task"\n"I finished writing the API docs"',
          "task_ref\n(title or index)",
          "actual_duration",
          "UPDATE tasks SET status='completed'; log actual_minutes",
          '"Done. [task] marked complete. That took [duration]."'
        ],
        [
          "update_task",
          '"Change the deadline on the report to Thursday"\n"Move the API task to high priority"\n"Estimate for the test task is 2 hours"',
          "task_ref\nfield\nnew_value",
          "—",
          "UPDATE tasks; log to task_history",
          '"Updated: [field] on [task] changed to [new_value]."'
        ],
        [
          "defer_task",
          '"Push the email task to tomorrow"\n"Defer the design review to next week"\n"Move the report to Monday"',
          "task_ref\ndefer_to_date",
          "reason",
          "UPDATE tasks SET status='deferred', deferred_to=date",
          '"[task] deferred to [date]. I\'ll remind you then."'
        ],
        [
          "flag_blocker",
          '"I\'m blocked on the API task waiting for design approval"\n"Flag the report as blocked — need client data"\n"Mark the parser task blocked on PR review"',
          "task_ref\nblocker_description",
          "—",
          "UPDATE tasks SET status='blocked', blocker_description=text",
          '"Got it. [task] flagged as blocked. I\'ll follow up in 24 hours."'
        ],
        [
          "list_blocked",
          '"What\'s blocking me right now?"\n"Show all my blockers"\n"What tasks are waiting on something?"',
          "—",
          "project_filter",
          "SELECT tasks WHERE status='blocked'",
          '"You have [N] blocked tasks: [list with blockers]."'
        ],
        [
          "add_subtask",
          '"Add a subtask to the API feature: write the endpoint first"\n"Break down the report task: first outline, then draft, then review"',
          "parent_task_ref\nsubtask_title",
          "order\nestimate",
          "INSERT tasks with parent_task_id",
          '"Subtask added to [parent]: [subtask title]."'
        ],
      ], iw),
      spacer(2),

      pb(),

      // ─── SECTION 3: DAY PLANNING ─────────────────────────────
      badgeBlock("CATEGORY 02  |  Day Planning & Scheduling", GREEN, GLIGHT),
      h2("3. Day Planning & Scheduling"),
      body("Intent group for interactive day planning, time-blocking, schedule queries, and dynamic re-routing. These intents often trigger multi-turn conversations."),
      spacer(1),
      intentTable([
        [
          "start_day_planning",
          '"Let\'s plan my day"\n"I want to build my schedule for today"\n"Help me plan today"',
          "—",
          "date\nfocus_area",
          "Load pending tasks + calendar; enter planning conversation mode",
          '"Good [morning/afternoon]. You have [N] pending tasks and [M] calendar events. Want to go through them?"'
        ],
        [
          "assign_time_block",
          '"Give the API bug 2 hours"\n"Schedule the report from 10 to 1"\n"Block 90 minutes for email after lunch"',
          "task_or_label\nduration or\nstart+end_time",
          "date\nblock_type",
          "INSERT time_blocks; write to calendar.ics",
          '"Blocked [duration] for [task] at [time]. That fills your schedule until [end_time]."'
        ],
        [
          "query_schedule",
          '"What\'s my schedule for today?"\n"What am I doing this afternoon?"\n"When\'s my next meeting?"',
          "—",
          "date\ntime_range",
          "SELECT from v_todays_schedule; read aloud",
          '"Your next block is [task] from [start] to [end]. After that, [next block]."'
        ],
        [
          "rebalance_schedule",
          '"Recalculate my schedule"\n"The bug is taking longer — re-route everything"\n"Adjust my day, I\'m running 2 hours behind"',
          "—",
          "overrun_minutes\nprotected_tasks",
          "Run re-routing algorithm; propose deferrals; await confirmation",
          '"I\'ve re-calculated. I suggest deferring [tasks] to tomorrow. Shall I apply this?"'
        ],
        [
          "find_free_slot",
          '"Find me a 2-hour deep work slot today"\n"When can I fit in the report writing?"\n"Is there time for a focus block this afternoon?"',
          "duration",
          "block_type\ntime_preference",
          "Scan time_blocks for gaps; respect calendar events",
          '"Your next [duration] free slot is [time range]. Want me to block it for [task]?"'
        ],
        [
          "prioritise_tasks",
          '"What should I work on first?"\n"What\'s the most important thing right now?"\n"Given my deadlines, what do I tackle next?"',
          "—",
          "project_filter",
          "Score tasks by priority×urgency×deadline; present top 3",
          '"Based on your deadlines and priorities, I recommend: 1) [task] — due [date], 2) [task], 3) [task]."'
        ],
      ], iw),
      spacer(2),

      pb(),

      // ─── SECTION 4: SESSION CONTROL ──────────────────────────
      badgeBlock("CATEGORY 03  |  Session Control (Memory)", AMBER, ALIGHT),
      h2("4. Session Control — Startup & Shutdown"),
      body("Intent group managing Zeno's memory system: shutdown rituals, startup briefings, and historical context queries."),
      spacer(1),
      intentTable([
        [
          "initiate_shutdown",
          '"Zeno, shutting down"\n"I\'m done for the day"\n"End session"',
          "—",
          "energy_level\nmood\nfocus_quality",
          "Enter shutdown ritual: capture context, prompt for notes, write session file, save DB snapshot",
          '"Got it. Before you go — any final notes? [pause] Saving your session. See you tomorrow."'
        ],
        [
          "deliver_briefing",
          '"What was I working on yesterday?"\n"Give me my morning briefing"\n"Where did I leave off?"',
          "—",
          "date",
          "Load latest session file; generate briefing via Claude; read aloud",
          '"Yesterday you were working on [task]. You left with [N] pending items. Your top priority today should be [task] — it\'s due [date]."'
        ],
        [
          "query_history",
          '"What was I doing last Tuesday?"\n"When did I complete the API feature?"\n"How much time did I spend on the dashboard last week?"',
          "date_or_range",
          "project_filter\ntask_filter",
          "Query sessions + activity_log for date range",
          '"On [date] you spent [N] hours on [project], mainly working on [tasks]."'
        ],
        [
          "add_shutdown_note",
          '"Note for tomorrow: check the Redis connection timeout"\n"Remember to ping Jake about the spec"\n"Save this before I shut down: the bug is in line 124"',
          "note_text",
          "task_ref\ndate",
          "INSERT session_pending_items or notes; link to current session",
          '"Saved. I\'ll remind you about this first thing tomorrow."'
        ],
        [
          "start_new_session",
          '"I\'m starting a new session"\n"Beginning work"\n"Start Zeno"',
          "—",
          "project_focus",
          "Load last session; check calendar; generate briefing; offer workspace setup",
          '"Welcome back. [briefing]. Shall I set up your [project] workspace?"'
        ],
      ], iw),
      spacer(2),

      pb(),

      // ─── SECTION 5: PROJECT PLANNING ──────────────────────────
      badgeBlock("CATEGORY 04  |  Project Planning (Rubber Duck Mode)", PURPLE, PLIGHT),
      h2("5. Project Planning — Rubber Duck Interrogation Mode"),
      body("Intent group that activates structured Socratic dialogue. Zeno becomes an interrogator rather than an executor. It asks questions, captures answers, and generates project artifacts."),
      spacer(1),
      intentTable([
        [
          "start_rubber_duck",
          '"Let\'s plan the new dashboard feature"\n"Help me think through this architecture"\n"I want to architect the auth refactor"',
          "project_name_or_topic",
          "project_id",
          "Enter rubber_duck conversation mode; load interrogation protocol; begin with problem statement",
          '"Understood. Before we plan anything, let\'s nail down the constraints. What is the single core outcome this needs to deliver?"'
        ],
        [
          "define_constraint",
          '"The deadline is end of May"\n"We\'re stuck with React — can\'t change the stack"\n"Budget is 40 hours total"',
          "constraint_text",
          "constraint_type",
          "Append to rubber_duck_sessions.constraints JSON",
          '"Got it — [constraint] noted. What are the top 3 ways this could go wrong?"'
        ],
        [
          "define_edge_case",
          '"If the network drops mid-upload we lose the file"\n"Edge case: user logs out during payment flow"\n"What if the API rate-limits us at peak load?"',
          "edge_case_text",
          "severity",
          "Append to rubber_duck_sessions.edge_cases; flag in risk register",
          '"Good catch. That\'s in the risk register. Any other failure modes?"'
        ],
        [
          "generate_prd",
          '"Generate the PRD now"\n"I think we have enough — write the spec"\n"Create the project document"',
          "—",
          "format\ninclude_roadmap",
          "Send session transcript to Claude API; generate PRD.md; save to ~/Zeno/projects/<slug>/",
          '"PRD generated and saved. I\'ve created [N] tasks and a [N]-milestone roadmap. Want me to add them to your schedule?"'
        ],
        [
          "query_project_status",
          '"How\'s the dashboard project going?"\n"What\'s the status of the API refactor?"\n"Give me a progress report on project X"',
          "project_ref",
          "—",
          "JOIN projects+tasks; compute % complete; read last session notes",
          '"[Project] is [N]% complete. [M] tasks done, [K] pending, [J] blocked. [Key insight from notes]."'
        ],
      ], iw),
      spacer(2),

      pb(),

      // ─── SECTION 6: WORKSPACE CONTROL ────────────────────────
      badgeBlock("CATEGORY 05  |  Workspace Control", NAVY, LIGHT),
      h2("6. Workspace Control"),
      body("Intent group for activating and managing contextual workspace macros. All actions execute from a user-defined whitelist — no arbitrary shell commands."),
      spacer(1),
      intentTable([
        [
          "activate_workspace",
          '"Start dev mode"\n"Switch to writing workspace"\n"I\'m beginning the data analysis project"\n"Load my design workspace"',
          "workspace_name_or_slug",
          "—",
          "Look up workspace_steps; execute whitelist macro sequence; announce on completion",
          '"[Workspace] workspace ready. I\'ve opened [apps], loaded [URLs], and enabled DND for [N] minutes."'
        ],
        [
          "query_workspaces",
          '"What workspaces do I have set up?"\n"List my workspace profiles"\n"What does my dev workspace open?"',
          "—",
          "workspace_filter",
          "SELECT from workspaces + workspace_steps; read aloud",
          '"You have [N] workspaces: [list]. Your dev workspace opens [apps]."'
        ],
        [
          "enable_focus_mode",
          '"Enable DND"\n"Focus mode for 45 minutes"\n"Don\'t disturb me for an hour"\n"Block distractions"',
          "—",
          "duration_minutes",
          "Toggle system DND; start focus timer; monitor off-task activity",
          '"Focus mode on. I\'ll check in with you in [N] minutes."'
        ],
        [
          "disable_focus_mode",
          '"Turn off DND"\n"Exit focus mode"\n"I\'m taking a break now"',
          "—",
          "—",
          "Disable DND; pause off-task monitoring; log focus session stats",
          '"Focus mode off. You stayed on-task for [N] of [M] minutes — nice work."'
        ],
        [
          "open_application",
          '"Open VS Code"\n"Launch Figma"\n"Can you open my terminal?"',
          "app_name",
          "—",
          "Validate against app_classifications whitelist; subprocess.Popen",
          '"Opening [app_name]."'
        ],
        [
          "open_url",
          '"Open the React documentation"\n"Load my GitHub repo in the browser"\n"Go to the project Notion page"',
          "url_or_label",
          "—",
          "Validate against URL allowlist; webbrowser.open()",
          '"Opening [URL] in your browser."'
        ],
      ], iw),
      spacer(2),

      pb(),

      // ─── SECTION 7: REMINDERS & TIMERS ───────────────────────
      badgeBlock("CATEGORY 06  |  Reminders & Timers", GREEN, GLIGHT),
      h2("7. Reminders & Timers"),
      body("Intent group for setting, querying, and managing reminders, countdowns, and Pomodoro-style focus timers."),
      spacer(1),
      intentTable([
        [
          "set_reminder",
          '"Remind me in 2 hours to check the data bug"\n"Remind me at 4pm about the client call"\n"Set a reminder for tomorrow morning: review PR 47"',
          "reminder_text\ntrigger_time",
          "task_ref\ndelivery_method",
          "INSERT reminders; schedule via APScheduler",
          '"Reminder set for [time]: [text]."'
        ],
        [
          "start_timer",
          '"Set a 25-minute Pomodoro"\n"Start a 45-minute focus timer"\n"Time me for 30 minutes"',
          "duration_minutes",
          "label\npomodoro_count",
          "Start APScheduler countdown; announce halfway and at end",
          '"Timer started. I\'ll check in at [halfway] and let you know when [N] minutes are up."'
        ],
        [
          "cancel_reminder",
          '"Cancel the 4pm reminder"\n"Delete the client call reminder"\n"Remove all my reminders for today"',
          "reminder_ref",
          "—",
          "UPDATE reminders SET status='cancelled'",
          '"Cancelled: [reminder description]."'
        ],
        [
          "snooze_reminder",
          '"Snooze that for 20 minutes"\n"Remind me again in an hour"\n"Not now — come back to this in 30 minutes"',
          "duration_minutes",
          "—",
          "UPDATE reminders SET status='snoozed', snoozed_until=datetime",
          '"Snoozed. I\'ll remind you again at [new_time]."'
        ],
        [
          "list_reminders",
          '"What reminders do I have today?"\n"Show my upcoming reminders"\n"What have I got set?"',
          "—",
          "date_filter",
          "SELECT from reminders WHERE status='pending' ORDER BY trigger_at",
          '"You have [N] reminders today: [list with times]."'
        ],
        [
          "break_reminder",
          '"Take a break"\n"I\'m going for a break"\n"5-minute break now"',
          "—",
          "duration_minutes",
          "Pause focus monitoring; start break timer; resume monitoring after",
          '"Break started. Back at it in [N] minutes."'
        ],
      ], iw),
      spacer(2),

      pb(),

      // ─── SECTION 8: ANALYTICS ────────────────────────────────
      badgeBlock("CATEGORY 07  |  Analytics & Performance Insights", AMBER, ALIGHT),
      h2("8. Analytics & Performance Insights"),
      body("Intent group for querying Zeno's passive analytics — time-on-task, distraction patterns, productivity trends, and estimation accuracy."),
      spacer(1),
      intentTable([
        [
          "query_daily_analytics",
          '"How did I do today?"\n"Give me a performance summary"\n"How much deep work did I get done today?"',
          "—",
          "date",
          "SELECT from analytics_daily WHERE date=today; read narrative",
          '"Today: [N] hours active, [M] hours deep work, [K] context switches, [J] tasks completed."'
        ],
        [
          "query_weekly_report",
          '"How was my week?"\n"Give me a weekly performance report"\n"What were my productivity patterns this week?"',
          "—",
          "week_start",
          "SELECT from analytics_weekly; read insight_summary aloud",
          '"This week you averaged [N] hours of deep work per day. Your peak focus window was [time]. [Key insight]."'
        ],
        [
          "query_peak_hours",
          '"When am I most productive?"\n"What time of day is my peak focus window?"\n"When should I schedule deep work?"',
          "—",
          "—",
          "Query behaviour_patterns WHERE pattern_key='peak_focus_window'",
          '"Your peak focus window is [time range]. You complete tasks [X]% faster in that slot."'
        ],
        [
          "query_time_on_project",
          '"How much time have I spent on the dashboard project?"\n"Time logged on the API refactor this week"\n"Total hours on project X?"',
          "project_ref",
          "date_range",
          "SUM activity_log WHERE project_id=X AND date BETWEEN range",
          '"You\'ve logged [N] hours on [project] this [period]. Estimated vs actual: [ratio]."'
        ],
        [
          "query_distraction",
          '"What sites distract me most?"\n"How much time am I wasting?"\n"Show me my off-task breakdown"',
          "—",
          "date_range",
          "SELECT browser_sessions WHERE url_category IN ('social','video','news')",
          '"Your top off-task sites this week: [site] ([N] min), [site] ([M] min). Total: [K] minutes."'
        ],
        [
          "what_Zeno_knows",
          '"What do you know about me?"\n"Show me my data"\n"What are you tracking?"',
          "—",
          "data_category",
          "Load all behaviour_patterns; enumerate tracked signals; read privacy summary",
          '"Here\'s what I\'m tracking: [list of signals]. You can ask me to delete any category at any time."'
        ],
        [
          "delete_data",
          '"Delete all my analytics"\n"Wipe my activity history"\n"Clear everything you know about me"',
          "—",
          "data_category\ndate_range",
          "Confirm → DELETE from activity_log, browser_sessions, analytics_* tables",
          '"Confirmed. I\'ve deleted your [category] data. This cannot be undone."'
        ],
      ], iw),
      spacer(2),

      pb(),

      // ─── SECTION 9: BRAIN DUMP & NOTES ──────────────────────
      badgeBlock("CATEGORY 08  |  Brain Dump & Note Capture", BLUE, LIGHT),
      h2("9. Brain Dump & Note Capture"),
      body("Intent group for rapid, frictionless thought capture. These intents execute silently in the background without interrupting the current workflow."),
      spacer(1),
      intentTable([
        [
          "capture_idea",
          '"Idea: use WebSocket instead of polling for live updates"\n"Note: client prefers dark mode by default"\n"Save this: the timeout is probably in the Redis config"',
          "note_text",
          "project_ref\ntags",
          "INSERT notes WHERE note_type='idea'; link to active project",
          '"Idea saved under [project]."'
        ],
        [
          "capture_question",
          '"Question: does the auth token expire on logout or timeout only?"\n"Open question: should we cache at the API or CDN layer?"',
          "question_text",
          "project_ref",
          "INSERT notes WHERE note_type='question'",
          '"Question logged. I\'ll surface this at your next [project] session."'
        ],
        [
          "capture_decision",
          '"Decision: we\'re going with PostgreSQL, not MongoDB"\n"We decided to use REST instead of GraphQL for v1"',
          "decision_text",
          "project_ref\nrationale",
          "INSERT notes WHERE note_type='decision'",
          '"Decision recorded: [short summary]."'
        ],
        [
          "capture_reference",
          '"Reference: MDN docs for the Intersection Observer API"\n"Save the link to the Rust async book"',
          "reference_text_or_url",
          "project_ref\ntags",
          "INSERT notes WHERE note_type='reference'",
          '"Reference saved."'
        ],
        [
          "search_notes",
          '"Find my notes about Redis"\n"Search for anything I saved about the auth flow"\n"What did I decide about the database?"',
          "search_query",
          "project_filter\nnote_type_filter",
          "FTS5 search on notes_fts virtual table",
          '"Found [N] notes matching [query]: [titles]. Want me to read the first one?"'
        ],
        [
          "add_task_from_thought",
          '"Add buy train tickets to my task list for tomorrow"\n"Put code review on my list for this afternoon"\n"Task: ping Jake about the spec, low priority"',
          "task_title\n(due_date implied by\ncurrent brain dump)",
          "due_date\npriority\nproject",
          "INSERT tasks; source='voice'; capture_context=active_app",
          '"Task added: [title] for [date]."'
        ],
      ], iw),
      spacer(2),

      pb(),

      // ─── SECTION 10: CALENDAR ────────────────────────────────
      badgeBlock("CATEGORY 09  |  Calendar & Events", GREEN, GLIGHT),
      h2("10. Calendar & Events"),
      body("Intent group for querying, creating, and modifying calendar events via the local .ics file. Read-write access to ~/Zeno/calendar.ics only."),
      spacer(1),
      intentTable([
        [
          "query_calendar",
          '"What\'s on my calendar today?"\n"Do I have anything on Thursday afternoon?"\n"What meetings do I have this week?"',
          "—",
          "date\ntime_range",
          "Parse calendar.ics; filter by date/time; read events aloud",
          '"Today you have [N] events: [list with times]. Your next is [event] at [time]."'
        ],
        [
          "create_event",
          '"Block 2pm for a team sync"\n"Add a meeting with Jake on Friday at 3pm"\n"Create an event: design review, Tuesday, 10am to 11am"',
          "title\ndate\nstart_time",
          "end_time\nduration\nlocation",
          "VEVENT to calendar.ics; INSERT time_blocks",
          '"Event created: [title] on [date] at [time]."'
        ],
        [
          "find_free_time",
          '"Find me a 2-hour deep work slot this week"\n"When am I free on Wednesday?"\n"Is there a gap between my meetings tomorrow?"',
          "duration",
          "date_range\nblock_type",
          "Scan calendar.ics for gaps; respect working_hours from user_profile",
          '"Your next [duration] gap is [day] from [start] to [end]. Want me to block it?"'
        ],
        [
          "check_conflicts",
          '"Do I have any conflicts today?"\n"Am I double-booked on Thursday?"\n"Check if my 3pm meeting clashes with anything"',
          "—",
          "date",
          "Scan time_blocks + calendar.ics for overlaps",
          '"I found [N] conflicts: [list]. Want me to suggest fixes?"'
        ],
      ], iw),
      spacer(2),

      pb(),

      // ─── SECTION 11: SYSTEM / GENERAL ────────────────────────
      badgeBlock("CATEGORY 10  |  System & General", SLATE, LIGHT2),
      h2("11. System & General"),
      body("Catch-all intent group for meta-commands, conversational interactions, clarifications, and system control."),
      spacer(1),
      intentTable([
        [
          "clarify_intent",
          "(Triggered internally when confidence < 0.75)",
          "—",
          "—",
          "Re-prompt user with candidate intents",
          '"I\'m not sure I caught that — did you mean [option A] or [option B]?"'
        ],
        [
          "cancel_action",
          '"Never mind"\n"Cancel that"\n"Forget it"\n"Stop"',
          "—",
          "—",
          "Abort pending action; do not write to DB",
          '"Cancelled."'
        ],
        [
          "repeat_last",
          '"Say that again"\n"What did you just say?"\n"Can you repeat that?"',
          "—",
          "—",
          "Re-play last TTS response",
          "[Repeats last spoken response]"
        ],
        [
          "help_command",
          '"What can you do?"\n"Help"\n"Show me what commands work"',
          "—",
          "category_filter",
          "Read top-level intent category list; offer to demo",
          '"I can help with tasks, day planning, notes, analytics, workspaces, reminders, and more. What would you like to try?"'
        ],
        [
          "set_preference",
          '"Set my working hours to 8am to 6pm"\n"Change wake word to Atlas"\n"Switch TTS to ElevenLabs"',
          "preference_key\npreference_value",
          "—",
          "UPDATE user_profile; write config.yaml",
          '"[Preference] updated to [value]."'
        ],
        [
          "conversational",
          '"How are you?"\n"Good morning"\n"Thanks"\n"You\'re great"',
          "—",
          "—",
          "Contextual response; no DB write",
          '"[Short warm response]. Ready when you are."'
        ],
      ], iw),
      spacer(2),

      pb(),

      // ─── SECTION 12: SLOT TYPE REFERENCE ────────────────────
      h1("12. Slot Type Reference"),
      body("All 31 slot types used across Zeno intent categories. The NLP parser extracts these from utterances using a combination of rule-based patterns and Claude API inference."),
      spacer(1),
      h2("12.1 Temporal Slots"),
      slotTable([
        ["due_date", "Date", '"tomorrow", "next Friday", "May 5th", "end of week"', "Resolved to ISO 8601 date relative to today"],
        ["due_time", "Time", '"3pm", "after lunch", "morning", "15:30"', "Resolved to HH:MM 24h format"],
        ["date_range", "DateRange", '"this week", "last month", "between Mon and Wed"', "Produces {start, end} tuple"],
        ["duration_minutes", "Integer", '"25 minutes", "2 hours", "half an hour", "an hour and a half"', "Always converted to integer minutes"],
        ["trigger_time", "DateTime", '"in 2 hours", "at 4pm", "tomorrow morning"', "Resolved to ISO 8601 datetime"],
        ["time_preference", "Enum", '"morning", "afternoon", "evening", "after lunch"', "Maps to time range"],
        ["week_start", "Date", '"this week", "last week", "week of April 14"', "Resolved to Monday date"],
      ]),
      spacer(1),
      h2("12.2 Entity Slots"),
      slotTable([
        ["title", "Text", '"fix the login bug", "write unit tests", "call Jake"', "Free text, title-cased on save"],
        ["note_text", "Text", '"use WebSocket instead of polling"', "Free text, stored as-is"],
        ["reminder_text", "Text", '"check the Redis config"', "Free text for notification body"],
        ["task_ref", "TaskRef", '"the login bug task", "task 3", "my report task"', "Resolved to task.id via fuzzy title match"],
        ["project_ref", "ProjectRef", '"the dashboard project", "API refactor"', "Resolved to project.id via fuzzy name match"],
        ["workspace_name_or_slug", "WorkspaceRef", '"dev mode", "writing workspace"', "Resolved to workspaces.slug"],
        ["app_name", "AppName", '"VS Code", "Figma", "Terminal"', "Validated against app_classifications whitelist"],
        ["url_or_label", "URLRef", '"the React docs", "my GitHub"', "Resolved via URL allowlist or workspace URL map"],
        ["reminder_ref", "ReminderRef", '"the 4pm reminder", "the client call reminder"', "Fuzzy match on reminders.message"],
        ["search_query", "Text", '"Redis", "auth flow", "database decision"', "Passed directly to FTS5"],
        ["constraint_text", "Text", '"deadline is end of May"', "Free text for rubber duck session"],
        ["edge_case_text", "Text", '"network drops mid-upload"', "Free text for risk register"],
        ["decision_text", "Text", '"going with PostgreSQL"', "Free text with project link"],
        ["reference_text_or_url", "Text/URL", '"MDN Intersection Observer API"', "Stored as note_type='reference'"],
        ["preference_key", "Enum", '"wake word", "working hours", "TTS engine"', "Maps to user_profile column or config.yaml key"],
        ["preference_value", "Text", '"Atlas", "8am to 6pm", "ElevenLabs"', "Validated against preference_key type"],
      ]),
      spacer(1),
      h2("12.3 Scalar & Enum Slots"),
      slotTable([
        ["priority", "Enum", '"high", "critical", "low", "urgent"', "Maps to: critical|high|medium|low"],
        ["status_filter", "Enum", '"blocked", "pending", "in progress", "completed"', "Maps to tasks.status CHECK values"],
        ["block_type", "Enum", '"deep work", "meeting", "focus", "break", "admin"', "Maps to time_blocks.block_type CHECK values"],
        ["energy_level", "Integer 1-10", '"I\'m exhausted (2)", "feeling great (9)"', "Claude infers numeric from qualitative description"],
        ["focus_quality", "Enum", '"excellent", "good", "scattered", "poor"', "Maps to sessions.focus_quality values"],
        ["mood", "Enum", '"tired", "stressed", "good", "great"', "Maps to sessions.mood CHECK values"],
        ["severity", "Enum", '"critical", "high", "medium", "low"', "For risk register entries"],
        ["delivery_method", "Enum", '"voice", "notification", "both"', "Maps to reminders.delivery_method"],
        ["data_category", "Enum", '"analytics", "browser history", "everything"', "Scopes data deletion command"],
      ]),
      spacer(2),

      pb(),

      // ─── SECTION 13: DIALOGUE STATE MACHINE ─────────────────
      h1("13. Dialogue State Machine — Multi-Turn Conversations"),
      body("Some intents initiate multi-turn conversations. The following table defines the states and transitions for each conversational flow."),
      spacer(1),
      new Table({
        width: { size: 13680, type: WidthType.DXA },
        columnWidths: [2000, 2400, 2800, 3600, 2880],
        rows: [
          headerRow(["Flow", "Entry Intent", "States", "Transitions", "Exit Condition"], [2000, 2400, 2800, 3600, 2880]),
          ...[
            [
              "Day Planning",
              "start_day_planning",
              "LOADING → PRESENTING → BLOCKING → CONFIRMING → DONE",
              "PRESENTING: user assigns each task a duration → BLOCKING\nBLOCKING: conflicts resolved → CONFIRMING\nCONFIRMING: user says 'looks good' → DONE",
              "User confirms schedule or exits with 'cancel'"
            ],
            [
              "Rubber Duck",
              "start_rubber_duck",
              "PROBLEM → CONSTRAINTS → EDGE_CASES → DEPS → CRITERIA → GENERATING",
              "Each state: Zeno asks one question, user answers, next state\nAt any point: 'skip' advances; 'done' jumps to GENERATING",
              "GENERATING state completes and files are written"
            ],
            [
              "Shutdown Ritual",
              "initiate_shutdown",
              "CAPTURING → PROMPTING → SAVING → DONE",
              "CAPTURING: auto-snapshot active window+tabs\nPROMPTING: up to 3 note exchanges → SAVING\nSAVING: writes files → DONE",
              "User says 'done' or 90s timeout elapses"
            ],
            [
              "Re-routing",
              "rebalance_schedule",
              "ANALYSING → PROPOSING → AWAITING → APPLYING",
              "PROPOSING: Zeno reads proposed changes aloud\nAWAITING: user accepts, rejects, or modifies per item\nAPPLYING: writes accepted changes",
              "All items resolved or user says 'apply all'"
            ],
            [
              "Clarification",
              "(auto, confidence < 0.75)",
              "CLARIFYING → RESOLVED / ABANDONED",
              "CLARIFYING: Zeno offers 2 candidate intents\nUser picks one → RESOLVED\nUser says 'never mind' → ABANDONED",
              "Max 2 clarification rounds then abandon"
            ],
          ].map((row, ri) => new TableRow({
            children: row.map((c, ci) => new TableCell({
              borders: brd,
              width: { size: [2000,2400,2800,3600,2880][ci], type: WidthType.DXA },
              shading: { fill: ri%2===0?WHITE:LIGHT2, type: ShadingType.CLEAR },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              verticalAlign: "top",
              children: c.split('\n').map(line =>
                new Paragraph({ spacing: { before: 0, after: 40 },
                  children: [new TextRun({ text: line, font: "Arial", size: 17, color: NAVY })]
                })
              )
            }))
          }))
        ]
      }),
      spacer(2),

      // Final note
      new Paragraph({
        alignment: AlignmentType.CENTER, spacing: { before: 200, after: 0 },
        border: { top: { style: BorderStyle.SINGLE, size: 6, color: BLUE2 } },
        children: [
          new TextRun({ text: "Zeno Voice Command Grammar v1.0  |  52 intents · 31 slot types · 5 conversational flows", font: "Arial", size: 20, bold: true, color: NAVY }),
          new TextRun({ text: "  |  Ready for NLP engineering handoff", font: "Arial", size: 20, italics: true, color: SLATE })
        ]
      })
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('/home/claude/Zeno_VoiceGrammar.docx', buf);
  console.log('Voice grammar doc done');
});
