"""Token Management service: anonymous service-token issuance."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from lsegkd.api.credentials import Credentials
from lsegkd.api.types import CreateServiceTokenResponse
from lsegkd.api.utils import parse_datetime
from lsegkd.core.http import BaseHttpClient, BaseHttpEndpoint


def _parse_token_response(response: dict[str, Any]) -> CreateServiceTokenResponse:
    """Validate and unpack a CreateServiceToken envelope into the model."""
    token_response = response.get("CreateServiceToken_Response_1")
    if not token_response:
        raise ValueError(
            "Invalid response format: missing 'CreateServiceToken_Response_1'"
        )

    token = token_response.get("Token")
    if not token:
        raise ValueError("Invalid response format: missing 'Token'")

    expiration_str = token_response.get("Expiration")
    if not expiration_str:
        raise ValueError("Invalid response format: missing 'Expiration'")

    return CreateServiceTokenResponse(
        token=token, expiration=parse_datetime(expiration_str)
    )


class CreateServiceToken(BaseHttpEndpoint):
    """Method to exchange username/password for a short-lived service token."""

    path: str = "CreateServiceToken_1"
    _client: TokenManagementServiceClient

    def _payload(self) -> dict[str, Any]:
        creds = self._client.credentials
        return {
            "CreateServiceToken_Request_1": {
                "ApplicationID": creds.app_id,
                "Username": creds.username,
                "Password": creds.password,
            }
        }

    def get(self, *, timeout: int = 30) -> CreateServiceTokenResponse:
        return _parse_token_response(self.post_json(self._payload(), timeout=timeout))


class TokenManagementServiceClient(BaseHttpClient):
    """Client for the (anonymous) Token Management service.

    This service issues short-lived service tokens that authenticate calls to
    other LSEG Knowledge Direct services. It is unauthenticated itself —
    credentials travel in the request body, not in headers.
    """

    SERVICE_PATH: str = (
        "api/TokenManagement/TokenManagement.svc/REST/Anonymous/TokenManagement_1/"
    )

    def __init__(self, credentials: Credentials) -> None:
        super().__init__(base_url=urljoin(credentials.base_url, self.SERVICE_PATH))
        self.credentials = credentials

    def create_service_token(self, *, timeout: int = 30) -> CreateServiceTokenResponse:
        return CreateServiceToken(self).get(timeout=timeout)
