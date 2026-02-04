# =============================================================================
# BRKOPS-2585 Voice Models
# Speech-to-text request/response schemas
# =============================================================================

from typing import Optional

from pydantic import BaseModel, Field


class TranscriptionRequest(BaseModel):
    """Request for audio transcription."""

    language: str = Field("en", description="Language code for transcription")
    prompt: Optional[str] = Field(None, description="Optional prompt to guide transcription")


class TranscriptionResponse(BaseModel):
    """Response from audio transcription."""

    text: str = Field(..., description="Transcribed text")
    language: str = Field(..., description="Detected or specified language")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")
    confidence: Optional[float] = Field(None, description="Transcription confidence score")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "I want to change OSPF configuration on Router-1 to use area 10",
                "language": "en",
                "duration": 4.5,
                "confidence": 0.95,
            }
        }


class StreamingTranscriptionChunk(BaseModel):
    """Chunk of streaming transcription."""

    text: str
    is_final: bool = False
    confidence: Optional[float] = None
