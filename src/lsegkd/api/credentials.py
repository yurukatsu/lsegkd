from __future__ import annotations

import os

from lsegkd.core.auth import Credentials as BaseCredentials


LSEG_KNOWLEDGE_DIRECT_API_BASE_URL: str = "https://api.rkd.refinitiv.com/"


class Credentials(BaseCredentials):
    """Credentials for the LSEG Knowledge Direct API.

    Reads `LSEG_KNOWLEDGE_DIRECT_USERNAME`, `_APP_ID`, `_PASSWORD` from the
    environment when not provided explicitly. Raises on construction if any
    required field is missing, so post-init the three credential attributes
    are guaranteed non-empty strings.
    """

    username: str
    app_id: str
    password: str
    base_url: str

    def __init__(
        self,
        *,
        username: str | None = None,
        app_id: str | None = None,
        password: str | None = None,
        base_url: str | None = None,
    ) -> None:
        u = username or os.getenv("LSEG_KNOWLEDGE_DIRECT_USERNAME")
        a = app_id or os.getenv("LSEG_KNOWLEDGE_DIRECT_APP_ID")
        p = password or os.getenv("LSEG_KNOWLEDGE_DIRECT_PASSWORD")

        if not (u and a and p):
            raise ValueError(
                "Credentials are not fully set. Please provide username, "
                "app_id, and password (or set the corresponding "
                "LSEG_KNOWLEDGE_DIRECT_* environment variables)."
            )

        self.username = u
        self.app_id = a
        self.password = p
        self.base_url = base_url or LSEG_KNOWLEDGE_DIRECT_API_BASE_URL

    def is_valid(self) -> bool:
        return bool(self.username and self.app_id and self.password)
