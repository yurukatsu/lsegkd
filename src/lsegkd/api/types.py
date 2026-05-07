"""Public data types for the LSEG Knowledge Direct API.

All Pydantic models and Literal types that surface in user code live here so
they can be imported with a shallow path (`from lsegkd.api.types import ...`).
Response *wrappers* that hold raw envelopes and expose extraction methods
stay co-located with the operation that produces them
(see `street_events.GetEventHeadlinesResponse`).

Model and field names mirror the LSEG API JSON envelope (PascalCase) so that
`EventHeadline.model_validate(raw_dict)` works without aliases. There is no
`*Model` suffix — these names match the conventions used in `lsegkd.xml`
(`Speaker`, `Episode`, `Turn`, ...).

Three classes carry a name that differs slightly from the JSON key
(`BriefSummary`, `SymbolList`, `DialIn`) because pydantic resolves an
`Optional[X] = None` annotation to `None` when the type name `X` collides
with the field name in the enclosing model. Keeping the wrapper-class names
distinct from their parent fields sidesteps the issue. These types are
re-exported from `lsegkd.api`.
"""

from __future__ import annotations

import datetime
from typing import Literal, Optional

from pydantic import BaseModel

from lsegkd.core.types import StrId


# Publication status of a piece of content (transcript, brief). Distinct from
# operational statuses used elsewhere — e.g. `LiveDialIn.Status` carries values
# like "Available" and is therefore typed as plain `str`.
ContentStatus = Literal["Preliminary", "Final", "Expected", "InProgress"]


class Duration(BaseModel):
    """Date/time range associated with an event or one of its components.

    Despite the LSEG-side field name "Duration", this is a *range* (start +
    end) rather than a length of time.
    """

    StartDateTime: datetime.datetime
    StartQualifier: str
    EndDateTime: datetime.datetime
    EndQualifier: str
    IsEstimate: bool


class BriefSummary(BaseModel):
    """A short summary descriptor attached to an event (JSON key: ``Brief``)."""

    BriefId: str
    Locale: str
    Status: ContentStatus


class TranscriptInfo(BaseModel):
    """Transcript *metadata* embedded in an event headline.

    Distinct from `lsegkd.xml.transcript.Transcript`, which is the *parsed*
    transcript content (speakers, turns, segments). This model just carries
    the IDs / locale / status needed to fetch and filter transcripts.
    """

    TranscriptId: str
    Locale: str
    Status: ContentStatus
    DeliveryType: str


class Symbol(BaseModel):
    """A single organization symbol (e.g. RIC, ticker)."""

    Type: str
    Value: str


class SymbolList(BaseModel):
    """Wrapper preserving the LSEG envelope shape `{ "Symbol": [...] }`
    (JSON key: ``Symbols``)."""

    Symbol: list[Symbol]


class Organization(BaseModel):
    """The organization the event belongs to."""

    Name: str
    Symbols: Optional[SymbolList] = None


class DialIn(BaseModel):
    """Live dial-in conference information for an event
    (JSON key: ``LiveDialIn``)."""

    Duration: Duration
    PhoneNumber: str
    Password: Optional[str]
    # Operational status (e.g. "Available") — narrower domain than ContentStatus
    Status: str


class Webcast(BaseModel):
    """Live or replay webcast information for an event."""

    Duration: Duration
    Provider: str
    Type: str
    Url: Optional[str]
    WebcastId: str


class EventHeadline(BaseModel):
    """An event headline returned by the GetEventHeadlines API.

    The optional `Transcript` field carries metadata only; use
    `StreetEventsServiceClient.aget_document(transcript_id=...)` to fetch the
    transcript document.
    """

    EventId: StrId
    EventType: str
    Name: str
    CountryCode: str
    LastUpdate: datetime.datetime

    Duration: Duration
    Brief: Optional[BriefSummary] = None
    Organization: Organization

    LiveDialIn: Optional[DialIn] = None
    LiveWebcast: Optional[Webcast] = None
    ReplayWebcast: Optional[Webcast] = None

    Transcript: Optional[TranscriptInfo] = None
    RsvpRequired: bool


class PaginationResult(BaseModel):
    """Page metadata returned alongside a page of headlines."""

    PageNumber: int
    RecordsOnPage: int
    RecordsPerPage: int
    TotalRecords: int


class CreateServiceTokenResponse(BaseModel):
    """Result of `TokenManagementServiceClient.create_service_token()`."""

    token: str
    expiration: datetime.datetime
