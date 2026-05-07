from __future__ import annotations

import xml.etree.ElementTree as ET
import datetime
from pathlib import Path
from typing import List, Dict, Optional

from pydantic import BaseModel, Field


class UtteranceSegment(BaseModel):
    """
    A minimal time-aligned utterance chunk.
    """

    sync_id: Optional[str] = None
    time: Optional[str] = None  # "HH:MM:SS"
    text: str


class Turn(BaseModel):
    """
    One speaker turn consisting of multiple utterance segments.
    """

    speaker_id: str = Field(..., description="Speaker reference id")
    segments: List[UtteranceSegment]

    @property
    def full_text(self) -> str:
        """Concatenate all segments into one text."""
        return " ".join(seg.text for seg in self.segments).strip()


class Section(BaseModel):
    """
    Logical section of the event (e.g. presentation, q-and-a).
    """

    type: Optional[str] = None
    name: Optional[str] = None
    turns: List[Turn]


class Episode(BaseModel):
    """
    One episode consisting of multiple sections.
    """

    sections: List[Section]


class Speaker(BaseModel):
    """
    Speaker master entity.
    """

    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    position: Optional[str] = None
    identified: bool = False
    organizer: bool = False

    @property
    def display_name(self) -> str:
        return " ".join(part for part in [self.first_name, self.last_name] if part)


class Transcript(BaseModel):
    """
    Transcript body containing speakers and spoken content.
    """

    speakers: Dict[str, Speaker]
    episode: Episode


class EventTranscript(BaseModel):
    """
    Root model for an event transcript.
    """

    event_id: Optional[str] = None
    last_edited: Optional[datetime.datetime] = None
    version: Optional[str] = None
    notes: Optional[str] = None
    transcript: Transcript


class EventTranscriptParser:
    """
    Parse EventTranscript XML into Pydantic models.
    """

    def __init__(self, root: ET.Element):
        self.root = root

    @classmethod
    def from_path(cls, xml_path: str | Path) -> "EventTranscriptParser":
        """
        Create an EventTranscriptParser from an XML file path.

        Args:
            xml_path (str | Path): The path to the XML file.

        Returns:
            EventTranscriptParser: An instance of the parser.
        """
        tree = ET.parse(xml_path)
        return cls(tree.getroot())

    @classmethod
    def from_string(cls, xml_string: str) -> "EventTranscriptParser":
        """
        Create an EventTranscriptParser from an XML string.

        Args:
            xml_string (str): The XML string to parse.

        Returns:
            EventTranscriptParser: An instance of the parser.
        """
        root = ET.fromstring(xml_string)
        return cls(root)

    def parse(self) -> EventTranscript:
        """Parse the XML and return the EventTranscript model."""
        return EventTranscript(
            event_id=self._parse_event_id(),
            last_edited=self._parse_last_edited(),
            version=self.root.attrib.get("version"),
            notes=self._parse_notes(),
            transcript=self._parse_transcript(),
        )

    def _parse_event_id(self) -> Optional[str]:
        """Parse the EventID from the root element."""
        elem = self.root.find("EventID")

        if elem is None:
            return None

        if elem.text is None:
            return None

        return elem.text.strip()

    def _parse_last_edited(self) -> Optional[datetime.datetime]:
        """Parse the lastEdited attribute from the root element."""
        value = self.root.attrib.get("lastEdited")
        if not value:
            return None
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _parse_notes(self) -> Optional[str]:
        """Parse the Notes element from the root element."""
        elem = self.root.find("Notes")
        return elem.text if elem is not None else None

    def _parse_transcript(self) -> Transcript:
        """Parse the Trans element into a Transcript model."""
        trans_elem = self.root.find("Trans")
        assert trans_elem is not None, "<Trans> element is required"

        speakers_elem = trans_elem.find("Speakers")
        assert speakers_elem is not None, "<Speakers> element is required"

        episode_elem = trans_elem.find("Episode")
        assert episode_elem is not None, "<Episode> element is required"

        return Transcript(
            speakers=self._parse_speakers(speakers_elem),
            episode=self._parse_episode(episode_elem),
        )

    def _parse_speakers(self, speakers_elem: ET.Element) -> Dict[str, Speaker]:
        """
        Parse the Speakers element into a dictionary of Speaker models.

        Args:
            speakers_elem (ET.Element): The Speakers XML element.
        Returns:
            Dict[str, Speaker]: A dictionary mapping speaker IDs to Speaker models.
        """
        speakers: Dict[str, Speaker] = {}

        for sp in speakers_elem.findall("Speaker"):
            speaker = Speaker(
                id=sp.attrib["id"],
                first_name=sp.attrib.get("firstName"),
                last_name=sp.attrib.get("lastName"),
                company_name=sp.attrib.get("companyName"),
                position=sp.attrib.get("position"),
                identified=sp.attrib.get("identified") == "true",
                organizer=sp.attrib.get("organizer") == "true",
            )
            speakers[speaker.id] = speaker

        return speakers

    def _parse_episode(self, episode_elem: ET.Element) -> Episode:
        """
        Parse the Episode element into an Episode model.

        Args:
            episode_elem (ET.Element): The Episode XML element.

        Returns:
            Episode: The parsed Episode model.
        """
        sections = [self._parse_section(sec) for sec in episode_elem.findall("Section")]
        return Episode(sections=sections)

    def _parse_section(self, section_elem: ET.Element) -> Section:
        """
        Parse the Section element into a Section model.

        Args:
            section_elem (ET.Element): The Section XML element.

        Returns:
            Section: The parsed Section model.
        """
        return Section(
            type=section_elem.attrib.get("type"),
            name=section_elem.attrib.get("name"),
            turns=[self._parse_turn(turn) for turn in section_elem.findall("Turn")],
        )

    def _parse_turn(self, turn_elem: ET.Element) -> Turn:
        """
        Parse the Turn element into a Turn model.

        Args:
            turn_elem (ET.Element): The Turn XML element.

        Returns:
            Turn: The parsed Turn model.
        """
        return Turn(
            speaker_id=turn_elem.attrib["speaker"],
            segments=self._parse_turn_segments(turn_elem),
        )

    def _parse_turn_segments(self, turn_elem: ET.Element) -> List[UtteranceSegment]:
        """
        Parse the segments within a Turn element.

        Args:
            turn_elem (ET.Element): The Turn XML element.

        Returns:
            List[UtteranceSegment]: A list of UtteranceSegment models.
        """
        segments: List[UtteranceSegment] = []

        current_sync_id: Optional[str] = None
        current_time: Optional[str] = None

        if turn_elem.text and turn_elem.text.strip():
            segments.append(
                UtteranceSegment(
                    sync_id=None,
                    time=None,
                    text=turn_elem.text.strip(),
                )
            )

        for elem in turn_elem:
            if elem.tag == "Sync":
                current_sync_id = elem.attrib.get("id")
                current_time = elem.attrib.get("time")

                if elem.tail and elem.tail.strip():
                    segments.append(
                        UtteranceSegment(
                            sync_id=current_sync_id,
                            time=current_time,
                            text=elem.tail.strip(),
                        )
                    )

            elif elem.tag == "br":
                if elem.tail and elem.tail.strip():
                    segments.append(
                        UtteranceSegment(
                            sync_id=current_sync_id,
                            time=current_time,
                            text=elem.tail.strip(),
                        )
                    )

        return segments
