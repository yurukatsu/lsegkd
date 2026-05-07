# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This package is **data-acquisition only**: it authenticates against the LSEG Knowledge Direct REST API, downloads event headlines + transcripts, and parses transcript XML into Pydantic models. Storage / search / analytics belong in downstream consumers, not here.

## Common commands

This project uses `uv` for dependency management and `poethepoet` (`poe`) as the task runner. Python 3.12+.

- Install dev deps: `uv sync --all-groups`
- Format: `uv run poe format` (ruff format)
- Lint + autofix: `uv run poe lint` (ruff check --fix)
- Type check: `uv run poe type-check` (**ty**, Astral's type checker)
- Test: `uv run poe test` (pytest)
- All of the above (= pre-commit hook entry): `uv run poe check`
- Run a single test: `uv run pytest tests/api/test_street_events.py::test_get_document_falls_back_to_signed_url`
- Run the CLI: `uv run lsegkd -d .env fetch-transcripts --from-date YYYY-MM-DD --to-date YYYY-MM-DD --countries US`

## Authentication

API calls require three credentials, normally read from a `.env` file (see [.env.sample](.env.sample)):

- `LSEG_KNOWLEDGE_DIRECT_USERNAME`
- `LSEG_KNOWLEDGE_DIRECT_APP_ID`
- `LSEG_KNOWLEDGE_DIRECT_PASSWORD`

[Credentials](src/lsegkd/api/credentials.py) reads these from the environment unless explicit kwargs are passed; it raises in `__init__` if any are missing, so post-init the three fields are guaranteed non-empty `str`. The CLI loads `.env` via the top-level `-d/--dotenv-path` option *before* the subcommand runs.

## Architecture

```
src/lsegkd/
├── cli.py                  Typer-based CLI (fetch-transcripts command)
├── core/                   Reusable HTTP / auth abstractions
│   ├── auth.py             Credentials (ABC), AuthStrategy, TokenAuth
│   └── http.py             BaseHttpClient, BaseHttpEndpoint
├── api/                    LSEG REST clients (one module per service)
│   ├── credentials.py      LSEG-specific Credentials
│   ├── types.py            All Pydantic models + ContentStatus — import from here
│   ├── street_events.py    StreetEventsServiceClient + GetEventHeadlines + GetDocument
│   ├── token_management.py TokenManagementServiceClient + CreateServiceToken
│   └── utils.py            parse_datetime
└── xml/                    Transcript XML parser
    └── transcript.py
```

The most-used names are re-exported from [api/__init__.py](src/lsegkd/api/__init__.py) so users can write `from lsegkd.api import EventHeadline, StreetEventsServiceClient, Credentials` rather than reaching into sub-modules. The top-level [__init__.py](src/lsegkd/__init__.py) goes one step further and re-exports the everyday surface — `Credentials`, `StreetEventsServiceClient`, `TokenManagementServiceClient`, `EventHeadline`, `EventTranscript`, `EventTranscriptParser` — so `from lsegkd import EventHeadline` works in one line.

Type-name conventions: data models drop the `*Model` suffix (matching `lsegkd.xml`); `ContentStatus` is the publication-status literal (`"Preliminary"|"Final"|"Expected"|"InProgress"`); `TranscriptInfo` is headline metadata (distinct from the parsed `lsegkd.xml.Transcript`). Three classes (`BriefSummary`, `SymbolList`, `DialIn`) carry names that differ from their JSON keys to avoid a pydantic shadowing bug — see the docstring in [types.py](src/lsegkd/api/types.py) for the rationale.

### `core` — what the rest of the codebase builds on

| Symbol | Purpose |
|---|---|
| [Credentials](src/lsegkd/core/auth.py) (ABC) | Marker base for credential bundles |
| [AuthStrategy](src/lsegkd/core/auth.py) (ABC) | `apply(headers) -> headers`; injects auth into outgoing requests |
| [TokenAuth](src/lsegkd/core/auth.py) | Concrete `AuthStrategy` adding a fixed header set; `TokenAuth.bearer(token)` for the common case |
| [BaseHttpClient](src/lsegkd/core/http.py) | Holds `base_url`, optional `auth`, optional shared `httpx.AsyncClient` |
| [BaseHttpEndpoint](src/lsegkd/core/http.py) | A single endpoint; subclass sets `path` and implements the operation. Provides `url`, `headers()`, `post_json()`, `apost_json()`, `get_text()`, `aget_text()` — both sync and async go through httpx |

When adding a new HTTP service, subclass `BaseHttpClient` for the service and `BaseHttpEndpoint` per operation. The convention is **one module per service** with the client + its endpoint subclasses + any operation-specific response wrapper co-located — see [api/street_events.py](src/lsegkd/api/street_events.py) and [api/token_management.py](src/lsegkd/api/token_management.py). Pure data types (Pydantic models, `ContentStatus` literal) live in [api/types.py](src/lsegkd/api/types.py).

### `api` — the LSEG service clients

Two services on top of `core.http`:

1. **TokenManagement** ([token_management.py](src/lsegkd/api/token_management.py)) — anonymous endpoint that exchanges username/app_id/password for a short-lived service token (`CreateServiceTokenResponse`). No `auth` strategy; credentials travel in the request body.
2. **StreetEvents** ([street_events.py](src/lsegkd/api/street_events.py)) — authenticated via `TokenAuth({"X-Trkd-Auth-ApplicationID": ..., "X-Trkd-Auth-Token": ...})`. Two operations:
   - `GetEventHeadlines` — paginated event/transcript metadata; `GetEventHeadlinesResponse.extract_event_headlines()` is a generator of `EventHeadline`, `extract_pagination_result()` returns `PaginationResult`.
   - `GetDocument` — fetches transcript XML. **Two-step strategy**: tries the templated public URL (`.../streetevents/documents/{transcript_id}/Transcript/Xml.ashx`) first and falls back to the documented `GetDocument_1` JSON endpoint (which returns a signed `DocumentURLSecure`). See `GetDocument.get` / `aget` in [street_events.py](src/lsegkd/api/street_events.py).

#### Sync vs async

Pass `async_mode=True` to `StreetEventsServiceClient` to construct a shared `httpx.AsyncClient` used by `aget_document(...)`. Calling an async method without `async_mode=True` raises `RuntimeError("Async client is not configured...")`. Always `await client.aclose()` when done.

#### Quirks worth preserving (don't refactor away)

- **`ContextCodes` is a one-element JSON array, not an object.** `GetEventHeadlines._create_payload` in [street_events.py](src/lsegkd/api/street_events.py) wraps the dict in a single-element tuple intentionally — httpx serializes tuples as JSON arrays, and the LSEG API expects exactly that shape. Test [test_get_event_headlines_payload_includes_filters](tests/api/test_street_events.py) pins this.
- **`parse_datetime` always re-appends "Z"** ([utils.py](src/lsegkd/api/utils.py)). It splits on `.`, takes the first half, and adds `"Z"`. This means inputs *without* fractional seconds end up with a doubled `ZZ` and fall through every pattern. Tests use `"...000Z"` form to work around this.
- **`EventHeadline.EventId` is a `str`** even when the API returns it as `int` — `StrId` (`Annotated[str, BeforeValidator(...)]`) coerces. Pinned in [tests/api/test_types.py](tests/api/test_types.py).

### `xml` — transcript parser

[EventTranscriptParser](src/lsegkd/xml/transcript.py) parses the raw transcript XML returned by `GetDocument` into a Pydantic [EventTranscript](src/lsegkd/xml/transcript.py) tree of `Transcript → Episode → Section → Turn → UtteranceSegment`, plus `speakers: Dict[str, Speaker]` keyed by `id`. Construct via `from_string(xml)` or `from_path(path)`, then call `.parse()`.

The parser handles a quirk: `<Turn>` body interleaves text with `<Sync id=... time=...>` markers and `<br/>` elements. Each `<Sync>` updates the "current" sync_id/time, and the `tail` text after `<Sync>`/`<br>` becomes the next `UtteranceSegment` — segments inherit the timing of the most recent preceding `<Sync>`. Don't refactor `_parse_turn_segments` without preserving that invariant. [test_turn_segments_inherit_last_sync](tests/xml/test_transcript.py) pins it.

### End-to-end flow (the CLI's `fetch-transcripts`)

`Credentials` → `TokenManagementServiceClient.create_service_token()` → `StreetEventsServiceClient(token=..., async_mode=True)` → `get_event_headlines(...)` → for each headline with a transcript: `aget_document(transcript_id)` → write XML, write headline JSON, parse with `EventTranscriptParser` and write parsed JSON. See `_fetch_transcripts` in [cli.py](src/lsegkd/cli.py).

## Testing

- `tests/` mirrors the source layout (`tests/core/`, `tests/api/`, `tests/xml/`).
- HTTP is mocked with **respx** (httpx interception). See [tests/api/test_street_events.py](tests/api/test_street_events.py) for the document-fallback pattern.
- pytest-asyncio is in `auto` mode — `async def test_*` functions run without per-test decorators.
- [tests/api/conftest.py](tests/api/conftest.py) provides a shared `credentials` fixture.
