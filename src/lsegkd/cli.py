"""Typer-based CLI for the LSEG Knowledge Direct toolkit."""

from __future__ import annotations

import asyncio
import datetime
import json
from enum import Enum
from pathlib import Path
from typing import Annotated

import dotenv
import typer
from loguru import logger
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from lsegkd.api import (
    Credentials,
    EventHeadline,
    StreetEventsServiceClient,
    TokenManagementServiceClient,
)
from lsegkd.api.types import ContentStatus
from lsegkd.xml import EventTranscriptParser


cli = typer.Typer(
    name="lsegkd",
    help="LSEG Knowledge Direct CLI.",
    no_args_is_help=True,
    add_completion=False,
)


class TranscriptStatusOption(str, Enum):
    """CLI choice for filtering transcripts by publication status.

    `any` is a sentinel meaning "do not filter" (passes None to the API).
    """

    Preliminary = "Preliminary"
    Final = "Final"
    Expected = "Expected"
    InProgress = "InProgress"
    Any = "any"


def _to_api_status(opt: TranscriptStatusOption) -> ContentStatus | None:
    return None if opt is TranscriptStatusOption.Any else opt.value  # type: ignore[return-value]


def _expand_countries(countries: list[str]) -> list[str]:
    """Accept both `--countries US,UK` (comma-separated) and `--countries US
    --countries UK` (repeated flag). Each value is split on commas, trimmed,
    upper-cased, and de-duplicated while preserving order. Typer/Click options
    cannot consume a variadic number of space-separated values, so commas are
    the supported single-flag form.
    """
    seen: dict[str, None] = {}
    for c in countries:
        for part in c.split(","):
            code = part.strip().upper()
            if code and code not in seen:
                seen[code] = None
    return list(seen)


def _load_env(dotenv_path: Path) -> None:
    if dotenv_path.exists():
        dotenv.load_dotenv(dotenv_path)
        logger.info(f"Loaded environment variables from {dotenv_path}")
    else:
        logger.warning(
            f".env file not found at {dotenv_path}, "
            "proceeding without loading environment variables."
        )


@cli.callback()
def _main(
    dotenv_path: Annotated[
        Path,
        typer.Option(
            "--dotenv_path",
            "-d",
            help="Path to the .env configuration file.",
        ),
    ] = Path(".env"),
) -> None:
    """LSEG Knowledge Direct CLI."""
    _load_env(dotenv_path)


def _ensure_output_tree(output_dir: Path) -> tuple[Path, Path, Path]:
    """Create xml/ headlines/ transcripts/ under output_dir if missing."""
    xml_dir = output_dir / "xml"
    headlines_dir = output_dir / "headlines"
    transcripts_dir = output_dir / "transcripts"
    for d in (xml_dir, headlines_dir, transcripts_dir):
        d.mkdir(parents=True, exist_ok=True)
    return xml_dir, headlines_dir, transcripts_dir


def _make_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("ETA"),
        TimeRemainingColumn(),
    )


async def _process_headline(
    *,
    client: StreetEventsServiceClient,
    headline: EventHeadline,
    xml_dir: Path,
    headlines_dir: Path,
    transcripts_dir: Path,
    skip_existing: bool,
) -> str:
    """Fetch + persist one event. Returns one of "saved", "skipped",
    "no_transcript", "error" so the caller can tally outcomes."""
    if headline.Transcript is None:
        return "no_transcript"

    xml_path = xml_dir / f"{headline.EventId}.xml"
    headline_path = headlines_dir / f"{headline.EventId}.json"
    transcript_path = transcripts_dir / f"{headline.EventId}.json"

    if skip_existing and xml_path.exists() and transcript_path.exists():
        return "skipped"

    try:
        xml = await client.aget_document(transcript_id=headline.Transcript.TranscriptId)
    except Exception as e:
        logger.error(
            f"Error fetching document for TranscriptId "
            f"{headline.Transcript.TranscriptId} "
            f"({headline.Transcript.Status}): {e}"
        )
        return "error"

    xml_path.write_text(xml, encoding="utf-8")
    headline_path.write_text(
        json.dumps(headline.model_dump(mode="json"), indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    event = EventTranscriptParser.from_string(xml).parse()
    transcript_path.write_text(
        json.dumps(event.model_dump(mode="json"), indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return "saved"


async def _fetch_transcripts(
    *,
    records_per_page: int,
    from_date: datetime.datetime,
    to_date: datetime.datetime,
    countries: list[str],
    output_dir: Path,
    transcript_status: ContentStatus | None,
    skip_existing: bool,
) -> None:
    """Async worker for the fetch-transcripts command."""
    xml_dir, headlines_dir, transcripts_dir = _ensure_output_tree(output_dir)

    credentials = Credentials()
    logger.success("Credentials loaded successfully.")

    service_token = TokenManagementServiceClient(
        credentials=credentials
    ).create_service_token()
    logger.success(
        f"Service token issued (expires {service_token.expiration.isoformat()})."
    )

    client = StreetEventsServiceClient(
        credentials=credentials,
        token=service_token.token,
        async_mode=True,
    )

    counts = {"saved": 0, "skipped": 0, "no_transcript": 0, "error": 0}

    try:
        # Fetch page 1 outside the bar so we know the total before drawing it.
        page = 1
        response = client.get_event_headlines(
            page_number=page,
            records_per_page=records_per_page,
            from_date=from_date,
            to_date=to_date,
            countries=countries,
            transcript_status=transcript_status,
        )
        pagination = response.extract_pagination_result()
        total = pagination.TotalRecords
        n_pages = (total + records_per_page - 1) // max(records_per_page, 1)
        logger.info(
            f"Total records: {total} "
            f"(records_per_page={records_per_page}, ~{n_pages} page(s))."
        )

        with _make_progress() as progress:
            task = progress.add_task("Fetching events", total=total)

            while True:
                if pagination.RecordsOnPage > 0:
                    for headline in response.extract_event_headlines():
                        progress.update(
                            task,
                            description=f"EventId={headline.EventId}",
                        )
                        result = await _process_headline(
                            client=client,
                            headline=headline,
                            xml_dir=xml_dir,
                            headlines_dir=headlines_dir,
                            transcripts_dir=transcripts_dir,
                            skip_existing=skip_existing,
                        )
                        counts[result] += 1
                        progress.advance(task)

                # Stop once we've consumed every record or the page came back empty.
                seen = pagination.PageNumber * pagination.RecordsPerPage
                if pagination.RecordsOnPage == 0 or seen >= total:
                    break

                page += 1
                response = client.get_event_headlines(
                    page_number=page,
                    records_per_page=records_per_page,
                    from_date=from_date,
                    to_date=to_date,
                    countries=countries,
                    transcript_status=transcript_status,
                )
                pagination = response.extract_pagination_result()

        logger.success(
            f"Done. saved={counts['saved']}, skipped={counts['skipped']}, "
            f"no_transcript={counts['no_transcript']}, errors={counts['error']}."
        )
    finally:
        await client.aclose()


@cli.command("fetch-transcripts")
def fetch_transcripts(
    from_date: Annotated[
        datetime.datetime,
        typer.Option(
            "--from-date",
            formats=["%Y-%m-%d"],
            help="Start date for fetching events (YYYY-MM-DD).",
        ),
    ],
    to_date: Annotated[
        datetime.datetime,
        typer.Option(
            "--to-date",
            formats=["%Y-%m-%d"],
            help="End date for fetching events (YYYY-MM-DD).",
        ),
    ],
    countries: Annotated[
        list[str],
        typer.Option(
            "--countries",
            "-c",
            help=(
                "Country codes. Pass comma-separated (--countries US,UK) "
                "or repeat the flag (--countries US --countries UK)."
            ),
        ),
    ] = ["US"],
    records_per_page: Annotated[
        int,
        typer.Option(
            "--records-per-page",
            help="Number of records to fetch per page.",
        ),
    ] = 1000,
    transcript_status: Annotated[
        TranscriptStatusOption,
        typer.Option(
            "--transcript-status",
            case_sensitive=False,
            help="Filter transcripts by publication status. Pass 'any' for no filter.",
        ),
    ] = TranscriptStatusOption.Final,
    skip_existing: Annotated[
        bool,
        typer.Option(
            "--skip-existing/--no-skip-existing",
            help="Skip events whose XML and transcript JSON already exist.",
        ),
    ] = True,
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            "-o",
            help="Path to the output directory.",
            file_okay=False,
            dir_okay=True,
        ),
    ] = Path("./output"),
) -> None:
    """Fetch event transcripts in a date range and save them to disk.

    For each event headline, downloads the transcript XML, the headline
    metadata, and the parsed transcript JSON into
    ``<output_dir>/{xml,headlines,transcripts}/<EventId>.{xml,json}``.
    """
    asyncio.run(
        _fetch_transcripts(
            records_per_page=records_per_page,
            from_date=from_date,
            to_date=to_date,
            countries=_expand_countries(countries),
            output_dir=output_dir,
            transcript_status=_to_api_status(transcript_status),
            skip_existing=skip_existing,
        )
    )
