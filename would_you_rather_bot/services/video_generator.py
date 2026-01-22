"""Video generation service for creating 'Would You Rather?' videos."""

import os
from pathlib import Path
from typing import Callable, Optional, Union

import numpy as np
from moviepy import ImageClip, CompositeVideoClip, TextClip, AudioFileClip
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
    DURATION = 6  # Total video duration in seconds
    ANIMATION_DURATION = 0.3  # Duration of entrance/exit animations
    
    # Timing for options (staggered to match TTS narration)
    OPTION1_START = 1  # When option 1 (upper) appears
    OPTION2_START = 2  # When option 2 (lower) appears
    PERCENTAGE_START = 4  # When percentages replace text
    EXIT_START = 5  # When exit animation begins
    
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
        upper_percentage: Optional[float] = None,
        lower_percentage: Optional[float] = None,
        audio_path: Optional[str] = None,
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
            upper_percentage: Optional percentage for upper option (shown at end).
            lower_percentage: Optional percentage for lower option (shown at end).
            audio_path: Optional path to audio file for narration.

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

            # Create image clips with staggered animations
            # Option 1 appears at OPTION1_START, Option 2 appears at OPTION2_START
            upper_clip = self._create_animated_image(
                upper_image, self.upper_offset, from_right=False, start_time=self.OPTION1_START
            )
            lower_clip = self._create_animated_image(
                lower_image, self.lower_offset, from_right=True, start_time=self.OPTION2_START
            )

            if progress_callback:
                progress_callback(12, "Creating text overlays...")

            # Calculate when to switch to percentage display
            show_percentages = upper_percentage is not None and lower_percentage is not None

            # Create text clips with staggered start times
            # Upper text: starts at OPTION1_START, ends at PERCENTAGE_START (if showing percentages) or DURATION
            upper_text_end = self.PERCENTAGE_START if show_percentages else self.DURATION
            upper_text_duration = upper_text_end - self.OPTION1_START
            upper_text_clip = self._create_text_clip(
                upper_text, self.upper_offset_text, duration=upper_text_duration
            )

            # Lower text: starts at OPTION2_START, ends at PERCENTAGE_START (if showing percentages) or DURATION
            lower_text_end = self.PERCENTAGE_START if show_percentages else self.DURATION
            lower_text_duration = lower_text_end - self.OPTION2_START
            lower_text_clip = self._create_text_clip(
                lower_text, self.lower_offset_text, duration=lower_text_duration
            )

            # Build list of clips
            clips = [
                background_clip,
                upper_clip.with_start(self.OPTION1_START),
                lower_clip.with_start(self.OPTION2_START),
                upper_text_clip.with_start(self.OPTION1_START),
                lower_text_clip.with_start(self.OPTION2_START),
            ]

            # Add percentage text clips if enabled
            if show_percentages:
                if progress_callback:
                    progress_callback(13, "Adding percentage overlays...")

                percentage_duration = self.DURATION - self.PERCENTAGE_START
                upper_pct_clip = self._create_percentage_clip(
                    upper_percentage, self.upper_offset_text, duration=percentage_duration
                )
                lower_pct_clip = self._create_percentage_clip(
                    lower_percentage, self.lower_offset_text, duration=percentage_duration
                )
                clips.extend([
                    upper_pct_clip.with_start(self.PERCENTAGE_START),
                    lower_pct_clip.with_start(self.PERCENTAGE_START),
                ])

            if progress_callback:
                progress_callback(15, "Compositing video layers...")

            # Compose all clips
            final_clip = CompositeVideoClip(clips).with_fps(self.FPS)

            # Add audio if provided
            if audio_path and os.path.exists(audio_path):
                if progress_callback:
                    progress_callback(16, "Adding audio...")
                try:
                    audio_clip = AudioFileClip(audio_path)
                    # Ensure audio doesn't exceed video duration
                    if audio_clip.duration > self.DURATION:
                        audio_clip = audio_clip.subclipped(0, self.DURATION)
                    final_clip = final_clip.with_audio(audio_clip)
                except Exception as e:
                    # Log but don't fail if audio can't be added
                    if progress_callback:
                        progress_callback(16, "Warning: Could not add audio")

            # Create progress logger if callback provided
            logger = ProgressCallback(progress_callback) if progress_callback else None

            # Write the video file
            final_clip.write_videofile(
                output_path,
                fps=self.FPS,
                codec="libx264",
                audio_codec="aac" if audio_path else None,
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

    def _create_text_clip(
        self, text: str, y_offset: float, duration: Optional[float] = None
    ) -> TextClip:
        """Create a text clip with styling.

        Args:
            text: The text content.
            y_offset: Vertical position on screen.
            duration: Optional duration override.

        Returns:
            A styled TextClip.
        """
        if duration is None:
            duration = self.DURATION - self.OPTION1_START

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
        text_clip = text_clip.with_position(("center", y_offset)).with_duration(duration)
        return text_clip

    def _create_percentage_clip(
        self, percentage: float, y_offset: float, duration: Optional[float] = None
    ) -> TextClip:
        """Create a percentage display text clip.

        Args:
            percentage: The percentage value to display.
            y_offset: Vertical position on screen.
            duration: Optional duration override.

        Returns:
            A styled TextClip showing the percentage.
        """
        if duration is None:
            duration = self.DURATION - self.PERCENTAGE_START

        # Format percentage - show as integer if whole number, else one decimal
        if percentage == int(percentage):
            pct_text = f"{int(percentage)}%"
        else:
            pct_text = f"{percentage:.1f}%"

        text_clip = TextClip(
            text=pct_text,
            size=(self.VIDEO_WIDTH, self.VIDEO_HEIGHT),
            vertical_align="top",
            font_size=120,
            color="white",
            font=self.font_path,
            stroke_color="black",
            stroke_width=5,
        )
        text_clip = text_clip.with_position(("center", y_offset)).with_duration(duration)
        return text_clip

    def _create_animated_image(
        self, image: Image.Image, y_offset: float, from_right: bool, start_time: float = 0
    ) -> ImageClip:
        """Create an animated image clip with entrance and exit animations.

        Args:
            image: PIL Image to animate.
            y_offset: Vertical position on screen.
            from_right: If True, enters from right; if False, enters from left.
            start_time: When this clip starts in the video timeline.

        Returns:
            An animated ImageClip.
        """
        # Calculate clip duration (from start_time to end of video)
        clip_duration = self.DURATION - start_time

        # Create clip from image
        clip = ImageClip(np.array(image), duration=clip_duration)

        # Calculate resize multiplier
        resize_mult = self._calc_resize_mult(clip)
        clip = clip.resized(resize_mult)

        # Apply rotation animation
        clip = clip.transform(self._create_rotation_transform())

        # Apply position animation (using clip-relative time, not video time)
        clip = clip.with_position(
            self._create_position_function(clip.w, y_offset, from_right, clip_duration)
        ).with_duration(clip_duration)

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
        self, image_width: float, y_offset: float, from_right: bool, clip_duration: float
    ):
        """Create a position function for entrance/exit animations.

        Args:
            image_width: Width of the image.
            y_offset: Vertical position.
            from_right: Animation direction.
            clip_duration: Duration of this clip.

        Returns:
            A position function for moviepy.
        """
        center_x = (self.VIDEO_WIDTH / 2) - (image_width / 2)
        
        # Calculate exit start time relative to clip start
        # Exit animation completes at DURATION, starts at EXIT_START
        # So relative to clip: exit_start_relative = clip_duration - (DURATION - EXIT_START)
        exit_duration = self.DURATION - self.EXIT_START  # Time from exit start to video end
        exit_start_relative = clip_duration - exit_duration

        def get_position(t):
            # Exit animation (starts at exit_start_relative within clip's timeline)
            if t >= exit_start_relative:
                exit_progress = min(1, (t - exit_start_relative) / exit_duration)
                if from_right:
                    # Exit to right
                    offscreen_x = self.VIDEO_WIDTH
                    current_x = center_x + (offscreen_x - center_x) * exit_progress
                else:
                    # Exit to left
                    offscreen_x = -self.MAX_DIMENSION
                    current_x = center_x + (offscreen_x - center_x) * exit_progress
                return current_x, y_offset

            # Entrance animation (at the start of clip)
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
