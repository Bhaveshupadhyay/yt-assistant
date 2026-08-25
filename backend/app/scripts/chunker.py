"""CLI utility for chunking podcast transcripts and inspecting metadata.

Usage:
    uv run python -m app.scripts.chunker
    uv run python -m app.scripts.chunker --input ../data/transcripts --output ../data/chunks.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from app.services.chunker import TranscriptChunker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("chunker_cli")


def find_default_transcripts_dir() -> Path:
    """Intelligently locate the transcripts directory from common execution locations."""
    candidates = [
        Path("data/transcripts"),
        Path("../data/transcripts"),
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "transcripts",
        Path(__file__).resolve().parent.parent.parent / "data" / "transcripts",
    ]
    for p in candidates:
        if p.exists() and p.is_dir():
            return p.resolve()
    # Default fallback
    return Path("../data/transcripts").resolve()


def main() -> None:
    """CLI entrypoint for chunking transcripts."""
    parser = argparse.ArgumentParser(description="Split transcripts into semantic chunks with metadata.")
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=None,
        help="Path to directory containing transcript JSON files or a single file",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Optional path to output JSON file containing all generated chunks",
    )
    parser.add_argument(
        "--min-tokens",
        type=int,
        default=500,
        help="Minimum token threshold per chunk (default: 500)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=700,
        help="Maximum token threshold per chunk (default: 700)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=100,
        help="Token overlap between adjacent chunks (default: 100)",
    )

    args = parser.parse_args()

    input_path = Path(args.input) if args.input else find_default_transcripts_dir()
    if not input_path.exists():
        logger.error(f"Input path not found: {input_path}")
        sys.exit(1)

    logger.info(f"Using transcripts input path: {input_path}")
    chunker = TranscriptChunker(
        min_tokens=args.min_tokens,
        max_tokens=args.max_tokens,
        overlap_tokens=args.overlap,
    )

    if input_path.is_file():
        chunks = chunker.chunk_file(input_path)
    else:
        chunks = chunker.chunk_directory(input_path)

    if not chunks:
        logger.warning("No chunks were generated. Please verify transcript file formats.")
        sys.exit(0)

    token_counts = [c.token_count for c in chunks]
    avg_tokens = sum(token_counts) / len(chunks)
    min_tok = min(token_counts)
    max_tok = max(token_counts)

    print("\n" + "=" * 60)
    print("🎙️  LENNY TRANSCRIPT CHUNKING REPORT")
    print("=" * 60)
    print(f"Total Chunks Generated : {len(chunks)}")
    print(f"Average Tokens / Chunk : {avg_tokens:.1f}")
    print(f"Min Tokens in Chunk    : {min_tok}")
    print(f"Max Tokens in Chunk    : {max_tok}")
    print("-" * 60)

    # Per-episode summary
    episodes: dict[str, list] = {}
    for c in chunks:
        episodes.setdefault(c.guest_name, []).append(c)

    for guest, g_chunks in sorted(episodes.items()):
        print(f"• {guest:<25} : {len(g_chunks):>2} chunks  (Title: {g_chunks[0].episode_title[:45]}...)")

    print("=" * 60 + "\n")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = [c.model_dump() for c in chunks]
        out_path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")
        logger.info(f"Saved {len(chunks)} chunks to {out_path}")


if __name__ == "__main__":
    main()
