"""Public surface of the LSEG Knowledge Direct REST client.

Most user code only needs the names re-exported here. Pydantic data types
live in `lsegkd.api.types` (also re-exported below).
"""

from lsegkd.api.credentials import Credentials
from lsegkd.api.street_events import (
    GetEventHeadlinesResponse,
    StreetEventsServiceClient,
)
from lsegkd.api.token_management import TokenManagementServiceClient
from lsegkd.api.types import (
    BriefSummary,
    ContentStatus,
    CreateServiceTokenResponse,
    DialIn,
    Duration,
    EventHeadline,
    Organization,
    PaginationResult,
    Symbol,
    SymbolList,
    TranscriptInfo,
    Webcast,
)

__all__ = [
    # Clients
    "Credentials",
    "StreetEventsServiceClient",
    "TokenManagementServiceClient",
    # Response wrappers
    "GetEventHeadlinesResponse",
    # Types (also at lsegkd.api.types)
    "BriefSummary",
    "ContentStatus",
    "CreateServiceTokenResponse",
    "DialIn",
    "Duration",
    "EventHeadline",
    "Organization",
    "PaginationResult",
    "Symbol",
    "SymbolList",
    "TranscriptInfo",
    "Webcast",
]
