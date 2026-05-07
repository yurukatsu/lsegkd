from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Mapping


class Credentials(ABC):
    """Base class for credential bundles.

    Subclasses define the fields they need (username/password, API key, etc.)
    and implement is_valid().
    """

    @abstractmethod
    def is_valid(self) -> bool:
        """Return True if all required credential fields are populated."""


class AuthStrategy(ABC):
    """Applies authentication to outgoing HTTP request headers.

    Implementations are stateless w.r.t. the request — all state (token, key,
    credentials) is captured at construction time. `apply()` returns a new
    headers mapping rather than mutating in place.
    """

    @abstractmethod
    def apply(self, headers: dict[str, str]) -> dict[str, str]:
        """Return a copy of `headers` with authentication added."""


class TokenAuth(AuthStrategy):
    """Inject a fixed set of headers into every request.

    Suitable for token / API-key style schemes where authentication is one or
    more static headers (e.g. LSEG's `X-Trkd-Auth-ApplicationID` +
    `X-Trkd-Auth-Token` pair, or a single `Authorization: Bearer ...`).
    """

    def __init__(self, headers: Mapping[str, str]) -> None:
        if not headers:
            raise ValueError("TokenAuth requires at least one header.")
        self._headers = dict(headers)

    @classmethod
    def bearer(cls, token: str) -> TokenAuth:
        return cls({"Authorization": f"Bearer {token}"})

    def apply(self, headers: dict[str, str]) -> dict[str, str]:
        return {**headers, **self._headers}
