"""Unit tests for voyo.model.rate_limit.RateLimiter.is_rate_limited — no network, no mocks."""

from __future__ import annotations

import httpx

from voyo.model.rate_limit import RateLimiter


def _rl() -> RateLimiter:
    """Fresh instance per call so degradation side effects don't leak across tests."""
    return RateLimiter(rpm=30, recover_wait=999.0)  # recover_wait 拉大避免 timer 误触发


class TestStatusCodeOnly:
    def test_429_is_rate_limited(self):
        rl = _rl()
        assert rl.is_rate_limited(httpx.Response(429)) is True

    def test_429_with_any_body(self):
        # 429 不看 body，只要状态码就判
        rl = _rl()
        assert rl.is_rate_limited(httpx.Response(429, text="some unrelated text")) is True

    def test_200_is_not_rate_limited(self):
        rl = _rl()
        assert rl.is_rate_limited(httpx.Response(200, json={"ok": True})) is False

    def test_201_is_not_rate_limited(self):
        rl = _rl()
        assert rl.is_rate_limited(httpx.Response(201)) is False

    def test_400_is_not_rate_limited(self):
        rl = _rl()
        assert rl.is_rate_limited(httpx.Response(400, text="Bad request")) is False

    def test_401_is_not_rate_limited(self):
        rl = _rl()
        assert rl.is_rate_limited(httpx.Response(401, text="Unauthorized")) is False

    def test_403_is_not_rate_limited(self):
        rl = _rl()
        assert rl.is_rate_limited(httpx.Response(403, text="Forbidden")) is False

    def test_404_is_not_rate_limited(self):
        rl = _rl()
        assert rl.is_rate_limited(httpx.Response(404, text="Not found")) is False

    def test_504_is_not_rate_limited(self):
        # 用户没有把 504 算进 rate-limit（虽然也是网关错）
        rl = _rl()
        assert rl.is_rate_limited(httpx.Response(504, text="Gateway timeout")) is False

    def test_502_is_not_rate_limited(self):
        # 同上 502 也不算
        rl = _rl()
        assert rl.is_rate_limited(httpx.Response(502, text="Bad gateway")) is False


class Test500Or503BodyMatch:
    def test_503_with_too_many_requests_matched(self):
        rl = _rl()
        resp = httpx.Response(503, text="Too many requests, please slow down")
        assert rl.is_rate_limited(resp) is True

    def test_500_with_too_many_requests_matched(self):
        rl = _rl()
        resp = httpx.Response(500, text="Error: too many requests concurrent")
        assert rl.is_rate_limited(resp) is True

    def test_503_match_is_case_insensitive(self):
        rl = _rl()
        resp = httpx.Response(503, text="TOO MANY REQUESTS, BACKOFF REQUIRED")
        assert rl.is_rate_limited(resp) is True

    def test_503_with_mixed_case(self):
        rl = _rl()
        resp = httpx.Response(503, text="Throttled: Too Many Requests in the last minute")
        assert rl.is_rate_limited(resp) is True

    def test_500_without_matching_phrase(self):
        rl = _rl()
        resp = httpx.Response(500, text="Internal server error: database connection failed")
        assert rl.is_rate_limited(resp) is False

    def test_503_with_unrelated_error(self):
        rl = _rl()
        resp = httpx.Response(503, text="Service temporarily unavailable for maintenance")
        assert rl.is_rate_limited(resp) is False

    def test_500_with_partial_match_is_false(self):
        # 单独出现 "many" 或 "request" 但没有 "too many requests" 短语不算
        rl = _rl()
        resp = httpx.Response(500, text="Bad request: too few items")
        assert rl.is_rate_limited(resp) is False


class TestReadIdempotent:
    """验证 resp.read() 不会破坏后续对 resp.text 的访问。"""

    def test_text_still_readable_after_check(self):
        rl = _rl()
        resp = httpx.Response(503, text="Too many requests, slow down")
        assert rl.is_rate_limited(resp) is True
        # read() 已被内部调用，但 resp.text 应仍可访问
        assert "too many requests" in resp.text.lower()

    def test_body_not_consumed_for_non_matching_codes(self):
        rl = _rl()
        resp = httpx.Response(200, json={"ok": True})
        assert rl.is_rate_limited(resp) is False
        # 200 不应触发 read，text 仍可访问
        assert resp.text == '{"ok":true}' or resp.json() == {"ok": True}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # noqa: F821  (pytest 是测试运行入口)
