from __future__ import annotations

import datetime

import httpx
import pytest
import respx

from lsegkd.api import TokenManagementServiceClient


TOKEN_URL = (
    "https://api.rkd.refinitiv.com/"
    "api/TokenManagement/TokenManagement.svc/REST/Anonymous/"
    "TokenManagement_1/CreateServiceToken_1"
)


@respx.mock
def test_create_service_token_returns_parsed_response(credentials):
    route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "CreateServiceToken_Response_1": {
                    "Token": "abc123",
                    "Expiration": "2025-01-15T10:30:00.000Z",
                }
            },
        )
    )
    result = TokenManagementServiceClient(credentials).create_service_token()

    assert result.token == "abc123"
    assert result.expiration == datetime.datetime(2025, 1, 15, 10, 30)

    request = route.calls.last.request
    body = request.read()
    import json

    assert json.loads(body) == {
        "CreateServiceToken_Request_1": {
            "ApplicationID": "testapp",
            "Username": "testuser",
            "Password": "testpass",
        }
    }


@respx.mock
def test_create_service_token_raises_on_missing_envelope(credentials):
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"foo": "bar"}))
    with pytest.raises(ValueError, match="CreateServiceToken_Response_1"):
        TokenManagementServiceClient(credentials).create_service_token()


@respx.mock
def test_create_service_token_raises_on_http_error(credentials):
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(500))
    with pytest.raises(httpx.HTTPStatusError):
        TokenManagementServiceClient(credentials).create_service_token()
