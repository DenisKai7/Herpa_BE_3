import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class ExternalHttpClient:
    def __init__(self, timeout: float = 20):
        self.client = httpx.AsyncClient(timeout=timeout, follow_redirects=False)

    async def close(self) -> None:
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=0.5, max=4),
        retry=retry_if_exception_type(httpx.TransportError),
        reraise=True,
    )
    async def get(self, url: str, params: dict | None = None) -> httpx.Response:
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response
