"""Tests for TranscriptChunker and chunking pipeline."""

import json
from pathlib import Path
import pytest
from app.core.config import Settings
from app.schemas.chunk import TranscriptChunk, TranscriptMetadata
from app.scripts.chunker import find_default_transcripts_dir
from app.services.chunker import TranscriptChunker


def test_chunker_initialization_validation() -> None:
    """Test parameter validation during chunker initialization."""
    # min_tokens must be positive
    with pytest.raises(ValueError, match="min_tokens"):
        TranscriptChunker(min_tokens=-1, max_tokens=500)
    with pytest.raises(ValueError, match="min_tokens"):
        TranscriptChunker(min_tokens=0, max_tokens=500)

    # max_tokens must be positive
    with pytest.raises(ValueError, match="max_tokens"):
        TranscriptChunker(min_tokens=100, max_tokens=0)

    # overlap_tokens must be non-negative
    with pytest.raises(ValueError, match="overlap_tokens"):
        TranscriptChunker(min_tokens=100, max_tokens=200, overlap_tokens=-1)

    # min_tokens must be < max_tokens
    with pytest.raises(ValueError, match="min_tokens"):
        TranscriptChunker(min_tokens=700, max_tokens=500)

    # overlap_tokens must be < min_tokens
    with pytest.raises(ValueError, match="overlap_tokens"):
        TranscriptChunker(min_tokens=500, max_tokens=700, overlap_tokens=600)


def test_chunker_token_estimation() -> None:
    """Test token estimation heuristic."""
    assert TranscriptChunker.estimate_tokens("") == 0
    assert TranscriptChunker.estimate_tokens("   ") == 0

    text = "Product Led Growth is a company wide distribution strategy."
    tokens = TranscriptChunker.estimate_tokens(text)
    assert tokens > 0
    assert isinstance(tokens, int)


def test_chunk_structured_transcript() -> None:
    """Test chunking structured dialogue turns into valid TranscriptChunks."""
    chunker = TranscriptChunker(min_tokens=50, max_tokens=100, overlap_tokens=20)

    metadata = TranscriptMetadata(
        episode_id="ep_test",
        episode_title="Testing Episode Title",
        guest_name="Test Guest",
        guest_role="Growth Lead",
        topic="Growth Strategy",
        url="https://example.com/podcast",
    )

    dialogue = [
        {
            "timestamp": "00:00:00",
            "speaker": "Lenny",
            "text": "Welcome to the show. Let's talk about growth loops and retention.",
        },
        {
            "timestamp": "00:01:00",
            "speaker": "Test Guest",
            "text": "Growth loops are compounding closed systems where outputs become inputs. " * 5,
        },
        {
            "timestamp": "00:03:00",
            "speaker": "Lenny",
            "text": "How do you measure retention and activation across cohorts?",
        },
        {
            "timestamp": "00:04:00",
            "speaker": "Test Guest",
            "text": "You must define your core value moment and measure time to value relentlessly. " * 6,
        },
    ]

    chunks = chunker.chunk_structured_transcript(metadata, dialogue)
    assert len(chunks) >= 1

    for chunk in chunks:
        assert isinstance(chunk, TranscriptChunk)
        assert chunk.episode_id == "ep_test"
        assert chunk.guest_name == "Test Guest"
        assert chunk.episode_title == "Testing Episode Title"
        assert chunk.topic == "Growth Strategy"
        assert chunk.url == "https://example.com/podcast"
        assert chunk.token_count > 0
        assert chunk.total_chunks == len(chunks)
        assert "Test Guest" in chunk.text
        assert "Testing Episode Title" in chunk.text
        assert chunk.citation_label.startswith("Test Guest in 'Testing Episode Title'")


def test_chunker_oversized_sentence_budget() -> None:
    """Test chunker correctly breaks massive single-sentence turns without exceeding max_tokens."""
    chunker = TranscriptChunker(min_tokens=50, max_tokens=120, overlap_tokens=20)
    metadata = TranscriptMetadata(
        episode_id="ep_long",
        episode_title="Long Monologue",
        guest_name="Long Speaker",
        guest_role="Monologue Specialist",
        topic="Strategy",
        url="https://example.com",
    )
    long_sentence = "This is a single massive unbroken run-on sentence discussing growth loops and retention systems repeatedly " * 30
    dialogue = [{"timestamp": "00:00:00", "speaker": "Long Speaker", "text": long_sentence}]

    chunks = chunker.chunk_structured_transcript(metadata, dialogue)
    assert len(chunks) > 1
    for c in chunks:
        assert c.token_count <= 160  # Header + budget comfortably bounded


def test_chunker_empty_input() -> None:
    """Test chunker handles empty dialogue gracefully."""
    chunker = TranscriptChunker(min_tokens=100, max_tokens=200, overlap_tokens=20)
    metadata = TranscriptMetadata(
        episode_id="ep_empty",
        episode_title="Empty",
        guest_name="Guest",
        guest_role="Role",
        topic="Topic",
        url="",
    )
    chunks = chunker.chunk_structured_transcript(metadata, [])
    assert chunks == []


def test_chunk_actual_transcript_corpus(tmp_path: Path) -> None:
    """Test chunking all files in data/transcripts."""
    transcripts_dir = find_default_transcripts_dir()
    assert transcripts_dir.exists(), f"Corpus dir not found: {transcripts_dir}"

    files = list(transcripts_dir.glob("*.json"))
    assert len(files) >= 10, f"Expected at least 10 episodes, found {len(files)}"

    chunker = TranscriptChunker(min_tokens=500, max_tokens=700, overlap_tokens=100)
    all_chunks = chunker.chunk_directory(transcripts_dir)

    assert len(all_chunks) >= len(files)

    # Check key guests are represented
    guest_names = {c.guest_name for c in all_chunks}
    required_guests = [
        "Elena Verna",
        "Brian Balfour",
        "Shreyas Doshi",
        "Julie Zhuo",
        "Madhavan Ramanujam",
        "Sean Ellis",
        "Lenny Rachitsky",
    ]
    for req in required_guests:
        assert req in guest_names, f"Missing required guest: {req}"


def test_chunk_file_json_and_plain_text(tmp_path: Path) -> None:
    """Test chunk_file handles both JSON and raw text files."""
    chunker = TranscriptChunker(min_tokens=50, max_tokens=100, overlap_tokens=10)

    # JSON transcript
    json_path = tmp_path / "sample_ep.json"
    json_path.write_text(
        json.dumps({
            "episode_id": "sample_1",
            "episode_title": "Sample Episode",
            "guest_name": "Sample Guest",
            "guest_role": "Advisor",
            "topic": "Strategy",
            "url": "https://example.com",
            "transcript": [
                {"timestamp": "00:00:10", "speaker": "Lenny", "text": "Hello world!"},
                {"timestamp": "00:00:20", "speaker": "Sample Guest", "text": "This is a detailed answer on growth strategy. " * 8},
            ],
        }),
        encoding="utf-8",
    )

    json_chunks = chunker.chunk_file(json_path)
    assert len(json_chunks) >= 1
    assert json_chunks[0].guest_name == "Sample Guest"

    # Plain text file
    txt_path = tmp_path / "sample_notes.txt"
    txt_path.write_text("This is an unformatted transcript note discussing PLG and retention loops in depth. " * 10, encoding="utf-8")

    txt_chunks = chunker.chunk_file(txt_path)
    assert len(txt_chunks) >= 1
    assert txt_chunks[0].episode_id == "sample_notes"


def test_chunk_directory_recursive_discovery(tmp_path: Path) -> None:
    """Test that chunk_directory scans subdirectories recursively."""
    chunker = TranscriptChunker(min_tokens=50, max_tokens=100, overlap_tokens=10)
    nested_dir = tmp_path / "nested" / "subfolder"
    nested_dir.mkdir(parents=True)
    nested_file = nested_dir / "nested_ep.json"
    nested_file.write_text(
        json.dumps({
            "episode_id": "nested_1",
            "episode_title": "Nested Episode",
            "guest_name": "Nested Guest",
            "guest_role": "Advisor",
            "topic": "Strategy",
            "url": "https://example.com",
            "transcript": [{"speaker": "Nested Guest", "text": "Testing recursive discovery.", "timestamp": "00:00:00"}],
        }),
        encoding="utf-8",
    )

    chunks = chunker.chunk_directory(tmp_path, strict=True)
    assert len(chunks) >= 1
    assert chunks[0].guest_name == "Nested Guest"


def test_chunk_directory_strict_mode_raises(tmp_path: Path) -> None:
    """Test that chunk_directory raises RuntimeError when a malformed file is encountered in strict mode."""
    chunker = TranscriptChunker(min_tokens=50, max_tokens=100, overlap_tokens=10)
    bad_file = tmp_path / "broken_transcript.json"
    bad_file.write_text("{ broken json content", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Transcript chunking failed"):
        chunker.chunk_directory(tmp_path, strict=True)


def test_find_default_transcripts_dir_respects_settings(tmp_path: Path) -> None:
    """Test find_default_transcripts_dir respects Settings.TRANSCRIPTS_DIR."""
    custom_dir = tmp_path / "custom_transcripts"
    custom_dir.mkdir(parents=True)
    custom_settings = Settings(TRANSCRIPTS_DIR=str(custom_dir))

    resolved = find_default_transcripts_dir(custom_settings)
    assert resolved == custom_dir.resolve()
