"""Street Events service: event headlines + transcript document retrieval."""

from __future__ import annotations

import datetime
from typing import Any, Generator, Literal
from urllib.parse import urljoin

import httpx
from loguru import logger

from lsegkd.api.credentials import Credentials
from lsegkd.api.types import (
    EventHeadline,
    PaginationResult,
    ContentStatus,
)
from lsegkd.core.auth import TokenAuth
from lsegkd.core.http import BaseHttpClient, BaseHttpEndpoint


class GetEventHeadlinesResponse:
    """Wraps the GetEventHeadlines API response envelope."""

    _root_key: str = "GetEventHeadlines_Response_1"

    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response.get(self._root_key, {})

        if not self.response:
            raise ValueError("Invalid response format")

    def extract_event_headlines(self) -> Generator[EventHeadline, None, None]:
        """Yield each headline as a validated `EventHeadline`."""
        if not self.response.get("EventHeadlines"):
            raise ValueError("No event headlines found in the response")

        for headline in self.response["EventHeadlines"].get("Headline", []):
            try:
                yield EventHeadline.model_validate(headline)
            except Exception as e:
                raise ValueError(f"Error parsing headline: {headline}\n\n{e}")

    def extract_pagination_result(self) -> PaginationResult:
        """Return the page metadata as a `PaginationResult`."""
        if result := self.response.get("PaginationResult"):
            return PaginationResult.model_validate(result)
        raise ValueError("PaginationResult not found in response")


class GetEventHeadlines(BaseHttpEndpoint):
    """Method to get paginated event headlines + transcript metadata."""

    path: str = "GetEventHeadlines_1"

    @staticmethod
    def _create_payload(
        *,
        page_number: int = 1,
        records_per_page: int = 1000,
        from_date: datetime.datetime | None = None,
        to_date: datetime.datetime | None = None,
        countries: list[str] = ["US"],
        transcript_status: ContentStatus | None = "Final",
        utc_indicator_in_response: bool = False,
    ) -> dict[str, Any]:
        # Typed as dict[str, Any] to allow the heterogeneous values added below
        # (the LSEG API expects ContextCodes wrapped in a single-element tuple,
        # which serializes to a one-element JSON array).
        parameters: dict[str, Any] = {
            "UTCIndicatorInResponse": utc_indicator_in_response,
            "DateTimeRange": {
                "From": from_date.isoformat() if from_date else None,
                "To": to_date.isoformat() if to_date else None,
            },
            "Pagination": {
                "PageNumber": page_number,
                "RecordsPerPage": records_per_page,
            },
        }

        if countries:
            parameters["ContextCodes"] = (
                {
                    "Type": "Geography",
                    "Scheme": "",
                    "Values": {"Value": countries},
                },
            )

        if transcript_status is not None:
            parameters["ContentFilters"] = {
                "TranscriptFilter": [{"status": transcript_status}],
            }

        return {"GetEventHeadlines_Request_1": parameters}

    def get(
        self,
        *,
        page_number: int = 1,
        records_per_page: int = 1000,
        from_date: datetime.datetime | None = None,
        to_date: datetime.datetime | None = None,
        countries: list[str] = ["US"],
        transcript_status: ContentStatus | None = "Final",
        utc_indicator_in_response: bool = False,
        timeout: int = 30,
    ) -> GetEventHeadlinesResponse:
        payload = self._create_payload(
            page_number=page_number,
            records_per_page=records_per_page,
            from_date=from_date,
            to_date=to_date,
            countries=countries,
            transcript_status=transcript_status,
            utc_indicator_in_response=utc_indicator_in_response,
        )
        return GetEventHeadlinesResponse(self.post_json(payload, timeout=timeout))


class GetDocument(BaseHttpEndpoint):
    """Method to fetch a transcript document.

    Tries a templated public URL first
    (`.../streetevents/documents/{transcript_id}/Transcript/Xml.ashx`) and
    falls back to the documented `GetDocument_1` JSON endpoint, which returns
    a signed URL that is then fetched as text. The fallback path matters for
    transcripts whose direct URL is not available.
    """

    path: str = "GetDocument_1"
    DOCUMENT_URL_TEMPLATE: str = (
        "https://api.rkd.refinitiv.com/api/streetevents/documents/"
        "{transcript_id}/Transcript/Xml.ashx"
    )

    @staticmethod
    def _create_payload(
        transcript_id: str,
        document_type: str,
        document_format: str,
        document_last_modified_date: datetime.datetime | None,
        decode_document: Literal[True] = True,
        private_network_url: Literal[False] = False,
    ) -> dict[str, Any]:
        return {
            "GetDocument_Request_1": {
                "DocumentId": transcript_id,
                "DocumentType": document_type,
                "DocumentFormat": document_format,
                "DocumentLastModifiedDate": document_last_modified_date,
                "DecodeDocument": decode_document,
                "PrivateNetworkURL": private_network_url,
            }
        }

    def get_document_url(
        self,
        transcript_id: str,
        *,
        document_type: Literal["Transcript"] = "Transcript",
        document_format: Literal["Xml"] = "Xml",
        document_last_modified_date: datetime.datetime | None = None,
        decode_document: Literal[True] = True,
        private_network_url: Literal[False] = False,
        timeout: int = 30,
    ) -> str:
        result = self.post_json(
            self._create_payload(
                transcript_id=transcript_id,
                document_type=document_type,
                document_format=document_format,
                document_last_modified_date=document_last_modified_date,
                decode_document=decode_document,
                private_network_url=private_network_url,
            ),
            timeout=timeout,
        )
        return result.get("GetDocument_Response_1", {}).get("DocumentURLSecure")

    async def aget_document_url(
        self,
        transcript_id: str,
        *,
        document_type: Literal["Transcript"] = "Transcript",
        document_format: Literal["Xml"] = "Xml",
        document_last_modified_date: datetime.datetime | None = None,
        decode_document: Literal[True] = True,
        private_network_url: Literal[False] = False,
        timeout: int = 30,
    ) -> str:
        result = await self.apost_json(
            self._create_payload(
                transcript_id=transcript_id,
                document_type=document_type,
                document_format=document_format,
                document_last_modified_date=document_last_modified_date,
                decode_document=decode_document,
                private_network_url=private_network_url,
            ),
            timeout=timeout,
        )
        return result.get("GetDocument_Response_1", {}).get("DocumentURLSecure")

    def get(self, transcript_id: str, *, timeout: int = 30) -> str:
        try:
            url = self.DOCUMENT_URL_TEMPLATE.format(transcript_id=transcript_id)
            logger.info(f"Trying standard URL: {url}")
            return self.get_text(url, timeout=timeout)
        except Exception:
            logger.info("Falling back to GetDocument API")
            url = self.get_document_url(transcript_id, timeout=timeout)
            logger.info(f"Trying fallback URL: {url}")
            return self.get_text(url, timeout=timeout)

    async def aget(self, transcript_id: str, *, timeout: int = 30) -> str:
        try:
            url = self.DOCUMENT_URL_TEMPLATE.format(transcript_id=transcript_id)
            logger.info(f"Trying standard URL: {url}")
            return await self.aget_text(url, timeout=timeout)
        except Exception:
            logger.info("Falling back to GetDocument API")
            url = await self.aget_document_url(transcript_id, timeout=timeout)
            logger.info(f"Trying fallback URL: {url}")
            return await self.aget_text(url, timeout=timeout)


class StreetEventsServiceClient(BaseHttpClient):
    """Client for the Street Events service of the LSEG Knowledge Direct API.

    Authenticates every request with the LSEG `X-Trkd-Auth-*` header pair via
    a `TokenAuth` strategy. Pass `async_mode=True` to enable async methods —
    this constructs an `httpx.AsyncClient` shared across all endpoint calls.
    """

    SERVICE_PATH: str = "api/StreetEvents/StreetEvents.svc/REST/StreetEvents_2/"

    def __init__(
        self,
        credentials: Credentials,
        token: str,
        *,
        async_mode: bool = False,
    ) -> None:
        super().__init__(
            base_url=urljoin(credentials.base_url, self.SERVICE_PATH),
            auth=TokenAuth(
                {
                    "X-Trkd-Auth-ApplicationID": credentials.app_id,
                    "X-Trkd-Auth-Token": token,
                }
            ),
            async_client=httpx.AsyncClient() if async_mode else None,
        )
        self.credentials = credentials
        self.token = token

    def get_event_headlines(
        self,
        *,
        page_number: int = 1,
        records_per_page: int = 1000,
        from_date: datetime.datetime | None = None,
        to_date: datetime.datetime | None = None,
        countries: list[str] = ["US"],
        transcript_status: ContentStatus | None = "Final",
        utc_indicator_in_response: bool = False,
        timeout: int = 30,
    ) -> GetEventHeadlinesResponse:
        return GetEventHeadlines(self).get(
            page_number=page_number,
            records_per_page=records_per_page,
            from_date=from_date,
            to_date=to_date,
            countries=countries,
            transcript_status=transcript_status,
            utc_indicator_in_response=utc_indicator_in_response,
            timeout=timeout,
        )

    def get_document(self, transcript_id: str, *, timeout: int = 30) -> str:
        return GetDocument(self).get(transcript_id=transcript_id, timeout=timeout)

    async def aget_document(self, transcript_id: str, *, timeout: int = 30) -> str:
        return await GetDocument(self).aget(
            transcript_id=transcript_id, timeout=timeout
        )

    async def aclose(self) -> None:
        """Close the shared async client, if one was created."""
        if self.async_client is not None:
            await self.async_client.aclose()
