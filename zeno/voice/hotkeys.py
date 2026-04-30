import threading
import time
import sys
from dataclasses import dataclass, field
import pynput

@dataclass
class HotkeyState:
    brain_dump_triggered: threading.Event = field(default_factory=threading.Event)
    push_to_talk_active: threading.Event = field(default_factory=threading.Event)

class HotkeyListener:
    def __init__(self, state: HotkeyState | None = None):
        self.state = state if state is not None else HotkeyState()
        self._listener: pynput.keyboard.GlobalHotKeys | None = None
        self._stop_event = threading.Event()

    def _on_brain_dump(self) -> None:
        try:
            self.state.brain_dump_triggered.set()
            
            def clear_flag():
                time.sleep(0.1)
                self.state.brain_dump_triggered.clear()
                
            threading.Thread(target=clear_flag, daemon=True).start()
        except Exception as e:
            print(f"Error in brain dump hotkey: {e}", file=sys.stderr)

    def _on_ptt_press(self) -> None:
        try:
            self.state.push_to_talk_active.set()
        except Exception as e:
            print(f"Error in PTT press hotkey: {e}", file=sys.stderr)

    def _on_ptt_release(self) -> None:
        try:
            self.state.push_to_talk_active.clear()
        except Exception as e:
            print(f"Error in PTT release hotkey: {e}", file=sys.stderr)

    def start(self) -> None:
        try:
            self._listener = pynput.keyboard.GlobalHotKeys({
                '<ctrl>+<shift>+<space>': self._on_brain_dump,
                '<ctrl>+<shift>+j': self._on_ptt_press
            })
            self._listener.start()
        except Exception as e:
            print(f"Failed to start hotkey listener: {e}", file=sys.stderr)

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
        self._stop_event.set()

def create_listener(state: HotkeyState | None = None) -> HotkeyListener:
    return HotkeyListener(state)
