"""Tests for the EventTranscript XML parser.

The parser handles a subtle quirk: <Sync>/<br> elements inside <Turn> contribute
their *tail* text as new segments, and segments after a <Sync> inherit that
sync's id/time until the next <Sync>. These tests pin that behavior.
"""

from __future__ import annotations

import datetime

import pytest

from lsegkd.xml import EventTranscriptParser


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<EventTranscript lastEdited="2025-01-15T10:30:00Z" version="1.0">
  <EventID>12345</EventID>
  <Notes>Quarterly earnings call.</Notes>
  <Trans>
    <Speakers>
      <Speaker id="s1" firstName="John" lastName="Doe" companyName="Acme" position="CEO" identified="true" organizer="true"/>
      <Speaker id="s2" firstName="Jane" lastName="Smith" companyName="Acme" position="CFO" identified="true"/>
    </Speakers>
    <Episode>
      <Section type="presentation" name="Opening">
        <Turn speaker="s1">Welcome everyone.<Sync id="t1" time="00:00:01"/>Today we will discuss results.<br/>Let me start.</Turn>
        <Turn speaker="s2"><Sync id="t2" time="00:00:30"/>Thanks John.</Turn>
      </Section>
      <Section type="q-and-a" name="Q&amp;A">
        <Turn speaker="s1">Question time.</Turn>
      </Section>
    </Episode>
  </Trans>
</EventTranscript>
"""


@pytest.fixture
def event():
    return EventTranscriptParser.from_string(SAMPLE_XML).parse()


def test_event_metadata(event):
    assert event.event_id == "12345"
    assert event.version == "1.0"
    assert event.notes == "Quarterly earnings call."
    assert event.last_edited == datetime.datetime(
        2025, 1, 15, 10, 30, tzinfo=datetime.timezone.utc
    )


def test_speakers_indexed_by_id(event):
    speakers = event.transcript.speakers
    assert set(speakers) == {"s1", "s2"}

    s1 = speakers["s1"]
    assert s1.first_name == "John"
    assert s1.last_name == "Doe"
    assert s1.position == "CEO"
    assert s1.identified is True
    assert s1.organizer is True
    assert s1.display_name == "John Doe"

    assert speakers["s2"].organizer is False


def test_episode_structure(event):
    sections = event.transcript.episode.sections
    assert [s.type for s in sections] == ["presentation", "q-and-a"]
    assert sections[0].name == "Opening"
    assert sections[1].name == "Q&A"
    assert len(sections[0].turns) == 2


def test_turn_segments_inherit_last_sync(event):
    """Segments after a <Sync> inherit its id/time until the next <Sync>."""
    turn = event.transcript.episode.sections[0].turns[0]
    assert turn.speaker_id == "s1"

    seg_texts = [(s.sync_id, s.time, s.text) for s in turn.segments]
    assert seg_texts == [
        (None, None, "Welcome everyone."),
        ("t1", "00:00:01", "Today we will discuss results."),
        ("t1", "00:00:01", "Let me start."),
    ]


def test_turn_starting_with_sync_has_no_pre_sync_segment(event):
    """A turn whose body opens with <Sync> should not produce a leading None segment."""
    turn = event.transcript.episode.sections[0].turns[1]
    assert [s.text for s in turn.segments] == ["Thanks John."]
    assert turn.segments[0].sync_id == "t2"


def test_full_text_concatenates_segments(event):
    turn = event.transcript.episode.sections[0].turns[0]
    assert (
        turn.full_text
        == "Welcome everyone. Today we will discuss results. Let me start."
    )


def test_from_path_parses_file(tmp_path):
    xml_file = tmp_path / "event.xml"
    xml_file.write_text(SAMPLE_XML)
    event = EventTranscriptParser.from_path(xml_file).parse()
    assert event.event_id == "12345"


def test_missing_event_id_returns_none():
    minimal = """<EventTranscript>
      <Trans>
        <Speakers/>
        <Episode/>
      </Trans>
    </EventTranscript>"""
    event = EventTranscriptParser.from_string(minimal).parse()
    assert event.event_id is None
    assert event.last_edited is None
    assert event.transcript.speakers == {}
    assert event.transcript.episode.sections == []


def test_event_id_coerced_from_int_when_constructed_directly():
    """Loading from a non-XML source (DB, other tool) may pass an int —
    StrId must coerce to str so downstream code (filenames, dict keys)
    behaves consistently with `EventHeadline.EventId`."""
    from lsegkd.xml import EventTranscript

    event = EventTranscript.model_validate(
        {
            "event_id": 16721770,
            "transcript": {"speakers": {}, "episode": {"sections": []}},
        }
    )
    assert event.event_id == "16721770"
    assert isinstance(event.event_id, str)
