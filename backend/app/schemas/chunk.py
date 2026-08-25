"""Schemas for transcript metadata and semantic chunks."""

from pydantic import BaseModel, Field


class TranscriptMetadata(BaseModel):
    """Metadata for an episode transcript."""

    episode_id: str = Field(..., description="Unique identifier for the episode")
    episode_title: str = Field(..., description="Full title of the podcast episode")
    guest_name: str = Field(..., description="Name of the featured guest or host")
    guest_role: str = Field(..., description="Role and affiliation of the guest")
    topic: str = Field(..., description="Primary topic or subject matter of the episode")
    url: str = Field(..., description="Canonical URL to the episode (YouTube, Podcast)")
    publication_date: str | None = Field(default=None, description="Original publication date")
    summary: str | None = Field(default=None, description="Brief summary of the episode")
    key_takeaways: list[str] = Field(default_factory=list, description="Key actionable takeaways")


class TranscriptChunk(BaseModel):
    """A semantic chunk of a transcript ready for hybrid vector embedding and retrieval."""

    chunk_id: str = Field(..., description="Unique deterministic identifier for the chunk")
    episode_id: str = Field(..., description="Identifier of the source episode")
    episode_title: str = Field(..., description="Full title of the podcast episode")
    guest_name: str = Field(..., description="Name of the featured guest or host")
    guest_role: str = Field(..., description="Role and affiliation of the guest")
    topic: str = Field(..., description="Primary topic or subject matter")
    url: str = Field(..., description="Canonical episode URL")
    timestamp: str = Field(..., description="Start timestamp or time range of the excerpt")
    chunk_index: int = Field(..., description="0-indexed position of chunk in the episode")
    total_chunks: int = Field(..., description="Total number of chunks in the episode")
    text: str = Field(..., description="Full formatted chunk text content")
    token_count: int = Field(..., description="Estimated or exact token count of the chunk")

    @property
    def citation_label(self) -> str:
        """Formatted human-readable citation label."""
        return f"{self.guest_name} in '{self.episode_title}' [{self.timestamp}]"
