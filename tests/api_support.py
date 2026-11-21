"""Small thread-free ASGI harness for the Phase 3 test suite."""

import asyncio
import httpx


class AsgiClient:
    def __init__(self, app, *, timeout=5):
        self.app = app
        self.timeout = timeout

    def request(self, method, path, **kwargs):
        async def send():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self.app, raise_app_exceptions=False),
                base_url="http://test",
            ) as client:
                return await asyncio.wait_for(
                    client.request(method, path, **kwargs), timeout=self.timeout,
                )
        return asyncio.run(send())

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def options(self, path, **kwargs):
        return self.request("OPTIONS", path, **kwargs)

