"""Tests for the shared Pydantic type aliases in lsegkd.core.types."""

from __future__ import annotations

from typing import Optional

import pytest
from pydantic import BaseModel

from lsegkd.core.types import StrId


class _Holder(BaseModel):
    id: StrId
    optional_id: Optional[StrId] = None


def test_int_coerced_to_str():
    h = _Holder.model_validate({"id": 16721770})
    assert h.id == "16721770"
    assert isinstance(h.id, str)


def test_str_passes_through():
    h = _Holder.model_validate({"id": "abc"})
    assert h.id == "abc"


def test_optional_none_stays_none():
    h = _Holder.model_validate({"id": "x"})
    assert h.optional_id is None


def test_optional_int_coerced():
    h = _Holder.model_validate({"id": "x", "optional_id": 42})
    assert h.optional_id == "42"


def test_unsupported_type_rejected():
    with pytest.raises(ValueError):
        _Holder.model_validate({"id": ["not", "an", "id"]})
