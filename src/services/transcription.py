"""Voice transcription service with OpenAI Whisper integration."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple, List
from enum import Enum


class TranscriptionProvider(str, Enum):
    """Supported transcription providers."""
    OPENAI = "openai"
    MOCK = "mock"


@dataclass
class TranscriptionResult:
    """Result of a voice transcription."""
    text: str
    confidence: float  # 0-1 scale
    language: str  # Detected language code
    duration_seconds: float
    provider: TranscriptionProvider
    segments: Optional[List[dict]] = None  # Word-level timestamps if available
    error: Optional[str] = None


class TranscriptionService(ABC):
    """Abstract base class for transcription services."""

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        language_hint: Optional[str] = None,
        format: str = "ogg",
    ) -> TranscriptionResult:
        """
        Transcribe audio data to text.

        Args:
            audio_data: Raw audio bytes
            language_hint: Optional language code hint (e.g., 'en', 'sw')
            format: Audio format (ogg, mp3, wav, m4a)

        Returns:
            TranscriptionResult with text and metadata
        """
        pass

    def calculate_confidence(self, segments: List[dict]) -> float:
        """Calculate overall confidence from segment data."""
        if not segments:
            return 0.8  # Default confidence

        # Average the segment confidences
        confidences = [s.get("confidence", 0.8) for s in segments if "confidence" in s]
        if confidences:
            return sum(confidences) / len(confidences)
        return 0.8


class OpenAITranscriptionService(TranscriptionService):
    """OpenAI Whisper API transcription service."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

    async def transcribe(
        self,
        audio_data: bytes,
        language_hint: Optional[str] = None,
        format: str = "ogg",
    ) -> TranscriptionResult:
        """Transcribe using OpenAI Whisper API."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                # Prepare the file for upload
                files = {
                    "file": (f"audio.{format}", audio_data, f"audio/{format}"),
                }
                data = {
                    "model": "whisper-1",
                    "response_format": "verbose_json",
                }
                if language_hint:
                    data["language"] = language_hint

                response = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=files,
                    data=data,
                )

                if response.status_code != 200:
                    return TranscriptionResult(
                        text="",
                        confidence=0.0,
                        language="",
                        duration_seconds=0.0,
                        provider=TranscriptionProvider.OPENAI,
                        error=f"API error: {response.status_code} - {response.text}",
                    )

                result = response.json()

                # Extract segments for confidence calculation
                segments = result.get("segments", [])
                confidence = self.calculate_confidence(segments)

                return TranscriptionResult(
                    text=result.get("text", ""),
                    confidence=confidence,
                    language=result.get("language", "en"),
                    duration_seconds=result.get("duration", 0.0),
                    provider=TranscriptionProvider.OPENAI,
                    segments=segments,
                )

        except ImportError:
            return TranscriptionResult(
                text="",
                confidence=0.0,
                language="",
                duration_seconds=0.0,
                provider=TranscriptionProvider.OPENAI,
                error="httpx library not installed. Run: pip install httpx",
            )
        except Exception as e:
            return TranscriptionResult(
                text="",
                confidence=0.0,
                language="",
                duration_seconds=0.0,
                provider=TranscriptionProvider.OPENAI,
                error=str(e),
            )


class MockTranscriptionService(TranscriptionService):
    """Mock transcription service for testing."""

    # Sample transcriptions for demo
    SAMPLE_TRANSCRIPTIONS = [
        {
            "text": "Hi, this is Sarah from Saruni Mara. We need 50 kilos of rice, 20 kilos of sugar, and 10 liters of cooking oil for delivery on Friday.",
            "language": "en",
            "duration": 8.5,
        },
        {
            "text": "Habari, nataka kuagiza mchele kilo hamsini, sukari kilo ishirini, na mafuta ya kupika lita kumi.",
            "language": "sw",
            "duration": 7.2,
        },
        {
            "text": "Good morning, please send us the usual order. Also add 5 crates of eggs and 20 loaves of bread.",
            "language": "en",
            "duration": 6.0,
        },
        {
            "text": "We need 30 kg maize flour, 15 kg wheat flour, and 10 packets of salt. Delivery ASAP please.",
            "language": "en",
            "duration": 5.8,
        },
    ]

    def __init__(self, sample_index: int = 0):
        self.sample_index = sample_index

    async def transcribe(
        self,
        audio_data: bytes,
        language_hint: Optional[str] = None,
        format: str = "ogg",
    ) -> TranscriptionResult:
        """Return a sample transcription for testing."""
        # Use audio data length to vary the sample
        sample_idx = (len(audio_data) + self.sample_index) % len(self.SAMPLE_TRANSCRIPTIONS)
        sample = self.SAMPLE_TRANSCRIPTIONS[sample_idx]

        # Filter by language hint if provided
        if language_hint:
            matching = [s for s in self.SAMPLE_TRANSCRIPTIONS if s["language"] == language_hint]
            if matching:
                sample = matching[0]

        return TranscriptionResult(
            text=sample["text"],
            confidence=0.92,  # Mock high confidence
            language=sample["language"],
            duration_seconds=sample["duration"],
            provider=TranscriptionProvider.MOCK,
        )


def get_transcription_service(
    provider: str = "mock",
    api_key: Optional[str] = None,
) -> TranscriptionService:
    """
    Factory function to get a transcription service.

    Args:
        provider: 'openai' or 'mock'
        api_key: API key for OpenAI (optional, uses env var)

    Returns:
        TranscriptionService instance
    """
    provider_enum = TranscriptionProvider(provider.lower())

    if provider_enum == TranscriptionProvider.OPENAI:
        return OpenAITranscriptionService(api_key)
    else:
        return MockTranscriptionService()


# Confidence thresholds for voice transcription
VOICE_CONFIDENCE_THRESHOLDS = {
    "high": 0.85,
    "medium": 0.70,
    "low": 0.50,
}


def adjust_extraction_confidence_for_voice(
    extraction_confidence: str,
    transcription_confidence: float,
) -> str:
    """
    Adjust extraction confidence based on transcription quality.

    Voice transcriptions are inherently less reliable, so we may
    need to downgrade confidence levels.

    Args:
        extraction_confidence: The extraction confidence ('high', 'medium', 'low')
        transcription_confidence: The transcription confidence (0-1)

    Returns:
        Adjusted confidence level
    """
    # If transcription confidence is low, cap extraction confidence
    if transcription_confidence < VOICE_CONFIDENCE_THRESHOLDS["low"]:
        return "low"

    if transcription_confidence < VOICE_CONFIDENCE_THRESHOLDS["medium"]:
        # Cap at medium
        if extraction_confidence == "high":
            return "medium"
        return extraction_confidence

    if transcription_confidence < VOICE_CONFIDENCE_THRESHOLDS["high"]:
        # Slight downgrade for high confidence
        if extraction_confidence == "high":
            return "medium"
        return extraction_confidence

    # High transcription confidence - no adjustment needed
    return extraction_confidence
