"""Unit tests for Artifact Extraction Service and Stream Parser."""

import pytest
from app.core.enums import ArtifactType
from app.services.artifact_service import (
    ArtifactParseResult,
    ArtifactService,
    ArtifactStreamParser,
    ExtractedArtifact,
)


def test_parse_artifacts_empty_text() -> None:
    """Test parse_artifacts handles empty or None inputs cleanly."""
    service = ArtifactService()
    res = service.parse_artifacts("")
    assert res.has_artifact is False
    assert res.artifacts == []
    assert res.clean_text == ""


def test_parse_artifacts_no_artifact() -> None:
    """Test standard conversational response without artifacts."""
    service = ArtifactService()
    text = "Elena Verna recommends focusing on product retention before scaling spend."
    res = service.parse_artifacts(text)
    assert res.has_artifact is False
    assert res.artifacts == []
    assert res.clean_text == text


def test_parse_artifacts_html_xml_tag() -> None:
    """Test extracting HTML artifact enclosed in <artifact> XML container."""
    service = ArtifactService()
    html_payload = (
        "<!DOCTYPE html>\n<html><head><title>Calculator</title></head>"
        "<body><h1>CAC:LTV Calculator</h1></body></html>"
    )
    raw_text = (
        "Here is the interactive CAC:LTV calculator you requested:\n\n"
        f'<artifact type="html" title="CAC:LTV Payback Calculator">\n{html_payload}\n</artifact>\n\n'
        "Let me know if you need any adjustments to the default payback assumptions."
    )

    res = service.parse_artifacts(raw_text)
    assert res.has_artifact is True
    assert len(res.artifacts) == 1

    art = res.artifacts[0]
    assert art.artifact_type == ArtifactType.HTML
    assert art.title == "CAC:LTV Payback Calculator"
    assert "<!DOCTYPE html>" in art.content
    assert "CAC:LTV Calculator" in art.content

    # Verify commentary text was cleaned
    assert "Here is the interactive CAC:LTV calculator you requested:" in res.clean_text
    assert "Let me know if you need any adjustments" in res.clean_text
    assert "<artifact" not in res.clean_text
    assert "<!DOCTYPE html>" not in res.clean_text


def test_parse_artifacts_markdown_framework() -> None:
    """Test extracting Markdown artifact framework."""
    service = ArtifactService()
    md_payload = "| Task | Category | Impact |\n|---|---|---|\n| Pricing v2 | Leverage | High |"
    raw_text = (
        "I have structured the LNO framework evaluation matrix below:\n\n"
        f'<artifact type="markdown" title="LNO Task Matrix">\n{md_payload}\n</artifact>'
    )

    res = service.parse_artifacts(raw_text)
    assert res.has_artifact is True
    assert len(res.artifacts) == 1
    art = res.artifacts[0]
    assert art.artifact_type == ArtifactType.MARKDOWN
    assert art.title == "LNO Task Matrix"
    assert "| Pricing v2 |" in art.content
    assert "<artifact" not in res.clean_text


def test_parse_artifacts_svg_diagram() -> None:
    """Test extracting SVG vector diagram."""
    service = ArtifactService()
    svg_payload = '<svg width="200" height="200"><circle cx="100" cy="100" r="80" fill="green" /></svg>'
    raw_text = (
        "Here is the growth loop diagram:\n\n"
        f'<artifact type="svg" title="Growth Loop Diagram">\n{svg_payload}\n</artifact>'
    )

    res = service.parse_artifacts(raw_text)
    assert res.has_artifact is True
    assert len(res.artifacts) == 1
    art = res.artifacts[0]
    assert art.artifact_type == ArtifactType.SVG
    assert art.title == "Growth Loop Diagram"
    assert "<circle" in art.content


def test_parse_artifacts_fallback_code_fences() -> None:
    """Test fallback detection for raw HTML fenced blocks."""
    service = ArtifactService()
    raw_text = (
        "Here is the widget:\n\n"
        "```html\n"
        "<!-- title: User Retention Widget -->\n"
        "<!DOCTYPE html>\n"
        "<html><body>Retention Widget</body></html>\n"
        "```\n\n"
        "You can embed this in your dashboard."
    )

    res = service.parse_artifacts(raw_text)
    assert res.has_artifact is True
    assert len(res.artifacts) == 1
    art = res.artifacts[0]
    assert art.artifact_type == ArtifactType.HTML
    assert art.title == "User Retention Widget"
    assert "<!DOCTYPE html>" in art.content
    assert "```html" not in res.clean_text


def test_wrap_artifact_helper() -> None:
    """Test wrap_artifact builds valid XML containers."""
    wrapped = ArtifactService.wrap_artifact(
        content="<div>Widget</div>",
        artifact_type=ArtifactType.HTML,
        title="My Widget",
    )
    assert '<artifact type="html" title="My Widget">' in wrapped
    assert "<div>Widget</div>" in wrapped
    assert "</artifact>" in wrapped


def test_artifact_stream_parser_flow() -> None:
    """Test ArtifactStreamParser incremental processing of streamed tokens."""
    stream_parser = ArtifactStreamParser()

    token_sequence = [
        "Here is the ",
        "tool:\n\n",
        '<artifact type="html" title="Pricing Slider">\n',
        "<button>",
        "Click Me",
        "</button>\n",
        "</artifact>",
        "\n\nLet me know what you think!",
    ]

    events = []
    for tok in token_sequence:
        event = stream_parser.feed_token(tok)
        events.append(event)

    completed_artifacts = stream_parser.finalize()
    assert len(completed_artifacts) == 1
    art = completed_artifacts[0]
    assert art.title == "Pricing Slider"
    assert art.artifact_type == ArtifactType.HTML
    assert "<button>Click Me</button>" in art.content

    # Check event types emitted
    event_types = [e["type"] for e in events if e["type"] != "none"]
    assert "text_delta" in event_types
    assert "artifact_delta" in event_types
    assert "artifact_completed" in event_types
