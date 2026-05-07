"""LSEG Knowledge Direct toolkit — top-level convenience re-exports.

The most-frequently-used names are re-exported here so user code can write
`from lsegkd import EventHeadline, EventTranscriptParser, ...` in one line.
Sub-modules (`lsegkd.api`, `lsegkd.xml`, `lsegkd.core`) remain the source of
truth — see their own ``__init__.py`` for the full public surface.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from lsegkd.api import (
    Credentials,
    EventHeadline,
    StreetEventsServiceClient,
    TokenManagementServiceClient,
)
from lsegkd.xml import EventTranscript, EventTranscriptParser

try:
    __version__ = _pkg_version("lsegkd")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = [
    "Credentials",
    "EventHeadline",
    "EventTranscript",
    "EventTranscriptParser",
    "StreetEventsServiceClient",
    "TokenManagementServiceClient",
    "__version__",
]
