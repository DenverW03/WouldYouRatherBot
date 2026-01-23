"""Text-to-speech generation service for voice narration."""

import os
from pathlib import Path
from typing import Optional


class TTSGeneratorError(Exception):
    """Exception raised when TTS generation fails."""

    pass


# Available voice options with user-friendly names
# Maps voice_id to model configuration
# Note: Only includes models that don't require external dependencies like espeak.
# These models use character-based or internal phonemizer approaches.
AVAILABLE_VOICES = {
    "ljspeech_tacotron": {
        "model": "tts_models/en/ljspeech/tacotron2-DDC",
        "description": "Linda (Female) - Clear American accent",
    },
    "ljspeech_tacotron_ph": {
        "model": "tts_models/en/ljspeech/tacotron2-DDC_ph",
        "description": "Laura (Female) - Crisp American accent",
    },
    "ljspeech_glowtts": {
        "model": "tts_models/en/ljspeech/glow-tts",
        "description": "Lisa (Female) - Smooth American accent",
    },
    "jenny": {
        "model": "tts_models/en/jenny/jenny",
        "description": "Jenny (Female) - Natural British accent",
    },
}

DEFAULT_VOICE = "ljspeech_tacotron"


def get_voice_options() -> list[tuple[str, str]]:
    """Get list of available voice options for UI display.

    Returns:
        List of (voice_id, description) tuples.
    """
    return [(voice_id, info["description"]) for voice_id, info in AVAILABLE_VOICES.items()]


def get_default_voice() -> str:
    """Get the default voice ID.

    Returns:
        The default voice identifier.
    """
    return DEFAULT_VOICE


class TTSGenerator:
    """Generates text-to-speech audio for video narration.

    Uses Coqui TTS for high-quality speech synthesis.
    """

    def __init__(self, voice_id: Optional[str] = None, model_name: Optional[str] = None):
        """Initialize the TTS generator.

        Args:
            voice_id: Optional voice identifier from AVAILABLE_VOICES.
                     Takes precedence over model_name if provided.
            model_name: Optional TTS model name. If None, uses a default model.
                       Ignored if voice_id is provided.
        """
        self._tts = None
        self._speaker = None

        if voice_id and voice_id in AVAILABLE_VOICES:
            voice_config = AVAILABLE_VOICES[voice_id]
            self._model_name = voice_config["model"]
            self._speaker = voice_config.get("speaker")
        else:
            self._model_name = model_name or AVAILABLE_VOICES[DEFAULT_VOICE]["model"]

    def _get_tts(self):
        """Lazily initialize the TTS engine.

        Returns:
            TTS instance.

        Raises:
            TTSGeneratorError: If TTS initialization fails.
        """
        if self._tts is not None:
            return self._tts

        try:
            from TTS.api import TTS

            self._tts = TTS(model_name=self._model_name, progress_bar=False)
            return self._tts
        except ImportError:
            raise TTSGeneratorError(
                "Text-to-speech is not available. The TTS package could not be loaded. "
                "Please ensure the 'TTS' package is installed correctly."
            )
        except Exception as e:
            raise TTSGeneratorError(f"Failed to initialize text-to-speech: {str(e)}")

    def generate(self, text: str, output_path: str) -> str:
        """Generate speech audio from text.

        Args:
            text: The text to convert to speech.
            output_path: Path where the audio file will be saved.

        Returns:
            The path to the generated audio file.

        Raises:
            TTSGeneratorError: If speech generation fails.
        """
        if not text or not text.strip():
            raise TTSGeneratorError("Cannot generate speech from empty text.")

        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            # Get or initialize TTS engine
            tts = self._get_tts()

            # Generate speech (with speaker if multi-speaker model)
            if self._speaker:
                tts.tts_to_file(text=text, file_path=output_path, speaker=self._speaker)
            else:
                tts.tts_to_file(text=text, file_path=output_path)

            # Verify the file was created
            if not os.path.exists(output_path):
                raise TTSGeneratorError("Speech audio file was not created.")

            return output_path

        except TTSGeneratorError:
            raise
        except Exception as e:
            raise TTSGeneratorError(f"Speech generation failed: {str(e)}")

    @staticmethod
    def is_available() -> bool:
        """Check if TTS functionality is available.

        Returns:
            True if TTS can be used, False otherwise.
        """
        try:
            from TTS.api import TTS

            return True
        except ImportError:
            return False
