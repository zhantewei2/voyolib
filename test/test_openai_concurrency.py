"""Integration tests for voyo.model.openai.OpenAiClient 并发与 RPM 控制 — no mocks。"""

from __future__ import annotations

import asyncio
import concurrent.futures
import time

import pytest

from voyo.model.openai import OpenAiClient

BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
API_KEY = "sk-372b5ed8a6614dd5a3b5ec528f882d26"
MODEL = "qwen-plus"
_PROMPT = [{"role": "user", "content": "hi"}]
_MAX_TOKENS = 8


def _chat(client: OpenAiClient) -> dict:
    return client.chat(model=MODEL, messages=_PROMPT, max_tokens=_MAX_TOKENS)


async def _achat(client: OpenAiClient) -> dict:
    return await client.achat(model=MODEL, messages=_PROMPT, max_tokens=_MAX_TOKENS)


class TestNoControl:
    def test_default_init_no_semaphore_no_pacing(self):
        client = OpenAiClient(base_url=BASE_URL, api_key=API_KEY)
        assert client._limiter._sem is None
        assert client._limiter._asem is None
        assert client._limiter._min_interval == 0.0

    def test_zero_args_no_semaphore_no_pacing(self):
        client = OpenAiClient(base_url=BASE_URL, api_key=API_KEY, max_workers=0, rpm=0)
        assert client._limiter._sem is None
        assert client._limiter._asem is None
        assert client._limiter._min_interval == 0.0


class TestSemaphore:
    def test_sync_max_workers_creates_threading_semaphore(self):
        client = OpenAiClient(base_url=BASE_URL, api_key=API_KEY, max_workers=3)
        sem = client._limiter._sem
        asem = client._limiter._asem
        assert sem is not None
        assert asem is not None  # 同步/异步信号量都构建
        # 同步信号量初始应允许 3 个
        assert sem.acquire(blocking=False) is True
        assert sem.acquire(blocking=False) is True
        assert sem.acquire(blocking=False) is True
        assert sem.acquire(blocking=False) is False  # 第 4 个被拒
        sem.release()
        sem.release()
        sem.release()

    def test_sync_baseline_concurrent_no_limit(self):
        """无并发控制时，3 个并发应几乎同时执行（基准耗时）。"""
        client = OpenAiClient(base_url=BASE_URL, api_key=API_KEY)
        t0 = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            list(ex.map(lambda _: _chat(client), range(3)))
        elapsed = time.monotonic() - t0
        print(f"\n[baseline sync] elapsed={elapsed:.2f}s")
        # 留出充足网络余量：3 个并发完成应 < 6s（远低于串行 3 次）
        assert elapsed < 6.0

    def test_sync_max_workers_1_serializes(self):
        client = OpenAiClient(base_url=BASE_URL, api_key=API_KEY, max_workers=1)
        t0 = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            list(ex.map(lambda _: _chat(client), range(3)))
        elapsed = time.monotonic() - t0
        print(f"\n[max_workers=1 sync] elapsed={elapsed:.2f}s")
        # 串行 3 次：单次 ~0.7s × 3 ≈ 2.1s，留 1.5s 下限
        assert elapsed >= 1.5

    def test_sync_max_workers_2_faster_than_1(self):
        """max_workers=2 应比 max_workers=1 更快完成同样 4 个请求。"""
        c1 = OpenAiClient(base_url=BASE_URL, api_key=API_KEY, max_workers=1)
        c2 = OpenAiClient(base_url=BASE_URL, api_key=API_KEY, max_workers=2)

        t0 = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(lambda _: _chat(c1), range(4)))
        t1 = time.monotonic() - t0

        t0 = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(lambda _: _chat(c2), range(4)))
        t2 = time.monotonic() - t0

        print(f"\n[max_workers 1 vs 2 sync] t1={t1:.2f}s t2={t2:.2f}s")
        assert t2 < t1

    @pytest.mark.asyncio
    async def test_async_max_workers_1_serializes(self):
        client = OpenAiClient(base_url=BASE_URL, api_key=API_KEY, max_workers=1)
        t0 = time.monotonic()
        await asyncio.gather(*[_achat(client) for _ in range(3)])
        elapsed = time.monotonic() - t0
        print(f"\n[max_workers=1 async] elapsed={elapsed:.2f}s")
        # 串行 3 次：单次 ~0.7s × 3 ≈ 2.1s，留 1.5s 下限
        assert elapsed >= 1.5

    @pytest.mark.asyncio
    async def test_async_max_workers_2_faster_than_1(self):
        c1 = OpenAiClient(base_url=BASE_URL, api_key=API_KEY, max_workers=1)
        c2 = OpenAiClient(base_url=BASE_URL, api_key=API_KEY, max_workers=2)

        t0 = time.monotonic()
        await asyncio.gather(*[_achat(c1) for _ in range(4)])
        t1 = time.monotonic() - t0

        t0 = time.monotonic()
        await asyncio.gather(*[_achat(c2) for _ in range(4)])
        t2 = time.monotonic() - t0

        print(f"\n[max_workers 1 vs 2 async] t1={t1:.2f}s t2={t2:.2f}s")
        assert t2 < t1


class TestRpm:
    def test_min_interval_calculation(self):
        # rpm=60 → 1s 间隔；rpm=30 → 2s；rpm=0 → 0
        assert OpenAiClient(BASE_URL, API_KEY, rpm=60)._limiter._min_interval == pytest.approx(1.0)
        assert OpenAiClient(BASE_URL, API_KEY, rpm=30)._limiter._min_interval == pytest.approx(2.0)
        assert OpenAiClient(BASE_URL, API_KEY)._limiter._min_interval == 0.0

    def test_sync_rpm_paces_sequential(self):
        # rpm=30 → 2s 间隔；3 个顺序请求至少 4s
        client = OpenAiClient(base_url=BASE_URL, api_key=API_KEY, rpm=30)
        t0 = time.monotonic()
        for _ in range(3):
            _chat(client)
        elapsed = time.monotonic() - t0
        print(f"\n[rpm=30 sync seq] elapsed={elapsed:.2f}s")
        assert elapsed >= 4.0

    @pytest.mark.asyncio
    async def test_async_rpm_paces_sequential(self):
        client = OpenAiClient(base_url=BASE_URL, api_key=API_KEY, rpm=30)
        t0 = time.monotonic()
        for _ in range(3):
            await _achat(client)
        elapsed = time.monotonic() - t0
        print(f"\n[rpm=30 async seq] elapsed={elapsed:.2f}s")
        assert elapsed >= 4.0

    @pytest.mark.asyncio
    async def test_async_rpm_paces_concurrent(self):
        """3 个并发 + rpm=30：预约槽位下应被均匀排成 2 个间隔共 4s+。"""
        client = OpenAiClient(base_url=BASE_URL, api_key=API_KEY, rpm=30)
        t0 = time.monotonic()
        await asyncio.gather(*[_achat(client) for _ in range(3)])
        elapsed = time.monotonic() - t0
        print(f"\n[rpm=30 async gather] elapsed={elapsed:.2f}s")
        # 2 个 2s 间隔 + 一次调用 ≈ 4.7s，下限 4.0s
        assert elapsed >= 4.0


class TestCombined:
    @pytest.mark.asyncio
    async def test_max_workers_and_rpm_compose(self):
        # max_workers=2 + rpm=60 (1s 间隔) + 4 个并发
        # 期望：2 并发为一批，批间间隔 ~1s，2 批共耗时 >= 2s + 调用时间
        client = OpenAiClient(base_url=BASE_URL, api_key=API_KEY, max_workers=2, rpm=60)
        t0 = time.monotonic()
        await asyncio.gather(*[_achat(client) for _ in range(4)])
        elapsed = time.monotonic() - t0
        print(f"\n[max_workers=2 rpm=60 async] elapsed={elapsed:.2f}s")
        # 至少 1 个间隔（1s）+ 2 批网络时间，远高于纯并发
        assert elapsed >= 2.0


class TestStreamUnderControl:
    """流式返回走的是生成器，信号量只在线程/协程内保护请求的提交部分。"""

    def test_sync_stream_with_max_workers_works(self):
        client = OpenAiClient(base_url=BASE_URL, api_key=API_KEY, max_workers=1)
        lines = list(client.chat(model=MODEL, messages=_PROMPT, max_tokens=_MAX_TOKENS, stream=True))
        data = [l for l in lines if l.startswith("data:") and "[DONE]" not in l]
        print(f"\n[stream max_workers=1 sync] data_lines={len(data)}")
        assert data

    @pytest.mark.asyncio
    async def test_async_stream_with_max_workers_works(self):
        client = OpenAiClient(base_url=BASE_URL, api_key=API_KEY, max_workers=1)
        lines = [
            line
            async for line in await client.achat(
                model=MODEL, messages=_PROMPT, max_tokens=_MAX_TOKENS, stream=True
            )
        ]
        data = [l for l in lines if l.startswith("data:") and "[DONE]" not in l]
        print(f"\n[stream max_workers=1 async] data_lines={len(data)}")
        assert data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
