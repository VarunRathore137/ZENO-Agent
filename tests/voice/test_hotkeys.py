import pytest
import threading
from zeno.voice.hotkeys import HotkeyListener, HotkeyState

def test_hotkey_state_init():
    state = HotkeyState()
    assert isinstance(state.brain_dump_triggered, threading.Event)
    assert isinstance(state.push_to_talk_active, threading.Event)
    assert not state.brain_dump_triggered.is_set()
    assert not state.push_to_talk_active.is_set()

def test_listener_init_with_state():
    state = HotkeyState()
    listener = HotkeyListener(state)
    assert listener.state is state

def test_listener_init_creates_state_if_none():
    listener = HotkeyListener()
    assert listener.state is not None
    assert isinstance(listener.state, HotkeyState)

def test_ptt_events():
    """PTT callbacks set/clear the event correctly."""
    state = HotkeyState()
    listener = HotkeyListener(state)
    listener._on_ptt_press()
    assert state.push_to_talk_active.is_set()
    listener._on_ptt_release()
    assert not state.push_to_talk_active.is_set()
