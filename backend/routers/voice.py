# =============================================================================
# BRKOPS-2585 Voice Router
# Speech-to-text transcription endpoints
# =============================================================================

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.voice import TranscriptionResponse
from services.voice_service import VoiceService

logger = structlog.get_logger()
router = APIRouter()


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = "en",
    db: AsyncSession = Depends(get_db),
):
    """
    Transcribe uploaded audio file using Whisper API.

    Supported formats: mp3, mp4, mpeg, mpga, m4a, wav, webm
    Maximum file size: 25MB
    """
    # Validate file type
    allowed_types = [
        "audio/mpeg",
        "audio/mp4",
        "audio/wav",
        "audio/webm",
        "audio/m4a",
        "video/mp4",
        "video/webm",
    ]

    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Supported: mp3, mp4, wav, webm, m4a",
        )

    # Check file size (25MB limit)
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 25MB limit",
        )

    logger.info(
        "Transcribing audio",
        filename=file.filename,
        size=len(content),
        content_type=file.content_type,
    )

    try:
        voice_service = VoiceService()
        result = await voice_service.transcribe(
            audio_data=content,
            filename=file.filename or "audio.wav",
            language=language,
        )

        logger.info("Transcription complete", text_length=len(result.text))

        return result

    except Exception as e:
        logger.error("Transcription failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )


@router.post("/transcribe/url", response_model=TranscriptionResponse)
async def transcribe_audio_url(
    audio_url: str,
    language: str = "en",
):
    """
    Transcribe audio from a URL.

    The audio file will be downloaded and transcribed.
    """
    logger.info("Transcribing audio from URL", url=audio_url)

    try:
        voice_service = VoiceService()
        result = await voice_service.transcribe_url(
            audio_url=audio_url,
            language=language,
        )

        return result

    except Exception as e:
        logger.error("Transcription from URL failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )
