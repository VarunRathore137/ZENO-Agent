import sqlite3, sys, threading
from zeno.macros.loader import load_workspaces, get_workspace
from zeno.macros.safety import assert_app_allowed, check_app_safety, MacroSafetyError
from zeno.macros.steps import execute_step

# Steps that target an app and need safety + pre-announce
_APP_STEPS = {"open_app", "focus_window"}
# Natural-language pre-announce templates per step type
_STEP_ANNOUNCEMENTS = {
    "open_app":     lambda p: f"Opening {p.get('app_name', 'app')}…",
    "open_url":     lambda p: f"Loading {p.get('url', 'page')} in your browser…",
    "focus_window": lambda p: f"Switching to {p.get('app_name', 'window')}…",
}

class MacroEngine:
    def __init__(self, db_path: str, tts_worker=None, yaml_path: str | None = None) -> None:
        self._db_path = db_path
        self._tts_worker = tts_worker
        self._yaml_path = yaml_path
        self._cancel_event = threading.Event()
        self._active_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_workspace(self, workspace_name: str) -> str:
        """
        Start macro execution in a background thread.
        Returns immediately with a status message.
        """
        try:
            workspace = get_workspace(workspace_name, self._yaml_path, self._tts_worker)
        except KeyError as e:
            return str(e)

        if self._active_thread and self._active_thread.is_alive():
            return "A macro is already running. Say 'stop' to cancel it first."

        self._cancel_event.clear()
        self._active_thread = threading.Thread(
            target=self._run_steps,
            args=(workspace,),
            daemon=True,
            name=f"Macro-{workspace_name}",
        )
        self._active_thread.start()
        return f"Starting workspace '{workspace.name}'."

    def stop_workspace(self) -> str:
        """Cancel the running macro. Flushes pending TTS."""
        if not (self._active_thread and self._active_thread.is_alive()):
            return "No macro is currently running."
        self._cancel_event.set()
        if self._tts_worker:
            self._tts_worker.flush()
        return "Macro cancelled."

    def list_workspaces(self) -> list[str]:
        try:
            return list(load_workspaces(self._yaml_path, self._tts_worker).keys())
        except Exception as e:
            print(f"[MacroEngine] Error listing workspaces: {e}", file=sys.stderr)
            return []

    # ------------------------------------------------------------------
    # Background worker
    # ------------------------------------------------------------------

    def _run_steps(self, workspace) -> None:
        self._log_event("macro_started", f"Starting: {workspace.name}")
        ctx = {"tts_worker": self._tts_worker}

        for i, step in enumerate(workspace.steps):
            if self._cancel_event.is_set():
                self._log_event("macro_cancelled", f"Cancelled at step {i+1}")
                if self._tts_worker:
                    self._tts_worker.enqueue("Workspace setup cancelled.")
                return

            # Three-tier safety for app-targeting steps
            if step.type in _APP_STEPS:
                app_name = step.params.get("app_name", "")
                if app_name:
                    result = check_app_safety(app_name, self._db_path)
                    if result.reason == "denied":
                        msg = f"Step {i+1} blocked: {result.message}"
                        self._log_event("macro_blocked", msg, severity="warning")
                        if self._tts_worker:
                            self._tts_worker.enqueue(result.message)
                        continue  # skip this step, continue macro
                    elif result.reason == "warn_unknown":
                        self._log_event("macro_warn_unknown", result.message, severity="warning")
                        if self._tts_worker:
                            self._tts_worker.enqueue(result.message)
                        # ALLOW — fall through to execution

            # Pre-step TTS announcement for navigating steps
            if step.type in _STEP_ANNOUNCEMENTS and self._tts_worker:
                self._tts_worker.enqueue(_STEP_ANNOUNCEMENTS[step.type](step.params))

            # Execute step
            try:
                execute_step(step.type, step.params, **ctx)
            except Exception as e:
                msg = f"Step {i+1} ({step.type}) error: {e}"
                print(f"[MacroEngine] {msg}", file=sys.stderr)
                self._log_event("macro_error", msg, severity="error")
                # Continue remaining steps — one failure does not abort

        self._log_event("macro_complete", f"Done: {workspace.name}")
        if self._tts_worker:
            self._tts_worker.enqueue(f"Workspace '{workspace.name}' is ready.")

    def _log_event(self, event_type: str, message: str, severity: str = "info") -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT INTO system_events (event_type, severity, component, message) "
                    "VALUES (?, ?, 'macro_engine', ?)",
                    (event_type, severity, message)
                )
        except Exception:
            pass  # logging failures are non-fatal
