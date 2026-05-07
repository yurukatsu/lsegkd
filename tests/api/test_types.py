"""Tests for behaviour built into the Pydantic models in lsegkd.api.types."""

from __future__ import annotations

import pytest

from lsegkd.api.types import EventHeadline


_BASE_HEADLINE = {
    "EventType": "EarningsCallsAndPresentations",
    "Name": "Acme Q1",
    "CountryCode": "US",
    "LastUpdate": "2025-01-15T10:30:00Z",
    "Duration": {
        "StartDateTime": "2025-01-15T15:00:00Z",
        "StartQualifier": "DateTime",
        "EndDateTime": "2025-01-15T16:00:00Z",
        "EndQualifier": "DateTime",
        "IsEstimate": False,
    },
    "Organization": {"Name": "Acme"},
    "RsvpRequired": False,
}


def test_event_id_int_is_coerced_to_str():
    """The LSEG API returns EventId as an integer; we want a string everywhere."""
    h = EventHeadline.model_validate({**_BASE_HEADLINE, "EventId": 16721770})
    assert h.EventId == "16721770"
    assert isinstance(h.EventId, str)


def test_event_id_str_passes_through():
    h = EventHeadline.model_validate({**_BASE_HEADLINE, "EventId": "16721770"})
    assert h.EventId == "16721770"


def test_event_id_invalid_type_rejected():
    with pytest.raises(ValueError):
        EventHeadline.model_validate({**_BASE_HEADLINE, "EventId": ["not", "an", "id"]})
