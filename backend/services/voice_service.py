# =============================================================================
# BRKOPS-2585 Voice Service
# Whisper API integration for speech-to-text
# =============================================================================

import io
from typing import Optional

import httpx
import structlog

from config import settings
from models.voice import TranscriptionResponse

logger = structlog.get_logger()


class VoiceService:
    """
    Voice transcription service using OpenAI Whisper API.
    """

    def __init__(self, http_timeout: int = 60):
        """Initialize voice service."""
        self.api_key = settings.openai_api_key
        self.http_timeout = http_timeout
        if not self.api_key:
            logger.warning("OpenAI API key not configured for voice service")

    async def transcribe(
        self,
        audio_data: bytes,
        filename: str = "audio.wav",
        language: str = "en",
        prompt: Optional[str] = None,
    ) -> TranscriptionResponse:
        """
        Transcribe audio data using Whisper API.

        Args:
            audio_data: Raw audio bytes
            filename: Original filename (for format detection)
            language: Language code (e.g., "en", "de", "es")
            prompt: Optional prompt to guide transcription

        Returns:
            TranscriptionResponse with transcribed text
        """
        if not self.api_key:
            raise RuntimeError("OpenAI API key not configured")

        # Determine content type from filename
        content_type = self._get_content_type(filename)

        # Prepare multipart form data
        files = {
            "file": (filename, io.BytesIO(audio_data), content_type),
        }

        data = {
            "model": "whisper-1",
            "language": language,
            "response_format": "verbose_json",
        }

        if prompt:
            data["prompt"] = prompt

        # Network engineering prompt for better accuracy
        network_prompt = (
            "This is a voice command from a network engineer. "
            "Common terms include: OSPF, BGP, EIGRP, router, switch, "
            "interface, VLAN, ACL, configuration, IP address, subnet, "
            "area, neighbor, adjacency, credential, password, username."
        )
        data["prompt"] = network_prompt + (f" {prompt}" if prompt else "")

        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                response = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    files=files,
                    data=data,
                )

                if response.status_code != 200:
                    error = response.text
                    logger.error("Whisper API error", status=response.status_code, error=error)
                    raise Exception(f"Whisper API error: {error}")

                result = response.json()

                return TranscriptionResponse(
                    text=result.get("text", ""),
                    language=result.get("language", language),
                    duration=result.get("duration"),
                    confidence=None,  # Whisper doesn't provide confidence
                )

        except httpx.TimeoutException:
            logger.error("Whisper API timeout")
            raise Exception("Transcription timed out")
        except Exception as e:
            logger.error("Transcription failed", error=str(e))
            raise

    async def transcribe_url(
        self,
        audio_url: str,
        language: str = "en",
    ) -> TranscriptionResponse:
        """
        Transcribe audio from a URL.

        Args:
            audio_url: URL to the audio file
            language: Language code

        Returns:
            TranscriptionResponse with transcribed text
        """
        # Download the audio file
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(audio_url)
                if response.status_code != 200:
                    raise Exception(f"Failed to download audio: {response.status_code}")

                audio_data = response.content

                # Get filename from URL
                filename = audio_url.split("/")[-1].split("?")[0]
                if not filename:
                    filename = "audio.wav"

                return await self.transcribe(audio_data, filename, language)

        except Exception as e:
            logger.error("Failed to transcribe from URL", url=audio_url, error=str(e))
            raise

    def _get_content_type(self, filename: str) -> str:
        """Get content type from filename."""
        ext = filename.lower().split(".")[-1] if "." in filename else ""

        content_types = {
            "mp3": "audio/mpeg",
            "mp4": "audio/mp4",
            "mpeg": "audio/mpeg",
            "mpga": "audio/mpeg",
            "m4a": "audio/mp4",
            "wav": "audio/wav",
            "webm": "audio/webm",
        }

        return content_types.get(ext, "audio/wav")
