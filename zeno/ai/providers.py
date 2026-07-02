"""
zeno/ai/providers.py — Abstract LLM Provider interface with concrete implementations.

Provides:
  - LLMProvider Protocol (the contract)
  - ClaudeProvider (high-reasoning tasks: briefings, PRDs, rubber duck)
  - GeminiProvider (low-latency tasks: intent slot fill, quick disambiguation)
  - ProviderRouter (routes feature keys to provider instances via config)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

import yaml


# ---------------------------------------------------------------------------
# Protocol — the contract every provider must fulfil
# ---------------------------------------------------------------------------

@runtime_checkable
class LLMProvider(Protocol):
    """Defines the minimal async interface all LLM providers must implement."""

    async def complete(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        """Single-turn completion. Returns the full response text."""
        ...

    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Completion that returns a parsed JSON dict."""
        ...

    async def stream(
        self,
        messages: list[dict[str, str]],
        system: str = "",
    ) -> AsyncIterator[str]:
        """Streaming completion — yields text chunks as they arrive."""
        ...


# ---------------------------------------------------------------------------
# ClaudeProvider
# ---------------------------------------------------------------------------

class ClaudeProvider:
    """
    LLMProvider backed by Anthropic Claude.
    Best for: morning briefings, rubber duck sessions, PRD generation,
              weekly insight narratives, clarification disambiguation.
    """

    DEFAULT_MODEL = "claude-sonnet-4-5"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model or self.DEFAULT_MODEL
        self._client: Any = None  # lazy-init

    def _get_client(self) -> Any:
        if self._client is None:
            if not self._api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY environment variable is not set. "
                    "Claude provider cannot initialise."
                )
            try:
                import anthropic  # type: ignore[import]
                self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
            except ImportError:
                print(
                    "Error: 'anthropic' package not installed. Run: pip install anthropic",
                    file=sys.stderr,
                )
                raise
        return self._client

    async def complete(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        client = self._get_client()
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        response = await client.messages.create(**kwargs)
        return response.content[0].text

    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # Append instruction to respond with JSON
        structured_system = (system + "\n\nRespond ONLY with valid JSON.").strip()
        text = await self.complete(messages, system=structured_system, max_tokens=4096)
        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()
        return json.loads(text)

    async def stream(
        self,
        messages: list[dict[str, str]],
        system: str = "",
    ) -> AsyncIterator[str]:
        client = self._get_client()
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        async with client.messages.stream(**kwargs) as s:
            async for chunk in s.text_stream:
                yield chunk


# ---------------------------------------------------------------------------
# GeminiProvider
# ---------------------------------------------------------------------------

class GeminiProvider:
    """
    LLMProvider backed by Google Gemini.
    Best for: intent slot filling, quick disambiguation, low-latency tasks.
    """

    DEFAULT_MODEL = "gemini-1.5-flash"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        self.model = model or self.DEFAULT_MODEL
        self._client: Any = None  # lazy-init

    def _get_client(self) -> Any:
        if self._client is None:
            if not self._api_key:
                raise ValueError(
                    "GOOGLE_API_KEY environment variable is not set. "
                    "Gemini provider cannot initialise."
                )
            try:
                from google import genai  # type: ignore[import]
                self._client = genai.Client(api_key=self._api_key)
            except ImportError:
                print(
                    "Error: 'google-genai' package not installed. Run: pip install google-genai",
                    file=sys.stderr,
                )
                raise
        return self._client

    async def complete(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        client = self._get_client()
        # Flatten messages into a single prompt for Gemini
        parts: list[str] = []
        if system:
            parts.append(f"System: {system}\n")
        for msg in messages:
            role = msg.get("role", "user").capitalize()
            parts.append(f"{role}: {msg.get('content', '')}")
        prompt = "\n".join(parts)
        # Run synchronous Gemini call in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=self.model,
                contents=prompt,
            ),
        )
        return response.text

    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        structured_system = (system + "\n\nRespond ONLY with valid JSON.").strip()
        text = await self.complete(messages, system=structured_system, max_tokens=4096)
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()
        return json.loads(text)

    async def stream(
        self,
        messages: list[dict[str, str]],
        system: str = "",
    ) -> AsyncIterator[str]:
        # Gemini streaming — yield as a single chunk for now (SDK parity)
        text = await self.complete(messages, system=system)
        yield text


# ---------------------------------------------------------------------------
# ProviderRouter
# ---------------------------------------------------------------------------

# Default feature → provider mapping. Can be overridden by config.yaml.
_DEFAULT_ROUTING: dict[str, str] = {
    "rubber_duck": "claude",
    "morning_briefing": "claude",
    "prd_generation": "claude",
    "weekly_insights": "claude",
    "clarification": "claude",
    "intent_slot_fill": "gemini",
    "fallback": "gemini",
}


class ProviderRouter:
    """
    Routes feature keys to the appropriate LLM provider instance.

    Routing priority:
      1. config.yaml `llm_routing` section (if present)
      2. Hard-coded defaults in _DEFAULT_ROUTING
    """

    def __init__(
        self,
        config_path: str | None = None,
        claude_provider: LLMProvider | None = None,
        gemini_provider: LLMProvider | None = None,
    ) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._routing: dict[str, str] = dict(_DEFAULT_ROUTING)

        # Load config overrides if provided
        if config_path:
            self._load_config(config_path)

        # Register concrete providers (lazy: only initialised if actually used)
        self._providers["claude"] = claude_provider or ClaudeProvider()
        self._providers["gemini"] = gemini_provider or GeminiProvider()

    def _load_config(self, config_path: str) -> None:
        """Merge llm_routing from a config.yaml file into the routing table."""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            routing_overrides: dict[str, str] = config.get("llm_routing", {})
            self._routing.update(routing_overrides)
        except FileNotFoundError:
            pass  # Config file optional; use defaults
        except yaml.YAMLError as e:
            print(f"Warning: Could not parse config.yaml llm_routing: {e}", file=sys.stderr)

    def get_provider(self, feature: str) -> LLMProvider:
        """
        Return the appropriate provider for a given feature key.

        Args:
            feature: A string key such as 'rubber_duck', 'intent_slot_fill', etc.

        Returns:
            An LLMProvider instance.
        """
        provider_name = self._routing.get(feature) or self._routing.get("fallback", "gemini")
        provider = self._providers.get(provider_name)
        if provider is None:
            # Fallback to Gemini if named provider is somehow missing
            provider = self._providers.get("gemini") or GeminiProvider()
        return provider

    # Convenience pass-throughs for the most common operation
    async def complete(
        self,
        feature: str,
        messages: list[dict[str, str]],
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        return await self.get_provider(feature).complete(messages, system=system, max_tokens=max_tokens)

    async def complete_structured(
        self,
        feature: str,
        messages: list[dict[str, str]],
        system: str = "",
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.get_provider(feature).complete_structured(messages, system=system, schema=schema)

    async def stream(
        self,
        feature: str,
        messages: list[dict[str, str]],
        system: str = "",
    ) -> AsyncIterator[str]:
        async for chunk in self.get_provider(feature).stream(messages, system=system):
            yield chunk


# ---------------------------------------------------------------------------
# Module-level singleton factory
# ---------------------------------------------------------------------------

_router: ProviderRouter | None = None


def get_router(config_path: str | None = None) -> ProviderRouter:
    """Return the module-level singleton ProviderRouter, creating it if needed."""
    global _router
    if _router is None:
        zeno_dir = os.path.join(os.path.expanduser("~"), "Zeno")
        default_config = os.path.join(zeno_dir, "config.yaml")
        _router = ProviderRouter(config_path=config_path or default_config)
    return _router
