"""Real API integration test for HighModelClient — 3 weighted providers from test/.env.
1/2 为 anthropic 类型，3 为 openai 类型；权重 4:4:2。No mocks: real HTTP round-trip."""

from __future__ import annotations

from pathlib import Path

import pytest

from voyo.model import HighModelClient, HighModelConfig, ModelUsage


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


def _configs() -> list[HighModelConfig]:
    configs = []
    for i, mtype in ((1, "anthropic"), (2, "anthropic"), (3, "openai")):
        configs.append(HighModelConfig(
            model_name=_ENV[f"MODEL_NAME{i}"],
            model_type=mtype,
            model_url=_ENV[f"MODEL_BASE_URL{i}"],
            model_token=_ENV[f"MODEL_API_KEY{i}"],
            model_weight=int(_ENV.get(f"MODEL_WEIGHT{i}", "1")),
            max_workers=5,
            rpm=120,
        ))
    return configs


class TestHighModel:
    def test_sync_chat_picks_provider(self):
        client = HighModelClient(_configs())
        usage = ModelUsage()
        resp = client.chat(
            messages=[{"role": "user", "content": "用一句话介绍你自己"}],
            usage=usage, max_tokens=256,
        )
        print(f"\n[high sync] usage={usage}")
        assert isinstance(resp, dict)
        assert usage.output_tokens > 0

    @pytest.mark.asyncio
    async def test_async_chat_picks_provider(self):
        client = HighModelClient(_configs())
        resp = await client.achat(
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=256,
        )
        print(f"\n[high async] resp_type={type(resp).__name__}")
        assert isinstance(resp, dict)

    def test_each_provider_reachable(self):
        """逐个 provider 单独调用，确认 3 个出口都可用。"""
        for cfg in _configs():
            client = HighModelClient([cfg])
            resp = client.chat(
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=64,
            )
            print(f"\n[{cfg['model_type']}:{cfg['model_name']}] ok")
            assert isinstance(resp, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
