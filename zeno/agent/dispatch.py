"""
zeno/agent/dispatch.py
──────────────────────
HTTP bridge: calls the ZENO OS Agent (port 8765) for tool execution.
Used by both the NLP dispatcher (router.py) and Gemini Live function calls.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

log = logging.getLogger("zeno.agent.dispatch")

AGENT_HOST = os.environ.get("ZENO_AGENT_HOST", "127.0.0.1")
AGENT_PORT = int(os.environ.get("ZENO_AGENT_PORT", "8765"))
AGENT_BASE_URL = f"http://{AGENT_HOST}:{AGENT_PORT}"


def dispatch_to_agent(tool_name: str, args: Dict[str, Any] = {}) -> Dict[str, Any]:
    """
    Send a synchronous POST /execute request to the ZENO OS Agent.

    Returns the parsed JSON response dict.
    Raises RuntimeError if the agent is unreachable or returns an error.
    """
    import urllib.request
    import urllib.error
    import json

    payload = json.dumps({"tool": tool_name, "args": args}).encode("utf-8")
    url = f"{AGENT_BASE_URL}/execute"

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            result = json.loads(body)
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"ZENO OS Agent unreachable at {url}. "
            f"Make sure the agent is running on port {AGENT_PORT}. Error: {e}"
        )
    except Exception as e:
        raise RuntimeError(f"Agent call failed for tool '{tool_name}': {e}")

    if not result.get("ok"):
        error_msg = result.get("error", "Unknown agent error")
        log.warning("Agent tool '%s' returned error: %s", tool_name, error_msg)
        raise RuntimeError(error_msg)

    return result.get("result") or {}


def is_agent_available() -> bool:
    """Quick health check — returns True if agent is up."""
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen(f"{AGENT_BASE_URL}/health", timeout=2):
            return True
    except Exception:
        return False
