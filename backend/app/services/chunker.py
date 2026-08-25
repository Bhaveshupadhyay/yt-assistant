"""Semantic chunking service for podcast and newsletter transcripts.

Splits transcripts into 500-700 token chunks with 100-token overlap,
preserving speaker dialogue turns, timestamp boundaries, and attaching rich metadata.
"""

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any
from app.schemas.chunk import TranscriptChunk, TranscriptMetadata

logger = logging.getLogger(__name__)


class TranscriptChunker:
    """Semantic sliding-window chunker optimized for podcast dialogue transcripts."""

    def __init__(
        self,
        min_tokens: int = 500,
        max_tokens: int = 700,
        overlap_tokens: int = 100,
    ) -> None:
        """Initialize the chunker with token bounds.

        Args:
            min_tokens: Target minimum token count per chunk.
            max_tokens: Hard ceiling target for chunk size before forcing a split.
            overlap_tokens: Target token count preserved across adjacent chunk boundaries.
        """
        if min_tokens >= max_tokens:
            raise ValueError(f"min_tokens ({min_tokens}) must be less than max_tokens ({max_tokens})")
        if overlap_tokens >= min_tokens:
            raise ValueError(f"overlap_tokens ({overlap_tokens}) must be less than min_tokens ({min_tokens})")

        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for a text block using standard whitespace and punctuation heuristic.

        Heuristic: 1 token ~= 0.75 words (or ~4 characters in English).
        """
        if not text or not text.strip():
            return 0
        words = text.strip().split()
        return max(1, int(len(words) * 1.33))

    def _split_long_text_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences while preserving sentence endings."""
        sentence_endings = re.compile(r"(?<=[.!?]) +")
        sentences = sentence_endings.split(text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _split_oversized_text(self, text: str, max_chunk_tokens: int) -> list[str]:
        """Split text that exceeds max_chunk_tokens first by sentences, then by word groups."""
        sentences = self._split_long_text_into_sentences(text)
        units: list[str] = []
        for s in sentences:
            if self.estimate_tokens(s) <= max_chunk_tokens:
                units.append(s)
            else:
                # Break sentence by word chunks
                words = s.split()
                # max words roughly max_chunk_tokens / 1.33
                max_words = max(1, int(max_chunk_tokens / 1.33))
                for i in range(0, len(words), max_words):
                    units.append(" ".join(words[i : i + max_words]))
        return units

    def chunk_structured_transcript(
        self,
        metadata: TranscriptMetadata,
        dialogue_turns: list[dict[str, Any]],
    ) -> list[TranscriptChunk]:
        """Chunk a list of structured dialogue turns into semantic chunks.

        Each dialogue turn is expected to have 'speaker', 'text', and optionally 'timestamp'.
        """
        if not dialogue_turns:
            return []

        # Estimated header token budget to ensure total chunk size is within max_tokens
        sample_header = (
            f"[{metadata.guest_name} | {metadata.episode_title} | "
            f"Topic: {metadata.topic} | Time: 00:00:00 - 00:00:00]"
        )
        header_tokens_budget = self.estimate_tokens(sample_header) + 4
        effective_max = max(self.min_tokens + 20, self.max_tokens - header_tokens_budget)

        # 1. Expand turns into atomic units
        units: list[dict[str, Any]] = []
        for turn in dialogue_turns:
            speaker = turn.get("speaker", "Speaker")
            text = turn.get("text", "").strip()
            timestamp = turn.get("timestamp", "00:00:00")
            if not text:
                continue

            speaker_prefix = f"{speaker}: "
            prefix_tokens = self.estimate_tokens(speaker_prefix)
            available_turn_tokens = effective_max - prefix_tokens

            turn_tokens = self.estimate_tokens(f"{speaker_prefix}{text}")
            if turn_tokens > effective_max:
                # Subdivide oversized text by sentences / words
                sub_texts = self._split_oversized_text(text, max_chunk_tokens=available_turn_tokens)
                for st in sub_texts:
                    formatted_line = f"{speaker_prefix}{st}"
                    units.append({
                        "speaker": speaker,
                        "text": formatted_line,
                        "raw_text": st,
                        "timestamp": timestamp,
                        "tokens": self.estimate_tokens(formatted_line),
                    })
            else:
                units.append({
                    "speaker": speaker,
                    "text": f"{speaker_prefix}{text}",
                    "raw_text": text,
                    "timestamp": timestamp,
                    "tokens": turn_tokens,
                })

        if not units:
            return []

        raw_chunks: list[dict[str, Any]] = []
        curr_units: list[dict[str, Any]] = []
        curr_tokens = 0

        for unit in units:
            unit_tokens = unit["tokens"]
            # If adding this unit exceeds effective_max and we already meet min_tokens, seal chunk
            if curr_tokens + unit_tokens > effective_max and curr_tokens >= self.min_tokens:
                raw_chunks.append({
                    "units": list(curr_units),
                    "start_timestamp": curr_units[0]["timestamp"],
                    "end_timestamp": curr_units[-1]["timestamp"],
                })

                # Calculate overlap units for the next chunk
                overlap_accum: list[dict[str, Any]] = []
                overlap_tokens_count = 0
                for prev_unit in reversed(curr_units):
                    if overlap_tokens_count + prev_unit["tokens"] <= self.overlap_tokens:
                        overlap_accum.insert(0, prev_unit)
                        overlap_tokens_count += prev_unit["tokens"]
                    else:
                        break

                curr_units = list(overlap_accum)
                curr_tokens = overlap_tokens_count

            curr_units.append(unit)
            curr_tokens += unit_tokens

        # Append trailing units
        if curr_units:
            raw_chunks.append({
                "units": list(curr_units),
                "start_timestamp": curr_units[0]["timestamp"],
                "end_timestamp": curr_units[-1]["timestamp"],
            })

        # Format final TranscriptChunk objects
        total_chunks = len(raw_chunks)
        chunks: list[TranscriptChunk] = []

        for idx, rc in enumerate(raw_chunks):
            start_ts = rc["start_timestamp"]
            end_ts = rc["end_timestamp"]
            time_label = f"{start_ts} - {end_ts}" if start_ts != end_ts else start_ts

            # Combine dialogue texts
            body_text = "\n\n".join(u["text"] for u in rc["units"])

            # Add rich header context to ground RAG retrieval
            header = (
                f"[{metadata.guest_name} | {metadata.episode_title} | "
                f"Topic: {metadata.topic} | Time: {time_label}]"
            )
            formatted_text = f"{header}\n\n{body_text}"
            token_count = self.estimate_tokens(formatted_text)

            # Deterministic unique RFC 4122 UUID v5 for Qdrant compatibility
            hash_input = f"{metadata.episode_id}_{idx}_{start_ts}"
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, hash_input))

            chunks.append(
                TranscriptChunk(
                    chunk_id=chunk_id,
                    episode_id=metadata.episode_id,
                    episode_title=metadata.episode_title,
                    guest_name=metadata.guest_name,
                    guest_role=metadata.guest_role,
                    topic=metadata.topic,
                    url=metadata.url,
                    timestamp=time_label,
                    chunk_index=idx,
                    total_chunks=total_chunks,
                    text=formatted_text,
                    token_count=token_count,
                )
            )

        return chunks

    def chunk_file(self, file_path: Path | str) -> list[TranscriptChunk]:
        """Load and chunk a single transcript file (JSON or text/markdown)."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Transcript file not found: {file_path}")

        content_raw = path.read_text(encoding="utf-8")

        if path.suffix.lower() == ".json":
            data = json.loads(content_raw)
            metadata = TranscriptMetadata(
                episode_id=data.get("episode_id", path.stem),
                episode_title=data.get("episode_title", path.stem.replace("_", " ").title()),
                guest_name=data.get("guest_name", "Lenny Rachitsky"),
                guest_role=data.get("guest_role", "Host / Guest"),
                topic=data.get("topic", "Product & Growth"),
                url=data.get("url", ""),
                publication_date=data.get("publication_date"),
                summary=data.get("summary"),
                key_takeaways=data.get("key_takeaways", []),
            )
            dialogue_turns = data.get("transcript", [])
            if isinstance(dialogue_turns, list) and dialogue_turns and isinstance(dialogue_turns[0], dict):
                return self.chunk_structured_transcript(metadata, dialogue_turns)
            elif isinstance(dialogue_turns, str):
                return self.chunk_structured_transcript(
                    metadata, [{"speaker": metadata.guest_name, "text": dialogue_turns, "timestamp": "00:00:00"}]
                )
            else:
                raise ValueError(f"Invalid or empty transcript format in {path.name}")
        else:
            metadata = TranscriptMetadata(
                episode_id=path.stem,
                episode_title=path.stem.replace("_", " ").title(),
                guest_name="Lenny Rachitsky",
                guest_role="Host",
                topic="Product & Growth",
                url="",
            )
            return self.chunk_structured_transcript(
                metadata, [{"speaker": "Speaker", "text": content_raw, "timestamp": "00:00:00"}]
            )

    def chunk_directory(self, dir_path: Path | str, strict: bool = True) -> list[TranscriptChunk]:
        """Recursively scan and chunk all transcript files in a directory.

        Args:
            dir_path: Directory containing transcript files.
            strict: If True, raises RuntimeError if any transcript file fails to parse or chunk.
        """
        path = Path(dir_path)
        if not path.is_dir():
            raise NotADirectoryError(f"Transcripts directory not found: {dir_path}")

        all_chunks: list[TranscriptChunk] = []
        failed_files: dict[str, str] = {}
        files = sorted(list(path.glob("*.json")) + list(path.glob("*.md")) + list(path.glob("*.txt")))

        logger.info(f"Discovered {len(files)} transcript files in {dir_path}")
        for file in files:
            try:
                chunks = self.chunk_file(file)
                all_chunks.extend(chunks)
                logger.debug(f"Chunked {file.name}: {len(chunks)} chunks generated.")
            except Exception as exc:
                logger.error(f"Failed to chunk {file.name}: {exc}", exc_info=True)
                failed_files[file.name] = str(exc)

        if failed_files and strict:
            raise RuntimeError(
                f"Transcript chunking failed for {len(failed_files)} file(s) in {dir_path}: {failed_files}"
            )

        return all_chunks
