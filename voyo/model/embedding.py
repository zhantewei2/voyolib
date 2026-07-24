import openai


class EmbeddingClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self._sync_client = openai.OpenAI(base_url=base_url, api_key=api_key)
        self._async_client = openai.AsyncOpenAI(base_url=base_url, api_key=api_key)

    def embed(self, *, model: str, input: str, retry_max: int = 2, **kwargs) -> list[float]:
        last_err: Exception | None = None
        for _ in range(retry_max):
            try:
                resp = self._sync_client.embeddings.create(model=model, input=input, **kwargs)
                return resp.data[0].embedding
            except Exception as err:
                last_err = err
        raise last_err  # type: ignore[misc]

    async def aembed(self, *, model: str, input: str, retry_max: int = 2, **kwargs) -> list[float]:
        last_err: Exception | None = None
        for _ in range(retry_max):
            try:
                resp = await self._async_client.embeddings.create(model=model, input=input, **kwargs)
                return resp.data[0].embedding
            except Exception as err:
                last_err = err
        raise last_err  # type: ignore[misc]

    def embed_batch(self, *, model: str, input: list[str], retry_max: int = 2, **kwargs) -> list[list[float]]:
        last_err: Exception | None = None
        for _ in range(retry_max):
            try:
                resp = self._sync_client.embeddings.create(model=model, input=input, **kwargs)
                return [item.embedding for item in resp.data]
            except Exception as err:
                last_err = err
        raise last_err  # type: ignore[misc]

    async def aembed_batch(self, *, model: str, input: list[str], retry_max: int = 2, **kwargs) -> list[list[float]]:
        last_err: Exception | None = None
        for _ in range(retry_max):
            try:
                resp = await self._async_client.embeddings.create(model=model, input=input, **kwargs)
                return [item.embedding for item in resp.data]
            except Exception as err:
                last_err = err
        raise last_err  # type: ignore[misc]
