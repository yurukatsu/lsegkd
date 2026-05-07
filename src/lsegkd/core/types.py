"""Generic Pydantic type aliases shared across the codebase.

Kept in ``lsegkd.core`` (rather than ``lsegkd.api.types`` or
``lsegkd.xml``) so that both subpackages can depend on it without
creating a peer-level import cycle.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BeforeValidator


# Coerces numeric IDs to string. The LSEG API returns event IDs as
# integers, but downstream code (filenames, dict keys, JSON
# stringification) is much happier with strings. Already-string inputs
# pass through unchanged.
StrId = Annotated[str, BeforeValidator(lambda v: str(v) if isinstance(v, int) else v)]


__all__ = ["StrId"]
