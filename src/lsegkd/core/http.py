"""Reusable HTTP client / endpoint base classes.

Concrete service clients subclass `BaseHttpClient`; concrete operations
subclass `BaseHttpEndpoint`. The endpoint helpers (`post_json`, `aget_text`,
etc.) cover the common JSON-POST / text-GET cases so that subclass code
focuses on payload shaping and response parsing. Both sync and async paths
go through `httpx`, so the only HTTP dependency is httpx.
"""

from __future__ import annotations

from abc import ABC
from typing import Any
from urllib.parse import urljoin

import httpx

from lsegkd.core.auth import AuthStrategy


class BaseHttpClient(ABC):
    """Base class for an HTTP service client.

    Holds the resolved base URL, an optional `AuthStrategy`, and an optional
    shared `httpx.AsyncClient` used by async endpoints. Concrete service
    clients are thin wrappers that instantiate `BaseHttpEndpoint` subclasses
    per call and forward arguments.
    """

    def __init__(
        self,
        base_url: str,
        *,
        auth: AuthStrategy | None = None,
        async_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("base_url must be a non-empty string.")
        self.base_url = base_url
        self.auth = auth
        self.async_client = async_client


class BaseHttpEndpoint(ABC):
    """A single HTTP endpoint within a service.

    Subclasses set `path` (relative to the parent client's base URL) and
    implement the operation as a public method (e.g. `get()`, `aget()`).
    Helpers handle URL composition, header building (with auth applied), and
    the common JSON-POST / text-GET cases.
    """

    path: str

    def __init__(self, client: BaseHttpClient) -> None:
        self._client = client

    @property
    def url(self) -> str:
        base = self._client.base_url
        if not base.endswith("/"):
            base = base + "/"
        return urljoin(base, self.path)

    def headers(
        self,
        *,
        json_body: bool = True,
        extra: dict[str, str] | None = None,
    ) -> dict[str, str]:
        headers: dict[str, str] = {}
        if json_body:
            headers["Content-Type"] = "application/json; charset=utf-8"
        if extra:
            headers.update(extra)
        if self._client.auth is not None:
            headers = self._client.auth.apply(headers)
        return headers

    def post_json(
        self,
        payload: dict[str, Any],
        *,
        timeout: int = 30,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        response = httpx.post(
            self.url,
            json=payload,
            headers=self.headers(extra=extra_headers),
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    async def apost_json(
        self,
        payload: dict[str, Any],
        *,
        timeout: int = 30,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        client = self._require_async_client()
        response = await client.post(
            self.url,
            json=payload,
            headers=self.headers(extra=extra_headers),
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_text(self, url: str | None = None, *, timeout: int = 30) -> str:
        response = httpx.get(url or self.url, timeout=timeout)
        response.raise_for_status()
        return response.text

    async def aget_text(self, url: str | None = None, *, timeout: int = 30) -> str:
        client = self._require_async_client()
        response = await client.get(url or self.url, timeout=timeout)
        response.raise_for_status()
        return response.text

    def _require_async_client(self) -> httpx.AsyncClient:
        client = self._client.async_client
        if client is None:
            raise RuntimeError(
                "Async client is not configured on the parent client; "
                "construct the client with async_client=httpx.AsyncClient()."
            )
        return client
