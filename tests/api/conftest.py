from __future__ import annotations

import pytest

from lsegkd.api import Credentials


@pytest.fixture
def credentials() -> Credentials:
    return Credentials(
        username="testuser",
        app_id="testapp",
        password="testpass",
    )
