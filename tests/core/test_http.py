from __future__ import annotations

import httpx
import pytest
import respx

from lsegkd.core.auth import TokenAuth
from lsegkd.core.http import BaseHttpClient, BaseHttpEndpoint


class DummyClient(BaseHttpClient):
    pass


class DummyEndpoint(BaseHttpEndpoint):
    path = "things/"


@pytest.fixture
def client():
    return DummyClient("https://example.com/svc/", auth=TokenAuth({"X-Token": "t"}))


@pytest.fixture
def endpoint(client):
    return DummyEndpoint(client)


def test_client_rejects_empty_base_url():
    with pytest.raises(ValueError):
        DummyClient("")


def test_url_joins_base_and_path(endpoint):
    assert endpoint.url == "https://example.com/svc/things/"


def test_url_appends_slash_to_base_when_missing():
    client = DummyClient("https://example.com/svc")
    endpoint = DummyEndpoint(client)
    assert endpoint.url == "https://example.com/svc/things/"


def test_headers_include_content_type_and_auth(endpoint):
    headers = endpoint.headers()
    assert headers == {
        "Content-Type": "application/json; charset=utf-8",
        "X-Token": "t",
    }


def test_headers_can_skip_content_type(endpoint):
    headers = endpoint.headers(json_body=False)
    assert headers == {"X-Token": "t"}


def test_headers_merge_extras(endpoint):
    headers = endpoint.headers(extra={"X-Trace": "abc"})
    assert headers["X-Trace"] == "abc"
    assert headers["X-Token"] == "t"


def test_headers_without_auth():
    endpoint = DummyEndpoint(DummyClient("https://example.com/"))
    assert "X-Token" not in endpoint.headers()


@respx.mock
def test_post_json_sends_payload_and_returns_parsed(endpoint):
    route = respx.post("https://example.com/svc/things/").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    result = endpoint.post_json({"hello": "world"})
    assert result == {"ok": True}

    assert route.called
    request = route.calls.last.request
    assert request.headers["X-Token"] == "t"
    assert request.headers["Content-Type"].startswith("application/json")
    import json

    assert json.loads(request.read()) == {"hello": "world"}


@respx.mock
def test_post_json_raises_on_4xx(endpoint):
    respx.post("https://example.com/svc/things/").mock(
        return_value=httpx.Response(404, json={"error": "not found"})
    )
    with pytest.raises(httpx.HTTPStatusError):
        endpoint.post_json({})


@respx.mock
def test_get_text_returns_body(endpoint):
    respx.get("https://example.com/svc/things/").mock(
        return_value=httpx.Response(200, text="<xml/>")
    )
    assert endpoint.get_text() == "<xml/>"


@respx.mock
def test_get_text_uses_override_url(endpoint):
    respx.get("https://other.example.com/file").mock(
        return_value=httpx.Response(200, text="hello")
    )
    assert endpoint.get_text("https://other.example.com/file") == "hello"


async def test_apost_json_requires_async_client():
    client = DummyClient("https://example.com/")
    endpoint = DummyEndpoint(client)
    with pytest.raises(RuntimeError, match="Async client"):
        await endpoint.apost_json({})


@respx.mock
async def test_apost_json_uses_shared_async_client():
    async with httpx.AsyncClient() as ac:
        client = DummyClient(
            "https://example.com/svc/",
            auth=TokenAuth({"X-Token": "t"}),
            async_client=ac,
        )
        endpoint = DummyEndpoint(client)
        respx.post("https://example.com/svc/things/").mock(
            return_value=httpx.Response(200, json={"async": True})
        )
        result = await endpoint.apost_json({"q": 1})
        assert result == {"async": True}


@respx.mock
async def test_aget_text_returns_body():
    async with httpx.AsyncClient() as ac:
        client = DummyClient("https://example.com/svc/", async_client=ac)
        endpoint = DummyEndpoint(client)
        respx.get("https://example.com/svc/things/").mock(
            return_value=httpx.Response(200, text="ok")
        )
        assert await endpoint.aget_text() == "ok"
