from __future__ import annotations

import json

import httpx
import pytest
import respx

from lsegkd.api import StreetEventsServiceClient


HEADLINES_URL = (
    "https://api.rkd.refinitiv.com/"
    "api/StreetEvents/StreetEvents.svc/REST/StreetEvents_2/GetEventHeadlines_1"
)
GET_DOCUMENT_URL = (
    "https://api.rkd.refinitiv.com/"
    "api/StreetEvents/StreetEvents.svc/REST/StreetEvents_2/GetDocument_1"
)
DOCUMENT_TEMPLATE = (
    "https://api.rkd.refinitiv.com/api/streetevents/documents/"
    "{transcript_id}/Transcript/Xml.ashx"
)


HEADLINES_BODY = {
    "GetEventHeadlines_Response_1": {
        "PaginationResult": {
            "PageNumber": 1,
            "RecordsOnPage": 1,
            "RecordsPerPage": 1000,
            "TotalRecords": 1,
        },
        "EventHeadlines": {
            "Headline": [
                {
                    "EventId": 42,
                    "EventType": "Earnings",
                    "Name": "Acme Q4 Earnings",
                    "CountryCode": "US",
                    "LastUpdate": "2025-01-15T10:30:00Z",
                    "Duration": {
                        "StartDateTime": "2025-01-15T15:00:00Z",
                        "StartQualifier": "Actual",
                        "EndDateTime": "2025-01-15T16:00:00Z",
                        "EndQualifier": "Actual",
                        "IsEstimate": False,
                    },
                    "Organization": {"Name": "Acme Corp"},
                    "Transcript": {
                        "TranscriptId": "T123",
                        "Locale": "en",
                        "Status": "Final",
                        "DeliveryType": "Live",
                    },
                    "RsvpRequired": False,
                }
            ]
        },
    }
}


@pytest.fixture
def client(credentials):
    return StreetEventsServiceClient(credentials, token="auth-token-xyz")


@respx.mock
def test_get_event_headlines_sends_auth_headers_and_parses(client):
    route = respx.post(HEADLINES_URL).mock(
        return_value=httpx.Response(200, json=HEADLINES_BODY)
    )
    response = client.get_event_headlines(records_per_page=1000)

    pagination = response.extract_pagination_result()
    assert pagination.TotalRecords == 1

    headlines = list(response.extract_event_headlines())
    assert len(headlines) == 1
    # EventId comes from the API as int; the model coerces it to str
    assert headlines[0].EventId == "42"
    assert headlines[0].Transcript is not None
    assert headlines[0].Transcript.TranscriptId == "T123"

    request = route.calls.last.request
    assert request.headers["X-Trkd-Auth-ApplicationID"] == "testapp"
    assert request.headers["X-Trkd-Auth-Token"] == "auth-token-xyz"


@respx.mock
def test_get_event_headlines_payload_includes_filters(client):
    route = respx.post(HEADLINES_URL).mock(
        return_value=httpx.Response(200, json=HEADLINES_BODY)
    )
    client.get_event_headlines(countries=["US", "UK"], transcript_status="Preliminary")

    payload = json.loads(route.calls.last.request.read())
    parameters = payload["GetEventHeadlines_Request_1"]
    # Preserved quirk: ContextCodes is a one-element JSON array (from a tuple)
    assert isinstance(parameters["ContextCodes"], list)
    assert parameters["ContextCodes"][0]["Values"]["Value"] == ["US", "UK"]
    assert (
        parameters["ContentFilters"]["TranscriptFilter"][0]["status"] == "Preliminary"
    )


@respx.mock
def test_get_document_uses_template_url(client):
    respx.get(DOCUMENT_TEMPLATE.format(transcript_id="T123")).mock(
        return_value=httpx.Response(200, text="<xml>content</xml>")
    )
    assert client.get_document("T123") == "<xml>content</xml>"


@respx.mock
def test_get_document_falls_back_to_signed_url(client):
    respx.get(DOCUMENT_TEMPLATE.format(transcript_id="T123")).mock(
        return_value=httpx.Response(404)
    )
    respx.post(GET_DOCUMENT_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "GetDocument_Response_1": {
                    "DocumentURLSecure": "https://signed.example/doc.xml"
                }
            },
        )
    )
    respx.get("https://signed.example/doc.xml").mock(
        return_value=httpx.Response(200, text="<xml>fallback</xml>")
    )
    assert client.get_document("T123") == "<xml>fallback</xml>"


@respx.mock
async def test_aget_document_uses_template_url(credentials):
    client = StreetEventsServiceClient(credentials, token="t", async_mode=True)
    respx.get(DOCUMENT_TEMPLATE.format(transcript_id="T999")).mock(
        return_value=httpx.Response(200, text="<async/>")
    )
    try:
        assert await client.aget_document("T999") == "<async/>"
    finally:
        await client.aclose()


@respx.mock
async def test_aget_document_falls_back(credentials):
    client = StreetEventsServiceClient(credentials, token="t", async_mode=True)
    respx.get(DOCUMENT_TEMPLATE.format(transcript_id="T999")).mock(
        return_value=httpx.Response(500)
    )
    respx.post(GET_DOCUMENT_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "GetDocument_Response_1": {
                    "DocumentURLSecure": "https://signed.example/async.xml"
                }
            },
        )
    )
    respx.get("https://signed.example/async.xml").mock(
        return_value=httpx.Response(200, text="<async-fallback/>")
    )
    try:
        assert await client.aget_document("T999") == "<async-fallback/>"
    finally:
        await client.aclose()


def test_aget_document_requires_async_mode(credentials):
    client = StreetEventsServiceClient(credentials, token="t", async_mode=False)
    import asyncio

    with pytest.raises(RuntimeError, match="Async client"):
        asyncio.run(client.aget_document("T1"))
