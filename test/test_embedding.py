"""Integration tests for voyo.model.embedding.EmbeddingClient — no mocks."""

from __future__ import annotations

import pytest

from voyo.model.embedding import EmbeddingClient

BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
API_KEY = "sk-372b5ed8a6614dd5a3b5ec528f882d26"
MODEL = "text-embedding-v4"

@pytest.fixture
def client():
    return EmbeddingClient(base_url=BASE_URL, api_key=API_KEY)


class TestEmbed:
    def test_single_text_returns_float_vector(self, client):
        result = client.embed(model=MODEL, input="Hello world")
        print(f"\n[embed] dim={len(result)}, first_5={result[:5]}")
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(x, float) for x in result)

    def test_different_texts_different_vectors(self, client):
        a = client.embed(model=MODEL, input="cat")
        b = client.embed(model=MODEL, input="stock market")
        print(f"\n[embed_diff] cat[:3]={a[:3]} | finance[:3]={b[:3]}")
        assert a != b


class TestAEmbed:
    @pytest.mark.asyncio
    async def test_single_text_returns_float_vector(self, client):
        result = await client.aembed(model=MODEL, input="Hello world")
        print(f"\n[aembed] dim={len(result)}, first_5={result[:5]}")
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(x, float) for x in result)


class TestEmbedBatch:
    def test_batch_count_matches_input(self, client):
        texts = ["apple", "banana", "cherry", "dragon fruit"]
        result = client.embed_batch(model=MODEL, input=texts)
        print(f"\n[embed_batch] count={len(result)}, dims={[len(v) for v in result]}")
        assert isinstance(result, list)
        assert len(result) == len(texts)
        assert all(isinstance(v, list) and len(v) > 0 for v in result)
        assert all(isinstance(x, float) for v in result for x in v[:1])


class TestAEmbedBatch:
    @pytest.mark.asyncio
    async def test_batch_count_matches_input(self, client):
        texts = ["red", "green", "blue"]
        result = await client.aembed_batch(model=MODEL, input=texts)
        print(f"\n[aembed_batch] count={len(result)}, dims={[len(v) for v in result]}")
        assert isinstance(result, list)
        assert len(result) == len(texts)
        assert all(isinstance(v, list) and len(v) > 0 for v in result)
