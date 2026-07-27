import openai

from voyo.model.types import ExtraBodyInput, ResponseFormat


class ModelClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self._sync_client = openai.OpenAI(base_url=base_url, api_key=api_key)
        self._async_client = openai.AsyncOpenAI(base_url=base_url, api_key=api_key)

    def chat(
        self,
        *,
        model: str,
        messages: list[dict],
        extra_body: ExtraBodyInput | None = None,
        temperature: float = 0.0,
        response_format: ResponseFormat | None = None,
        max_tokens: int = 4096,
        retry_max: int = 1,
        stream: bool = False,
    ):
        last_err: Exception | None = None
        for _ in range(retry_max):
            try:
                return self._sync_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    extra_body=extra_body,
                    stream=stream,
                )
            except Exception as err:
                last_err = err
        raise last_err  # type: ignore[misc]

    async def achat(
        self,
        *,
        model: str,
        messages: list[dict],
        extra_body: ExtraBodyInput | None = None,
        temperature: float = 0.0,
        response_format: ResponseFormat | None = None,
        max_tokens: int = 4096,
        retry_max: int = 1,
        stream: bool = False,
    ):
        last_err: Exception | None = None
        for _ in range(retry_max):
            try:
                return await self._async_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    extra_body=extra_body,
                    stream=stream,
                )
            except Exception as err:
                last_err = err
        raise last_err  # type: ignore[misc]
