"""Real API integration test for OpenAiClient — hits the endpoint in test/.env.
Skips when test/.env is absent. No mocks: real HTTP round-trip."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from voyo.model.openai import OpenAiClient


def _load_env() -> dict[str, str]:
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        return {}
    env = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


_ENV = _load_env()
pytestmark = pytest.mark.skipif(not _ENV, reason="test/.env not found")

_NAME = _ENV.get("MODEL_NAME3", "")
_BASE = _ENV.get("MODEL_BASE_URL3", "")
_KEY = _ENV.get("MODEL_API_KEY3", "")


def _client() -> OpenAiClient:
    return OpenAiClient(base_url=_BASE, api_key=_KEY, rpm=60, max_workers=5)


class TestRealChat:
    def test_sync_hello(self):
        resp = _client().chat(
            model=_NAME, messages=[{"role": "user", "content": "hello"}],
        )
        content = resp["choices"][0]["message"]["content"]
        print(f"\n[real sync] {content!r}")
        assert isinstance(content, str) and content.strip()

    @pytest.mark.asyncio
    async def test_async_hello(self):
        resp = await _client().achat(
            model=_NAME, messages=[{"role": "user", "content": "hello"}],
        )
        content = resp["choices"][0]["message"]["content"]
        print(f"\n[real async] {content!r}")
        assert isinstance(content, str) and content.strip()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
