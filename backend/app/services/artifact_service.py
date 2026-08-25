"""Artifact detection and extraction service for isolating interactive widgets, frameworks, and tools."""

import logging
import re
from typing import Any
from pydantic import BaseModel, Field
from app.core.enums import ArtifactType

logger = logging.getLogger(__name__)

ARTIFACT_TAG_REGEX = re.compile(
    r'<artifact\s+type=[\'"](?P<type>html|markdown|svg)[\'"]\s+title=[\'"](?P<title>[^\'"]+)[\'"]\s*>(?P<content>.*?)</artifact>',
    re.DOTALL | re.IGNORECASE,
)

# Fallback regex for models producing standalone HTML documents or SVG blocks in code fences
HTML_BLOCK_REGEX = re.compile(
    r"```(?:html|xml)\s*(?:<!--\s*(?:title:)?\s*(?P<html_title>[^\n]+)\s*-->)?\s*(?P<html_code><!DOCTYPE html>.*?|<html>.*?|<!doctype html>.*?|<svg .*?</svg>)```",
    re.DOTALL | re.IGNORECASE,
)

SVG_BLOCK_REGEX = re.compile(
    r"```(?:svg|xml)\s*(?:<!--\s*(?:title:)?\s*(?P<svg_title>[^\n]+)\s*-->)?\s*(?P<svg_code><svg\b[^>]*>.*?</svg>)```",
    re.DOTALL | re.IGNORECASE,
)


class ExtractedArtifact(BaseModel):
    """Structured representation of an extracted artifact."""

    artifact_type: ArtifactType = Field(..., description="Type of artifact: html, markdown, svg")
    title: str = Field(..., description="Human-readable title for the artifact")
    content: str = Field(..., description="Raw HTML/Markdown/SVG payload ready for sandboxed rendering")
    raw_match: str | None = Field(default=None, description="Original raw match string in text")


class ArtifactParseResult(BaseModel):
    """Result of parsing chat text for embedded artifacts."""

    clean_text: str = Field(..., description="Sanitized conversational text with artifact payload removed")
    artifacts: list[ExtractedArtifact] = Field(default_factory=list, description="List of extracted artifacts")
    has_artifact: bool = Field(default=False, description="Whether one or more artifacts were detected")


class ArtifactService:
    """Service for parsing, formatting, and isolating interactive artifacts from LLM outputs."""

    @staticmethod
    def get_artifact_system_instructions() -> str:
        """Return system prompt guidelines instructing the model on how to package artifacts."""
        return (
            "\n\n🛠️ ARTIFACT GENERATION GUIDELINES:\n"
            "When the user requests interactive tools, calculators, landing page mockups, evaluation matrices, "
            "spreadsheets, or comprehensive frameworks, encapsulate the standalone deliverable inside an "
            "`<artifact>` XML container tag:\n\n"
            '<artifact type="html|markdown|svg" title="Artifact Title">\n'
            "<!-- Full standalone HTML/CSS/JS or Markdown framework here -->\n"
            "</artifact>\n\n"
            "- HTML artifacts must be complete, self-contained documents (`<!DOCTYPE html><html>...</html>`) with embedded CSS and vanilla JS.\n"
            "- Markdown artifacts should contain structured tables, checklists, and rubric matrices.\n"
            "- Provide a brief 1-2 sentence conversational intro before the artifact tag, and keep all code inside the tag."
        )

    @staticmethod
    def wrap_artifact(content: str, artifact_type: ArtifactType | str, title: str) -> str:
        """Helper to wrap content in standard artifact tag delimiters.

        Args:
            content: Artifact HTML, Markdown, or SVG payload.
            artifact_type: Type of artifact.
            title: Title for the artifact.

        Returns:
            str: Tag-wrapped artifact block.
        """
        type_str = artifact_type.value if isinstance(artifact_type, ArtifactType) else str(artifact_type).lower()
        return f'<artifact type="{type_str}" title="{title}">\n{content.strip()}\n</artifact>'

    def parse_artifacts(self, text: str) -> ArtifactParseResult:
        """Parse raw LLM response text, extracting all artifacts and cleaning chat commentary.

        Args:
            text: Raw output string from LLM.

        Returns:
            ArtifactParseResult: Contains cleaned chat text and list of ExtractedArtifact objects.
        """
        if not text:
            return ArtifactParseResult(clean_text="", artifacts=[], has_artifact=False)

        artifacts: list[ExtractedArtifact] = []
        clean_text = text

        # 1. Primary extraction: Standard <artifact type="..." title="...">...</artifact> tags
        for match in ARTIFACT_TAG_REGEX.finditer(text):
            raw_type = match.group("type").lower()
            title = match.group("title").strip()
            content = match.group("content").strip()
            raw_match = match.group(0)

            try:
                art_type = ArtifactType(raw_type)
            except ValueError:
                art_type = ArtifactType.HTML if "html" in raw_type else ArtifactType.MARKDOWN

            artifacts.append(
                ExtractedArtifact(
                    artifact_type=art_type,
                    title=title,
                    content=content,
                    raw_match=raw_match,
                )
            )
            # Remove tag from conversational text
            clean_text = clean_text.replace(raw_match, "")

        # 2. Fallback extraction: Fenced HTML blocks if no XML tags found
        if not artifacts:
            for match in HTML_BLOCK_REGEX.finditer(text):
                html_code = match.group("html_code").strip()
                title_tag = match.group("html_title")
                title = title_tag.strip() if title_tag else "Interactive Component"
                raw_match = match.group(0)

                artifacts.append(
                    ExtractedArtifact(
                        artifact_type=ArtifactType.HTML,
                        title=title,
                        content=html_code,
                        raw_match=raw_match,
                    )
                )
                clean_text = clean_text.replace(raw_match, "")

        # 3. Fallback extraction: Fenced SVG blocks
        if not artifacts:
            for match in SVG_BLOCK_REGEX.finditer(text):
                svg_code = match.group("svg_code").strip()
                title_tag = match.group("svg_title")
                title = title_tag.strip() if title_tag else "Diagram"
                raw_match = match.group(0)

                artifacts.append(
                    ExtractedArtifact(
                        artifact_type=ArtifactType.SVG,
                        title=title,
                        content=svg_code,
                        raw_match=raw_match,
                    )
                )
                clean_text = clean_text.replace(raw_match, "")

        # Clean up any leftover blank lines or whitespace
        clean_text = re.sub(r"\n{3,}", "\n\n", clean_text).strip()

        return ArtifactParseResult(
            clean_text=clean_text,
            artifacts=artifacts,
            has_artifact=len(artifacts) > 0,
        )


class ArtifactStreamParser:
    """Stateful stream parser for isolating artifact tokens from chat text during real-time streaming."""

    def __init__(self) -> None:
        """Initialize the stream parser state."""
        self.buffer = ""
        self.in_artifact = False
        self.current_type: ArtifactType | None = None
        self.current_title: str | None = None
        self.artifact_content_buffer = ""
        self.extracted_artifacts: list[ExtractedArtifact] = []

    def feed_token(self, token: str) -> dict[str, Any]:
        """Process an incoming streaming token.

        Args:
            token: Incoming text chunk from LLM stream.

        Returns:
            dict[str, Any]: Event dictionary containing:
                - 'type': 'text_delta' | 'artifact_delta' | 'artifact_completed' | 'none'
                - 'content': str
                - 'artifact': Optional[ExtractedArtifact]
        """
        self.buffer += token

        # Check if we are currently outside an artifact
        if not self.in_artifact:
            if "<artifact" in self.buffer:
                # Potential start of artifact tag
                start_idx = self.buffer.find("<artifact")
                tag_end_idx = self.buffer.find(">", start_idx)

                if tag_end_idx != -1:
                    # Full start tag received
                    tag_str = self.buffer[start_idx : tag_end_idx + 1]
                    text_before = self.buffer[:start_idx]
                    self.buffer = self.buffer[tag_end_idx + 1 :]

                    # Extract type and title attributes
                    type_match = re.search(r'type=[\'"]([^\'"]+)[\'"]', tag_str, re.I)
                    title_match = re.search(r'title=[\'"]([^\'"]+)[\'"]', tag_str, re.I)

                    raw_type = type_match.group(1).lower() if type_match else "html"
                    try:
                        self.current_type = ArtifactType(raw_type)
                    except ValueError:
                        self.current_type = ArtifactType.HTML

                    self.current_title = title_match.group(1).strip() if title_match else "Interactive Tool"
                    self.in_artifact = True
                    self.artifact_content_buffer = ""

                    return {
                        "type": "text_delta",
                        "content": text_before,
                        "artifact_start": True,
                        "artifact_type": self.current_type.value,
                        "artifact_title": self.current_title,
                    }
                else:
                    # Incomplete tag, keep buffering without emitting yet
                    return {"type": "none", "content": ""}
            else:
                # Regular text token, emit buffer
                to_emit = self.buffer
                self.buffer = ""
                return {"type": "text_delta", "content": to_emit}

        else:
            # We are inside an artifact
            if "</artifact>" in self.buffer:
                end_idx = self.buffer.find("</artifact>")
                artifact_chunk = self.buffer[:end_idx]
                self.artifact_content_buffer += artifact_chunk
                self.buffer = self.buffer[end_idx + len("</artifact>") :]

                artifact = ExtractedArtifact(
                    artifact_type=self.current_type or ArtifactType.HTML,
                    title=self.current_title or "Artifact",
                    content=self.artifact_content_buffer.strip(),
                )
                self.extracted_artifacts.append(artifact)
                self.in_artifact = False
                self.current_type = None
                self.current_title = None

                return {
                    "type": "artifact_completed",
                    "content": artifact_chunk,
                    "artifact": artifact,
                }
            else:
                # Inside artifact content, buffer and emit artifact delta
                delta = self.buffer
                self.artifact_content_buffer += delta
                self.buffer = ""
                return {
                    "type": "artifact_delta",
                    "content": delta,
                }

    def finalize(self) -> list[ExtractedArtifact]:
        """Finalize the parser and return all captured artifacts."""
        if self.in_artifact and self.artifact_content_buffer:
            artifact = ExtractedArtifact(
                artifact_type=self.current_type or ArtifactType.HTML,
                title=self.current_title or "Artifact",
                content=self.artifact_content_buffer.strip(),
            )
            self.extracted_artifacts.append(artifact)
            self.in_artifact = False
        return self.extracted_artifacts
