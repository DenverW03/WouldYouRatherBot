"""Video generation service for creating 'Would You Rather?' videos."""

import os
from pathlib import Path
from typing import Callable, Optional, Union

import numpy as np
from moviepy import ImageClip, CompositeVideoClip, TextClip
from PIL import Image
from proglog import ProgressBarLogger


class VideoGeneratorError(Exception):
    """Exception raised when video generation fails."""

    pass


class ProgressCallback(ProgressBarLogger):
    """Custom progress logger that calls a callback function with progress updates."""

    def __init__(self, progress_fn: Optional[Callable[[int, str], None]] = None):
        """Initialize the progress callback.

        Args:
            progress_fn: Function to call with (progress_percent, status_message).
        """
        super().__init__()
        self.progress_fn = progress_fn
        self.last_percent = 0

    def bars_callback(self, bar, attr, value, old_value=None):
        """Called when progress bar is updated."""
        if self.progress_fn is None:
            return

        if bar == "frame_index" and attr == "index":
            # This is the frame rendering progress
            total = self.bars.get("frame_index", {}).get("total", 0)
            if total > 0:
                # Scale to 15-95% range (leaving room for setup and encoding)
                percent = int(15 + (value / total) * 80)
                if percent != self.last_percent:
                    self.last_percent = percent
                    self.progress_fn(percent, "Rendering video frames...")


class VideoGenerator:
    """Generates 'Would You Rather?' style videos with animated images and text."""

    # Video settings
    DURATION = 10  # Total video duration in seconds
    ANIMATION_DURATION = 0.3  # Duration of entrance/exit animations
    IMAGE_EXIT_OFFSET = 0.6  # When to start exit animation before video ends
    TEXT_START = 1  # When text starts to fade in
    MAX_DIMENSION = 500  # Maximum dimension for images
    FPS = 30  # Frames per second

    # Layout calculations for 1080x1920 (9:16 portrait)
    VIDEO_WIDTH = 1080
    VIDEO_HEIGHT = 1920

    def __init__(self, background_path: Optional[str] = None, font_path: Optional[str] = None):
        """Initialize the video generator.

        Args:
            background_path: Path to the background image. If None, uses default.
            font_path: Path to the font file. If None, uses bundled font.
        """
        assets_dir = Path(__file__).parent.parent / "assets"

        if background_path is None:
            background_path = str(assets_dir / "background.jpg")

        if font_path is None:
            font_path = str(assets_dir / "DejaVuSans-Bold.ttf")

        if not os.path.exists(background_path):
            raise VideoGeneratorError(f"Background image not found: {background_path}")

        if not os.path.exists(font_path):
            raise VideoGeneratorError(f"Font file not found: {font_path}")

        self.background_path = background_path
        self.font_path = font_path
        self._calculate_offsets()

    def _calculate_offsets(self):
        """Calculate positioning offsets for images and text."""
        # Image vertical positions (upper and lower halves)
        self.upper_offset = ((self.VIDEO_HEIGHT / 2) - self.MAX_DIMENSION) / 2
        self.lower_offset = (self.VIDEO_HEIGHT - self.upper_offset) - self.MAX_DIMENSION

        # Text vertical positions
        self.upper_offset_text = (self.VIDEO_HEIGHT / 2) - 200
        self.lower_offset_text = (self.VIDEO_HEIGHT / 2) + 40

    def generate(
        self,
        upper_text: str,
        lower_text: str,
        upper_image: Image.Image,
        lower_image: Image.Image,
        output_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> str:
        """Generate a 'Would You Rather?' video.

        Args:
            upper_text: Text for the first (upper) option.
            lower_text: Text for the second (lower) option.
            upper_image: PIL Image for the upper option.
            lower_image: PIL Image for the lower option.
            output_path: Path where the video will be saved.
            progress_callback: Optional callback function that receives
                (progress_percent, status_message) updates.

        Returns:
            The path to the generated video.

        Raises:
            VideoGeneratorError: If video generation fails.
        """
        try:
            if progress_callback:
                progress_callback(5, "Initializing...")

            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            if progress_callback:
                progress_callback(8, "Creating background...")

            # Create background clip
            background_clip = ImageClip(self.background_path, duration=self.DURATION)

            if progress_callback:
                progress_callback(10, "Processing images...")

            # Create image clips with animations
            upper_clip = self._create_animated_image(
                upper_image, self.upper_offset, from_right=False
            )
            lower_clip = self._create_animated_image(
                lower_image, self.lower_offset, from_right=True
            )

            if progress_callback:
                progress_callback(12, "Creating text overlays...")

            # Create text clips
            upper_text_clip = self._create_text_clip(upper_text, self.upper_offset_text)
            lower_text_clip = self._create_text_clip(lower_text, self.lower_offset_text)

            if progress_callback:
                progress_callback(15, "Compositing video layers...")

            # Compose all clips
            final_clip = CompositeVideoClip(
                [
                    background_clip,
                    upper_clip,
                    lower_clip,
                    upper_text_clip.with_start(self.TEXT_START),
                    lower_text_clip.with_start(self.TEXT_START),
                ]
            ).with_fps(self.FPS)

            # Create progress logger if callback provided
            logger = ProgressCallback(progress_callback) if progress_callback else None

            # Write the video file
            final_clip.write_videofile(
                output_path,
                fps=self.FPS,
                codec="libx264",
                audio=False,
                logger=logger,
            )

            if progress_callback:
                progress_callback(98, "Finalizing...")

            # Clean up
            final_clip.close()

            if progress_callback:
                progress_callback(100, "Complete!")

            return output_path

        except VideoGeneratorError:
            raise
        except Exception as e:
            raise VideoGeneratorError(f"Video generation failed: {str(e)}")

    def _create_text_clip(self, text: str, y_offset: float) -> TextClip:
        """Create a text clip with styling.

        Args:
            text: The text content.
            y_offset: Vertical position on screen.

        Returns:
            A styled TextClip.
        """
        text_clip = TextClip(
            text=text,
            size=(self.VIDEO_WIDTH, self.VIDEO_HEIGHT),
            vertical_align="top",
            font_size=100,
            color="white",
            font=self.font_path,
            stroke_color="black",
            stroke_width=4,
        )
        text_clip = text_clip.with_position(("center", y_offset)).with_duration(
            self.DURATION - self.TEXT_START
        )
        return text_clip

    def _create_animated_image(
        self, image: Image.Image, y_offset: float, from_right: bool
    ) -> ImageClip:
        """Create an animated image clip with entrance and exit animations.

        Args:
            image: PIL Image to animate.
            y_offset: Vertical position on screen.
            from_right: If True, enters from right; if False, enters from left.

        Returns:
            An animated ImageClip.
        """
        # Create clip from image
        clip = ImageClip(np.array(image), duration=self.DURATION)

        # Calculate resize multiplier
        resize_mult = self._calc_resize_mult(clip)
        clip = clip.resized(resize_mult)

        # Apply rotation animation
        clip = clip.transform(self._create_rotation_transform())

        # Apply position animation
        clip = clip.with_position(
            self._create_position_function(clip.w, y_offset, from_right)
        ).with_duration(self.DURATION)

        return clip

    def _calc_resize_mult(self, clip: ImageClip) -> float:
        """Calculate resize multiplier to fit image within max dimension.

        Args:
            clip: The image clip to resize.

        Returns:
            The resize multiplier.
        """
        largest_dimension = max(clip.w, clip.h)
        return self.MAX_DIMENSION / largest_dimension

    def _create_rotation_transform(self):
        """Create a rotation transformation function for the entrance animation.

        Returns:
            A transform function for moviepy.
        """

        def rotate_and_translate(get_frame, t):
            frame = get_frame(t)

            # Calculate rotation angle (90° to 0° during animation)
            start_angle = 90
            end_angle = 0
            progress = min(1, t / self.ANIMATION_DURATION)
            current_angle = start_angle + (end_angle - start_angle) * progress

            # Apply rotation using PIL
            image_pil = Image.fromarray(frame)

            # Convert to RGBA for proper rotation with transparency
            im2 = image_pil.convert("RGBA")
            rotated_image = im2.rotate(current_angle, expand=True)

            # Composite with transparent background
            background = Image.new("RGBA", rotated_image.size, (255, 255, 255, 0))
            result = Image.composite(rotated_image, background, rotated_image)

            return np.array(result)

        return rotate_and_translate

    def _create_position_function(
        self, image_width: float, y_offset: float, from_right: bool
    ):
        """Create a position function for entrance/exit animations.

        Args:
            image_width: Width of the image.
            y_offset: Vertical position.
            from_right: Animation direction.

        Returns:
            A position function for moviepy.
        """
        center_x = (self.VIDEO_WIDTH / 2) - (image_width / 2)

        def get_position(t):
            # Exit animation
            if t >= self.DURATION - self.IMAGE_EXIT_OFFSET:
                exit_progress = min(
                    1, (t - (self.DURATION - self.IMAGE_EXIT_OFFSET)) / self.ANIMATION_DURATION
                )
                if from_right:
                    # Exit to right
                    offscreen_x = self.VIDEO_WIDTH
                    current_x = center_x + (offscreen_x - center_x) * exit_progress
                else:
                    # Exit to left
                    offscreen_x = -self.MAX_DIMENSION
                    current_x = center_x + (offscreen_x - center_x) * exit_progress
                return current_x, y_offset

            # Entrance animation
            entrance_progress = min(1, t / self.ANIMATION_DURATION)
            if from_right:
                # Enter from right
                offscreen_x = self.VIDEO_WIDTH
                current_x = offscreen_x + (center_x - offscreen_x) * entrance_progress
            else:
                # Enter from left
                offscreen_x = -self.MAX_DIMENSION
                current_x = offscreen_x + (center_x - offscreen_x) * entrance_progress

            return current_x, y_offset

        return get_position
