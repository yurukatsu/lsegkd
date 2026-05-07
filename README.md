# LSEG Knowledge Direct Python API

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org)
[![CI](https://img.shields.io/github/actions/workflow/status/yurukatsu/lseg-knowledge-direct/ci.yml?branch=master&label=CI)](https://github.com/yurukatsu/lseg-knowledge-direct/actions/workflows/ci.yml)
[![codecov](https://img.shields.io/codecov/c/github/yurukatsu/lseg-knowledge-direct?branch=master)](https://codecov.io/gh/yurukatsu/lseg-knowledge-direct)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python client for the **LSEG Knowledge Direct** REST API. It authenticates,
downloads event headlines + transcripts, parses transcript XML into typed
Pydantic models, and ships a Typer-based CLI for bulk download.

## Features

- Authentication and short-lived service token issuance
- Paginated event-headline retrieval (`GetEventHeadlines`) with country and
  publication-status filters
- Sync and async transcript document fetching with automatic public-URL →
  signed-URL fallback (`GetDocument`)
- Pydantic models for headlines and parsed transcripts
- Typer CLI with progress bar, idempotent re-runs, and pagination loop

## Installation

### From PyPI

```bash
uv add lsegkd
```

or

```bash
pip install lsegkd
```

### From source (development)

```bash
git clone https://github.com/yurukatsu/lseg-knowledge-direct.git
cd lseg-knowledge-direct
uv sync --all-groups
```

## Authentication

Set the three environment variables (e.g. via a `.env` file — see
[`.env.sample`](.env.sample)):

```bash
LSEG_KNOWLEDGE_DIRECT_USERNAME=your_username
LSEG_KNOWLEDGE_DIRECT_APP_ID=your_app_id
LSEG_KNOWLEDGE_DIRECT_PASSWORD=your_password
```

Or pass them directly when constructing `Credentials`:

```python
from lsegkd import Credentials

credentials = Credentials(
    username="your_username",
    app_id="your_app_id",
    password="your_password",
)
```

## CLI usage

```bash
# Minimum: a date range
uv run lsegkd -d .env fetch-transcripts --from-date 2025-11-22 --to-date 2025-11-23

# Multiple countries (comma-separated or repeated)
uv run lsegkd -d .env fetch-transcripts \
    --from-date 2025-11-22 --to-date 2025-11-23 \
    --countries US,UK,JP

# All transcript statuses, force re-download, custom output dir
uv run lsegkd -d .env fetch-transcripts \
    --from-date 2025-11-22 --to-date 2025-11-23 \
    --transcript-status any \
    --no-skip-existing \
    --output-dir ./data/raw
```

Run `uv run lsegkd fetch-transcripts --help` for the full option list.

### Output layout

The `fetch-transcripts` command writes three files per event under `output_dir`:

```
<output_dir>/
├── xml/<EventId>.xml             raw transcript XML
├── headlines/<EventId>.json      EventHeadline metadata
└── transcripts/<EventId>.json    parsed EventTranscript
```

Re-runs skip events whose `xml/` and `transcripts/` JSON already exist
(`--skip-existing` is on by default; pass `--no-skip-existing` to force).

## Python API usage

```python
import asyncio
from lsegkd import (
    Credentials,
    EventTranscriptParser,
    StreetEventsServiceClient,
    TokenManagementServiceClient,
)


async def main() -> None:
    credentials = Credentials()  # reads env vars

    # Exchange username/password for a short-lived service token
    token = TokenManagementServiceClient(credentials).create_service_token()

    client = StreetEventsServiceClient(
        credentials=credentials,
        token=token.token,
        async_mode=True,
    )

    try:
        response = client.get_event_headlines(
            from_date=...,  # datetime
            to_date=...,    # datetime
            countries=["US", "UK"],
            transcript_status="Final",
        )

        for headline in response.extract_event_headlines():
            if headline.Transcript is None:
                continue
            xml = await client.aget_document(
                transcript_id=headline.Transcript.TranscriptId
            )
            event = EventTranscriptParser.from_string(xml).parse()
            # event is a Pydantic EventTranscript — use it however you need
    finally:
        await client.aclose()


asyncio.run(main())
```

Pydantic data types (`EventHeadline`, `Duration`, `Organization`, `Symbol`,
`PaginationResult`, ...) live in [`lsegkd.api.types`](src/lsegkd/api/types.py)
and are also re-exported from `lsegkd.api`. Parsed transcript types
(`EventTranscript`, `Speaker`, `Episode`, `Section`, `Turn`, ...) live in
[`lsegkd.xml.transcript`](src/lsegkd/xml/transcript.py).

## Development

```bash
uv sync --all-groups
uv run poe check       # ruff format + ruff check + ty + pytest
uv run poe test        # tests only
```

See [CLAUDE.md](CLAUDE.md) for architecture notes and the conventions enforced
by the codebase (HTTP / endpoint base classes, type-naming rules, the
LSEG-API quirks pinned by tests).

## License

MIT — see [LICENSE](LICENSE).
