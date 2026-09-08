"""Unit tests for voyo.model.rate_limit.RateLimiter — no network, no mocks."""

from __future__ import annotations

import asyncio
import concurrent.futures
import time

import pytest

from voyo.model.rate_limit import RateLimiter


class TestInit:
    def test_default_no_pacing(self):
        rl = RateLimiter()
        assert rl._min_interval == 0.0

    def test_rpm_60_is_1s_interval(self):
        assert RateLimiter(rpm=60)._min_interval == pytest.approx(1.0)

    def test_rpm_30_is_2s_interval(self):
        assert RateLimiter(rpm=30)._min_interval == pytest.approx(2.0)

    def test_rpm_120_is_half_second(self):
        assert RateLimiter(rpm=120)._min_interval == pytest.approx(0.5)


class TestAcquireSync:
    def test_no_rpm_returns_immediately(self):
        rl = RateLimiter()
        t0 = time.monotonic()
        with rl.acquire_sync():
            pass
        assert time.monotonic() - t0 < 0.1

    def test_first_call_no_wait(self):
        # _last_req_at=0，时间戳远大于 0，首次不需等
        rl = RateLimiter(rpm=30)
        t0 = time.monotonic()
        with rl.acquire_sync():
            pass
        assert time.monotonic() - t0 < 0.1

    def test_sequential_paces_2s(self):
        rl = RateLimiter(rpm=30)
        with rl.acquire_sync():
            pass  # 首次立即
        t0 = time.monotonic()
        with rl.acquire_sync():
            pass  # 第二次应等 ~2s
        elapsed = time.monotonic() - t0
        print(f"\n[acquire_sync seq] elapsed={elapsed:.2f}s")
        assert elapsed >= 1.8

    def test_concurrent_threads_pace_correctly(self):
        # 3 个并发线程 + rpm=30：先占 1 个槽，3 个并发应排成 2 个 2s 间隔共 ~4s
        rl = RateLimiter(rpm=30)
        with rl.acquire_sync():
            pass  # 先占一格
        t0 = time.monotonic()
        def _go():
            with rl.acquire_sync():
                pass
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            list(ex.map(lambda _: _go(), range(3)))
        elapsed = time.monotonic() - t0
        print(f"\n[acquire_sync gather] elapsed={elapsed:.2f}s")
        assert elapsed >= 3.5


class TestAcquireAsync:
    @pytest.mark.asyncio
    async def test_no_rpm_returns_immediately(self):
        rl = RateLimiter()
        t0 = time.monotonic()
        async with rl.acquire():
            pass
        assert time.monotonic() - t0 < 0.1

    @pytest.mark.asyncio
    async def test_first_call_no_wait(self):
        rl = RateLimiter(rpm=30)
        t0 = time.monotonic()
        async with rl.acquire():
            pass
        assert time.monotonic() - t0 < 0.1

    @pytest.mark.asyncio
    async def test_sequential_paces_2s(self):
        rl = RateLimiter(rpm=30)
        async with rl.acquire():
            pass
        t0 = time.monotonic()
        async with rl.acquire():
            pass
        elapsed = time.monotonic() - t0
        print(f"\n[acquire async seq] elapsed={elapsed:.2f}s")
        assert elapsed >= 1.8

    @pytest.mark.asyncio
    async def test_concurrent_coroutines_pace_correctly(self):
        # 4 个并发协程：预约槽位下应排成 3 个 2s 间隔共 ~6s
        rl = RateLimiter(rpm=30)
        t0 = time.monotonic()
        async def _go():
            async with rl.acquire():
                pass
        await asyncio.gather(*[_go() for _ in range(4)])
        elapsed = time.monotonic() - t0
        print(f"\n[acquire async gather 4] elapsed={elapsed:.2f}s")
        # 3 个 2s 间隔 = 6s，下限 5.5s
        assert elapsed >= 5.5


class TestMixedSyncAsync:
    """同一实例上 sync 和 async 共享 last_req_at（按用户约定：项目只走一种）。"""

    @pytest.mark.asyncio
    async def test_sync_then_async_sees_advanced_last_req(self):
        rl = RateLimiter(rpm=30)
        with rl.acquire_sync():
            pass  # 同步占一格
        t0 = time.monotonic()
        async with rl.acquire():
            pass  # async 视角：上次请求刚发生过 ~0s 前，应等 ~2s
        elapsed = time.monotonic() - t0
        print(f"\n[sync→async] elapsed={elapsed:.2f}s")
        assert elapsed >= 1.8


class TestDegradation:
    def test_default_degrade_sleep_10s(self):
        assert RateLimiter()._degrade_sleep == 10.0

    def test_429_drops_rpm_by_step(self):
        rl = RateLimiter(rpm=30, recover_wait=999.0)
        rl.is_rate_limited_text(429, "")
        assert rl._current_rpm == 25
        assert rl._min_interval == pytest.approx(60.0 / 25)

    def test_429_sets_no_global_block(self):
        # 429 后其他请求不应被阻塞，只受 rpm 节奏影响；rpm=0 时完全无等待
        rl = RateLimiter(rpm=0)
        rl.is_rate_limited_text(429, "")
        t0 = time.monotonic()
        with rl.acquire_sync():
            pass
        assert time.monotonic() - t0 < 0.1

    def test_penalty_sleep_sync(self):
        rl = RateLimiter(degrade_sleep=0.2)
        t0 = time.monotonic()
        rl.penalty_sleep_sync()
        assert time.monotonic() - t0 >= 0.18

    @pytest.mark.asyncio
    async def test_penalty_sleep_only_blocks_current_coroutine(self):
        # 协程 A 睡 penalty 期间，协程 B 的 acquire 应照常完成
        rl = RateLimiter(degrade_sleep=0.5)
        done = []

        async def _a():
            await rl.penalty_sleep()
            done.append("a")

        async def _b():
            async with rl.acquire():
                done.append("b")

        await asyncio.gather(_a(), _b())
        assert done[0] == "b"  # b 先完成，未被 a 的 penalty 拖住


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
