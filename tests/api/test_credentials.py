from __future__ import annotations

import pytest

from lsegkd.api import Credentials


def test_explicit_args_populate_fields():
    creds = Credentials(username="u", app_id="a", password="p")
    assert creds.username == "u"
    assert creds.app_id == "a"
    assert creds.password == "p"
    assert creds.base_url == "https://api.rkd.refinitiv.com/"
    assert creds.is_valid()


def test_missing_field_raises(monkeypatch):
    monkeypatch.delenv("LSEG_KNOWLEDGE_DIRECT_USERNAME", raising=False)
    monkeypatch.delenv("LSEG_KNOWLEDGE_DIRECT_APP_ID", raising=False)
    monkeypatch.delenv("LSEG_KNOWLEDGE_DIRECT_PASSWORD", raising=False)
    with pytest.raises(ValueError, match="Credentials"):
        Credentials(username="u", app_id="a")  # password missing


def test_env_vars_used_when_kwargs_omitted(monkeypatch):
    monkeypatch.setenv("LSEG_KNOWLEDGE_DIRECT_USERNAME", "envuser")
    monkeypatch.setenv("LSEG_KNOWLEDGE_DIRECT_APP_ID", "envapp")
    monkeypatch.setenv("LSEG_KNOWLEDGE_DIRECT_PASSWORD", "envpw")
    creds = Credentials()
    assert (creds.username, creds.app_id, creds.password) == (
        "envuser",
        "envapp",
        "envpw",
    )


def test_explicit_kwargs_override_env(monkeypatch):
    monkeypatch.setenv("LSEG_KNOWLEDGE_DIRECT_USERNAME", "envuser")
    monkeypatch.setenv("LSEG_KNOWLEDGE_DIRECT_APP_ID", "envapp")
    monkeypatch.setenv("LSEG_KNOWLEDGE_DIRECT_PASSWORD", "envpw")
    creds = Credentials(username="explicit", app_id="a", password="p")
    assert creds.username == "explicit"


def test_custom_base_url():
    creds = Credentials(
        username="u", app_id="a", password="p", base_url="https://staging.example/"
    )
    assert creds.base_url == "https://staging.example/"
