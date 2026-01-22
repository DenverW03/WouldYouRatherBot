"""Text-to-speech generation service for voice narration."""

import os
from pathlib import Path
from typing import Optional


class TTSGeneratorError(Exception):
    """Exception raised when TTS generation fails."""

    pass


class TTSGenerator:
    """Generates text-to-speech audio for video narration.

    Uses Coqui TTS for high-quality speech synthesis.
    """

    def __init__(self, model_name: Optional[str] = None):
        """Initialize the TTS generator.

        Args:
            model_name: Optional TTS model name. If None, uses a default model.
        """
        self._tts = None
        self._model_name = model_name or "tts_models/en/ljspeech/tacotron2-DDC"

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

            # Generate speech
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
