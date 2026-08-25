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


def test_parse_artifacts_ant_artifact_and_reversed_attrs() -> None:
    """Test extracting artifact with reversed attributes and antArtifact tags."""
    service = ArtifactService()
    raw_text = (
        "An authoritative executive growth memo on evaluating career pivots.\n\n"
        '<antArtifact identifier="ship-30-career" title="The Career Expiration Date" type="text/markdown">\n'
        "# The Career Expiration Date\n\nMost operators leave too early or too late.\n"
        "</antArtifact>\n\nLet me know if you want to dive deeper."
    )

    res = service.parse_artifacts(raw_text)
    assert res.has_artifact is True
    assert len(res.artifacts) == 1
    art = res.artifacts[0]
    assert art.artifact_type == ArtifactType.MARKDOWN
    assert art.title == "The Career Expiration Date"
    assert "# The Career Expiration Date" in art.content
    assert "An authoritative executive growth memo" in res.clean_text
    assert "<antArtifact" not in res.clean_text
    assert "# The Career Expiration Date" not in res.clean_text


def test_artifact_stream_parser_ant_artifact_flow() -> None:
    """Test ArtifactStreamParser with antArtifact tag flow."""
    stream_parser = ArtifactStreamParser()

    token_sequence = [
        "Executive overview.\n\n",
        '<antArtifact title="Ada Chen on Quitting" type="text/markdown">\n',
        "# The Curiosity Loop\n",
        "Framework details here.\n",
        "</antArtifact>",
        "\n\nClosing note.",
    ]

    events = []
    for tok in token_sequence:
        event = stream_parser.feed_token(tok)
        events.append(event)

    completed_artifacts = stream_parser.finalize()
    assert len(completed_artifacts) == 1
    art = completed_artifacts[0]
    assert art.title == "Ada Chen on Quitting"
    assert art.artifact_type == ArtifactType.MARKDOWN
    assert "# The Curiosity Loop" in art.content


def test_artifact_stream_parser_split_tokens() -> None:
    """Test ArtifactStreamParser when opening and closing tags are fragmented across tokens."""
    stream_parser = ArtifactStreamParser()

    token_sequence = [
        "Executive ",
        "summary:\n\n",
        "<",
        "arti",
        'fact type="markdown" title="Split Tag Test">',
        "\n# Content Line 1\n",
        "Content Line 2\n",
        "</",
        "arti",
        "fact>",
        "\n\nFooter note.",
    ]

    events = []
    for tok in token_sequence:
        event = stream_parser.feed_token(tok)
        events.append(event)

    completed_artifacts = stream_parser.finalize()
    assert len(completed_artifacts) == 1
    art = completed_artifacts[0]
    assert art.title == "Split Tag Test"
    assert art.artifact_type == ArtifactType.MARKDOWN
    assert "# Content Line 1" in art.content
    assert "Content Line 2" in art.content

    # Check that tag fragments were not emitted as text_delta
    text_deltas = [e["content"] for e in events if e["type"] == "text_delta"]
    full_text_delta = "".join(text_deltas)
    assert "<arti" not in full_text_delta
    assert "</arti" not in full_text_delta
    assert "Executive summary:" in full_text_delta
    assert "Footer note." in full_text_delta
