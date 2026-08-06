"""基准测试: input_tokens 大小 / 并发量 与响应时延的关系 (qwen3.6-27b @ 192.168.20.114:8080)"""

from __future__ import annotations

import asyncio
import time

from voyo.model.base import ModelUsage
from voyo.model.openai import ModelClient

BASE_URL = "http://192.168.20.114:8080/v1"
API_KEY = "sk-372b5ed8a6614dd5a3b5ec528f882d26"
MODEL = "qwen3.6-27b"
MAX_TOKENS = 64  # 控制生成长度, 聚焦 prefill 耗时

# 实测中文约 1 字 ≈ 0.54 token
CHAR_PER_TOKEN = 1.85
SEGMENT = "人工智能正在深刻改变软件工程的开发方式,大模型可以完成代码生成、审查与重构等任务。"


def make_prompt(target_tokens: int) -> str:
    target_chars = int(target_tokens * CHAR_PER_TOKEN)
    text = (SEGMENT * (target_chars // len(SEGMENT) + 1))[:target_chars]
    return f"请用一句话总结以下内容:\n{text}"


def bench_input_sizes(client: ModelClient, sizes: list[int]) -> None:
    print("\n=== input_tokens vs 时延 (串行) ===")
    print(f"{'目标input':>10} {'实际input':>10} {'output':>8} {'总耗时s':>9} {'prefill tok/s':>14}")
    for size in sizes:
        usage = ModelUsage()
        t0 = time.time()
        client.chat(
            model=MODEL,
            messages=[{"role": "user", "content": make_prompt(size)}],
            max_tokens=MAX_TOKENS,
            timeout=600.0,
            usage=usage,
        )
        elapsed = time.time() - t0
        print(f"{size:>10} {usage.input_tokens:>10} {usage.output_tokens:>8} {elapsed:>9.2f} {usage.input_tokens / elapsed:>14.0f}")


async def _one(client: ModelClient, prompt: str) -> tuple[float, ModelUsage]:
    usage = ModelUsage()
    t0 = time.time()
    await client.achat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=MAX_TOKENS,
        timeout=600.0,
        usage=usage,
    )
    return time.time() - t0, usage


async def bench_concurrency(client: ModelClient, input_size: int, levels: list[int]) -> None:
    print(f"\n=== 并发量 vs 时延 (input≈{input_size} tokens) ===")
    print(f"{'并发':>6} {'总耗时s':>9} {'单请求均值s':>12} {'单请求最大s':>12} {'吞吐 req/s':>11}")
    prompt = make_prompt(input_size)
    for n in levels:
        t0 = time.time()
        results = await asyncio.gather(*(_one(client, prompt) for _ in range(n)))
        total = time.time() - t0
        latencies = [r[0] for r in results]
        print(f"{n:>6} {total:>9.2f} {sum(latencies) / n:>12.2f} {max(latencies):>12.2f} {n / total:>11.2f}")


def main() -> None:
    client = ModelClient(base_url=BASE_URL, api_key=API_KEY)
    # 预热
    client.chat(model=MODEL, messages=[{"role": "user", "content": "hi"}], max_tokens=8, timeout=600.0)
    bench_input_sizes(client, [2048, 4096, 8192, 16384, 32768])
    asyncio.run(bench_concurrency(client, 8192, [1, 2, 4, 8]))


if __name__ == "__main__":
    main()
