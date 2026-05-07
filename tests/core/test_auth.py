from __future__ import annotations

import pytest

from lsegkd.core.auth import AuthStrategy, Credentials, TokenAuth


def test_credentials_is_abstract():
    with pytest.raises(TypeError):
        Credentials()  # type: ignore[abstract]


def test_auth_strategy_is_abstract():
    with pytest.raises(TypeError):
        AuthStrategy()  # type: ignore[abstract]


def test_token_auth_adds_headers():
    auth = TokenAuth({"X-Api-Key": "abc", "X-App-Id": "xyz"})
    result = auth.apply({"Content-Type": "application/json"})
    assert result == {
        "Content-Type": "application/json",
        "X-Api-Key": "abc",
        "X-App-Id": "xyz",
    }


def test_token_auth_overrides_existing_header():
    auth = TokenAuth({"Authorization": "Bearer new"})
    result = auth.apply({"Authorization": "Bearer old"})
    assert result == {"Authorization": "Bearer new"}


def test_token_auth_does_not_mutate_input():
    auth = TokenAuth({"X-Token": "t"})
    original = {"Content-Type": "application/json"}
    auth.apply(original)
    assert original == {"Content-Type": "application/json"}


def test_token_auth_bearer_helper():
    auth = TokenAuth.bearer("abc123")
    assert auth.apply({}) == {"Authorization": "Bearer abc123"}


def test_token_auth_rejects_empty_headers():
    with pytest.raises(ValueError):
        TokenAuth({})
