"""Would You Rather Bot - Main Reflex Application."""

import base64
import os
import random
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import reflex as rx

from .services.video_generator import VideoGenerator, VideoGeneratorError
from .services.image_retrieval import ImageProcessor, ImageProcessingError
from .services.tts_generator import (
    TTSGenerator,
    TTSGeneratorError,
    get_voice_options,
    get_default_voice,
    AVAILABLE_VOICES,
)
from .components import floating_support_button


# Color constants matching the video style
COLORS = {
    "red": "#ED1C24",
    "blue": "#3D9AE8",
    "black": "#000000",
    "white": "#FFFFFF",
    "dark_gray": "#1a1a1a",
    "light_gray": "#f5f5f5",
    "background_gray": "#4a4a4a",
    "off_white": "#e0e0e0",
}


class State(rx.State):
    """Application state for the video generator."""

    # Form inputs
    upper_text: str = ""
    lower_text: str = ""

    # Image upload tracking
    upper_image_data: Optional[str] = None
    lower_image_data: Optional[str] = None
    upper_image_name: str = ""
    lower_image_name: str = ""

    # Percentage settings
    show_percentages: bool = False
    auto_percentages: bool = True
    upper_percentage: str = ""
    lower_percentage: str = ""

    # TTS settings
    enable_tts: bool = False
    selected_voice: str = "ljspeech_tacotron"

    # Status tracking
    is_generating: bool = False
    error_message: str = ""
    success_message: str = ""

    # Video data for download (base64 encoded)
    video_data: Optional[str] = None
    video_ready: bool = False

    # Upload progress
    is_uploading_upper: bool = False
    is_uploading_lower: bool = False

    # Video generation progress
    generation_progress: int = 0
    generation_status: str = ""

    @rx.event
    def clear_messages(self):
        """Clear status messages."""
        self.error_message = ""
        self.success_message = ""

    @rx.event
    def set_upper_text(self, value: str):
        """Set the upper text value."""
        self.upper_text = value
        self.clear_messages()

    @rx.event
    def set_lower_text(self, value: str):
        """Set the lower text value."""
        self.lower_text = value
        self.clear_messages()

    @rx.event
    def toggle_show_percentages(self, value: bool):
        """Toggle the show percentages setting."""
        self.show_percentages = value
        self.clear_messages()

    @rx.event
    def toggle_auto_percentages(self, value: bool):
        """Toggle the auto-generate percentages setting."""
        self.auto_percentages = value
        self.clear_messages()

    @rx.event
    def set_upper_percentage(self, value: str):
        """Set the upper percentage value."""
        self.upper_percentage = value
        self.clear_messages()

    @rx.event
    def set_lower_percentage(self, value: str):
        """Set the lower percentage value."""
        self.lower_percentage = value
        self.clear_messages()

    @rx.event
    def toggle_tts(self, value: bool):
        """Toggle text-to-speech setting."""
        self.enable_tts = value
        self.clear_messages()

    @rx.event
    def set_voice_by_description(self, description: str):
        """Set the selected TTS voice by its description."""
        # Find the voice_id that matches this description
        for voice_id, info in AVAILABLE_VOICES.items():
            if info["description"] == description:
                self.selected_voice = voice_id
                break
        self.clear_messages()

    @rx.var
    def selected_voice_description(self) -> str:
        """Get the description of the currently selected voice."""
        if self.selected_voice in AVAILABLE_VOICES:
            return AVAILABLE_VOICES[self.selected_voice]["description"]
        return AVAILABLE_VOICES[get_default_voice()]["description"]

    @rx.event
    async def handle_upper_image_upload(self, files: list[rx.UploadFile]):
        """Handle upper image file upload."""
        self.is_uploading_upper = True
        self.clear_messages()

        try:
            if not files:
                self.error_message = "No file selected for Option 1 image."
                return

            file = files[0]
            upload_data = await file.read()

            # Validate the image can be processed
            try:
                ImageProcessor.process_uploaded_image(upload_data, file.filename)
            except ImageProcessingError as e:
                self.error_message = f"Option 1 image error: {str(e)}"
                return

            # Store as base64 for state persistence
            self.upper_image_data = base64.b64encode(upload_data).decode("utf-8")
            self.upper_image_name = file.filename or "image"

        except Exception as e:
            self.error_message = f"Failed to upload Option 1 image: {str(e)}"
        finally:
            self.is_uploading_upper = False

    @rx.event
    async def handle_lower_image_upload(self, files: list[rx.UploadFile]):
        """Handle lower image file upload."""
        self.is_uploading_lower = True
        self.clear_messages()

        try:
            if not files:
                self.error_message = "No file selected for Option 2 image."
                return

            file = files[0]
            upload_data = await file.read()

            # Validate the image can be processed
            try:
                ImageProcessor.process_uploaded_image(upload_data, file.filename)
            except ImageProcessingError as e:
                self.error_message = f"Option 2 image error: {str(e)}"
                return

            # Store as base64 for state persistence
            self.lower_image_data = base64.b64encode(upload_data).decode("utf-8")
            self.lower_image_name = file.filename or "image"

        except Exception as e:
            self.error_message = f"Failed to upload Option 2 image: {str(e)}"
        finally:
            self.is_uploading_lower = False

    @rx.event
    def clear_upper_image(self):
        """Clear the upper image."""
        self.upper_image_data = None
        self.upper_image_name = ""
        self.clear_messages()

    @rx.event
    def clear_lower_image(self):
        """Clear the lower image."""
        self.lower_image_data = None
        self.lower_image_name = ""
        self.clear_messages()

    def _validate_inputs(self) -> bool:
        """Validate all form inputs."""
        if not self.upper_text.strip():
            self.error_message = "Please enter text for Option 1."
            return False
        if not self.lower_text.strip():
            self.error_message = "Please enter text for Option 2."
            return False
        if not self.upper_image_data:
            self.error_message = "Please upload an image for Option 1."
            return False
        if not self.lower_image_data:
            self.error_message = "Please upload an image for Option 2."
            return False

        # Validate percentages if enabled and not auto-generated
        if self.show_percentages and not self.auto_percentages:
            upper_pct, lower_pct = self._parse_percentages()
            if upper_pct is None or lower_pct is None:
                self.error_message = "Please enter valid percentage values (numbers between 0 and 100)."
                return False
            if abs((upper_pct + lower_pct) - 100) > 0.01:
                self.error_message = f"Percentages must add up to 100%. Currently: {upper_pct}% + {lower_pct}% = {upper_pct + lower_pct}%"
                return False

        return True

    def _parse_percentages(self) -> tuple:
        """Parse percentage values from string inputs.
        
        Returns:
            Tuple of (upper_percentage, lower_percentage) as floats, or (None, None) if invalid.
        """
        try:
            upper_pct = float(self.upper_percentage.strip()) if self.upper_percentage.strip() else None
            lower_pct = float(self.lower_percentage.strip()) if self.lower_percentage.strip() else None
            
            if upper_pct is None or lower_pct is None:
                return (None, None)
            
            if upper_pct < 0 or upper_pct > 100 or lower_pct < 0 or lower_pct > 100:
                return (None, None)
                
            return (upper_pct, lower_pct)
        except ValueError:
            return (None, None)

    def _get_percentages(self) -> tuple:
        """Get percentage values, either auto-generated or user-provided.
        
        Returns:
            Tuple of (upper_percentage, lower_percentage) as floats.
        """
        if self.auto_percentages:
            # Generate random percentages that sum to 100
            upper_pct = random.randint(10, 90)
            lower_pct = 100 - upper_pct
            return (float(upper_pct), float(lower_pct))
        else:
            return self._parse_percentages()

    @rx.event(background=True)
    async def generate_video(self):
        """Generate the video based on form inputs."""
        import asyncio
        import threading

        async with self:
            self.error_message = ""
            self.success_message = ""
            self.video_data = None
            self.video_ready = False
            self.generation_progress = 0
            self.generation_status = ""

            if not self._validate_inputs():
                return

            self.is_generating = True
            self.generation_progress = 2
            self.generation_status = "Starting..."

        # Shared state for progress updates from the video generator thread
        progress_state = {"progress": 2, "status": "Starting..."}
        generation_complete = threading.Event()
        generation_result = {"success": False, "error": None, "video_base64": None}

        try:
            # Get data from state
            async with self:
                upper_image_data = self.upper_image_data
                lower_image_data = self.lower_image_data
                upper_text = self.upper_text.strip()
                lower_text = self.lower_text.strip()
                show_percentages = self.show_percentages
                enable_tts = self.enable_tts
                selected_voice = self.selected_voice

                # Get percentages if enabled
                if show_percentages:
                    upper_percentage, lower_percentage = self._get_percentages()
                else:
                    upper_percentage, lower_percentage = None, None

            # Process the uploaded images (quick operation)
            upper_image = ImageProcessor.process_uploaded_image(upper_image_data)
            lower_image = ImageProcessor.process_uploaded_image(lower_image_data)

            # Generate TTS audio if enabled
            tts_audio_path = None
            if enable_tts:
                async with self:
                    self.generation_progress = 3
                    self.generation_status = "Generating voice narration..."
                
                try:
                    tts_generator = TTSGenerator(voice_id=selected_voice)
                    tts_text = f"Would you rather {upper_text} or {lower_text}?"
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tts_file:
                        tts_audio_path = tts_file.name
                    tts_generator.generate(tts_text, tts_audio_path)
                except TTSGeneratorError as e:
                    async with self:
                        self.error_message = f"Voice generation failed: {str(e)}"
                        self.is_generating = False
                        self.generation_progress = 0
                        self.generation_status = ""
                    return

            # Create a temporary file for the video
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
                output_path = tmp_file.name

            def progress_callback(progress: int, status: str):
                """Callback to update progress from video generator."""
                progress_state["progress"] = progress
                progress_state["status"] = status

            def generate_in_thread():
                """Run video generation in a separate thread."""
                try:
                    generator = VideoGenerator()
                    generator.generate(
                        upper_text=upper_text,
                        lower_text=lower_text,
                        upper_image=upper_image,
                        lower_image=lower_image,
                        output_path=output_path,
                        progress_callback=progress_callback,
                        upper_percentage=upper_percentage,
                        lower_percentage=lower_percentage,
                        audio_path=tts_audio_path,
                    )

                    # Read the video file and encode as base64
                    with open(output_path, "rb") as f:
                        video_bytes = f.read()
                    generation_result["video_base64"] = base64.b64encode(video_bytes).decode("utf-8")
                    generation_result["success"] = True

                except Exception as e:
                    generation_result["error"] = str(e)
                finally:
                    generation_complete.set()

            # Start video generation in a separate thread
            gen_thread = threading.Thread(target=generate_in_thread, daemon=True)
            gen_thread.start()

            # Poll for progress updates while generation is running
            last_progress = -1
            while not generation_complete.is_set():
                current_progress = progress_state["progress"]
                current_status = progress_state["status"]

                if current_progress != last_progress:
                    async with self:
                        self.generation_progress = current_progress
                        self.generation_status = current_status
                    last_progress = current_progress

                await asyncio.sleep(0.1)  # Poll every 100ms

            # Clean up temporary files
            if os.path.exists(output_path):
                os.unlink(output_path)
            if tts_audio_path and os.path.exists(tts_audio_path):
                os.unlink(tts_audio_path)

            # Handle result
            if generation_result["success"]:
                async with self:
                    self.generation_progress = 100
                    self.generation_status = "Complete!"
                    self.video_data = generation_result["video_base64"]
                    self.video_ready = True
                    self.success_message = "Video generated successfully! Click download to save."
                    self.is_generating = False
            else:
                async with self:
                    self.error_message = generation_result["error"] or "Video generation failed"
                    self.is_generating = False
                    self.generation_progress = 0
                    self.generation_status = ""

        except (VideoGeneratorError, ImageProcessingError) as e:
            async with self:
                self.error_message = str(e)
                self.is_generating = False
                self.generation_progress = 0
                self.generation_status = ""
        except Exception as e:
            async with self:
                self.error_message = f"An unexpected error occurred: {str(e)}"
                self.is_generating = False
                self.generation_progress = 0
                self.generation_status = ""

    @rx.event
    def download_video(self):
        """Trigger video download in browser."""
        if not self.video_data:
            return

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"would_you_rather_{timestamp}.mp4"

        # Decode base64 back to bytes for download
        video_bytes = base64.b64decode(self.video_data)

        # Return download action with raw bytes
        return rx.download(
            data=video_bytes,
            filename=filename,
        )

    @rx.event
    def clear_video(self):
        """Clear the generated video."""
        self.video_data = None
        self.video_ready = False
        self.success_message = ""
        self.generation_progress = 0
        self.generation_status = ""

    @rx.var
    def can_generate(self) -> bool:
        """Check if the generate button should be enabled."""
        return (
            bool(self.upper_text.strip())
            and bool(self.lower_text.strip())
            and bool(self.upper_image_data)
            and bool(self.lower_image_data)
            and not self.is_generating
        )

    @rx.var
    def has_upper_image(self) -> bool:
        """Check if upper image is uploaded."""
        return bool(self.upper_image_data)

    @rx.var
    def has_lower_image(self) -> bool:
        """Check if lower image is uploaded."""
        return bool(self.lower_image_data)

    @rx.var
    def upper_image_preview(self) -> str:
        """Get the upper image preview URL."""
        if self.upper_image_data:
            return f"data:image/png;base64,{self.upper_image_data}"
        return ""

    @rx.var
    def lower_image_preview(self) -> str:
        """Get the lower image preview URL."""
        if self.lower_image_data:
            return f"data:image/png;base64,{self.lower_image_data}"
        return ""


def input_field(
    label: str,
    placeholder: str,
    value: rx.Var,
    on_change: rx.EventHandler,
) -> rx.Component:
    """Create a styled input field with text area for better readability."""
    return rx.box(
        rx.text(
            label,
            font_weight="bold",
            font_size="1.1em",
            color=COLORS["white"],
            margin_bottom="0.5em",
        ),
        rx.text_area(
            placeholder=placeholder,
            value=value,
            on_change=on_change,
            width="100%",
            min_height="100px",
            padding="1em",
            border=f"2px solid {COLORS['white']}",
            border_radius="8px",
            font_size="1em",
            line_height="1.5",
            background="rgba(255, 255, 255, 0.1)",
            color=COLORS["white"],
            resize="vertical",
            _placeholder={"color": "rgba(255, 255, 255, 0.6)"},
            _focus={
                "border_color": COLORS["white"],
                "box_shadow": "0 0 0 3px rgba(255, 255, 255, 0.3)",
                "outline": "none",
            },
        ),
        width="100%",
        margin_bottom="1em",
    )


def image_upload_area(
    upload_id: str,
    label: str,
    has_image: rx.Var,
    image_preview: rx.Var,
    image_name: rx.Var,
    on_upload: rx.EventHandler,
    on_clear: rx.EventHandler,
    is_uploading: rx.Var,
) -> rx.Component:
    """Create an image upload area with preview."""
    return rx.box(
        rx.text(
            label,
            font_weight="bold",
            font_size="1.1em",
            color=COLORS["white"],
            margin_bottom="0.5em",
        ),
        rx.cond(
            has_image,
            # Show preview when image is uploaded
            rx.box(
                rx.image(
                    src=image_preview,
                    max_height="150px",
                    max_width="100%",
                    object_fit="contain",
                    border_radius="8px",
                ),
                rx.hstack(
                    rx.text(
                        image_name,
                        color=COLORS["white"],
                        font_size="0.9em",
                        overflow="hidden",
                        text_overflow="ellipsis",
                        white_space="nowrap",
                        flex="1",
                    ),
                    rx.button(
                        rx.icon("x", size=16),
                        on_click=on_clear,
                        background="rgba(255, 255, 255, 0.2)",
                        color=COLORS["white"],
                        padding="0.3em 0.5em",
                        border_radius="4px",
                        cursor="pointer",
                        _hover={"background": "rgba(255, 255, 255, 0.3)"},
                    ),
                    width="100%",
                    margin_top="0.5em",
                    align_items="center",
                    gap="0.5em",
                ),
                padding="1em",
                border=f"2px solid {COLORS['white']}",
                border_radius="8px",
                background="rgba(255, 255, 255, 0.1)",
            ),
            # Show upload area when no image
            rx.upload(
                rx.box(
                    rx.cond(
                        is_uploading,
                        rx.vstack(
                            rx.spinner(size="2"),
                            rx.text(
                                "Uploading...",
                                color=COLORS["white"],
                                font_size="0.9em",
                            ),
                            spacing="2",
                            align_items="center",
                        ),
                        rx.vstack(
                            rx.icon("upload", size=32, color=COLORS["white"]),
                            rx.text(
                                "Click or drag image here",
                                color=COLORS["white"],
                                font_size="0.95em",
                                text_align="center",
                            ),
                            rx.text(
                                "JPG, PNG, GIF, WebP",
                                color="rgba(255, 255, 255, 0.6)",
                                font_size="0.8em",
                            ),
                            spacing="2",
                            align_items="center",
                        ),
                    ),
                    padding="2em",
                    border=f"2px dashed {COLORS['white']}",
                    border_radius="8px",
                    background="rgba(255, 255, 255, 0.05)",
                    cursor="pointer",
                    _hover={"background": "rgba(255, 255, 255, 0.1)"},
                    width="100%",
                    display="flex",
                    justify_content="center",
                    align_items="center",
                    min_height="120px",
                ),
                id=upload_id,
                accept={
                    "image/png": [".png"],
                    "image/jpeg": [".jpg", ".jpeg"],
                    "image/gif": [".gif"],
                    "image/webp": [".webp"],
                    "image/bmp": [".bmp"],
                },
                max_files=1,
                on_drop=on_upload,
                border="none",
                padding="0",
            ),
        ),
        width="100%",
        margin_bottom="1em",
    )


def option_section(
    title: str,
    text_label: str,
    text_placeholder: str,
    text_value: rx.Var,
    text_on_change: rx.EventHandler,
    upload_id: str,
    image_label: str,
    has_image: rx.Var,
    image_preview: rx.Var,
    image_name: rx.Var,
    on_upload: rx.EventHandler,
    on_clear: rx.EventHandler,
    is_uploading: rx.Var,
    color: str,
) -> rx.Component:
    """Create a section for one 'Would You Rather' option."""
    return rx.box(
        rx.heading(
            title,
            size="5",
            color=COLORS["white"],
            margin_bottom="1em",
            text_align="center",
        ),
        input_field(
            label=text_label,
            placeholder=text_placeholder,
            value=text_value,
            on_change=text_on_change,
        ),
        image_upload_area(
            upload_id=upload_id,
            label=image_label,
            has_image=has_image,
            image_preview=image_preview,
            image_name=image_name,
            on_upload=on_upload,
            on_clear=on_clear,
            is_uploading=is_uploading,
        ),
        background=color,
        padding="2em",
        border_radius="12px",
        width="100%",
    )


def or_divider() -> rx.Component:
    """Create the 'OR' divider matching the video style."""
    return rx.center(
        rx.box(
            rx.text(
                "OR",
                color=COLORS["white"],
                font_weight="bold",
                font_size="1.5em",
            ),
            background=COLORS["black"],
            width="4em",
            height="4em",
            border_radius="50%",
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        width="100%",
        margin_y="-1em",
        position="relative",
        z_index="10",
    )


def status_messages() -> rx.Component:
    """Create status message displays."""
    return rx.fragment(
        rx.cond(
            State.error_message != "",
            rx.box(
                rx.hstack(
                    rx.icon("alert-circle", size=20),
                    rx.text(State.error_message),
                    spacing="2",
                    align_items="center",
                ),
                color=COLORS["white"],
                background="#dc3545",
                padding="1em",
                border_radius="8px",
                width="100%",
                margin_bottom="1em",
            ),
        ),
        rx.cond(
            State.success_message != "",
            rx.box(
                rx.hstack(
                    rx.icon("check-circle", size=20),
                    rx.text(State.success_message),
                    spacing="2",
                    align_items="center",
                ),
                color=COLORS["white"],
                background="#28a745",
                padding="1em",
                border_radius="8px",
                width="100%",
                margin_bottom="1em",
            ),
        ),
    )


def download_button() -> rx.Component:
    """Create the download button for generated videos."""
    return rx.cond(
        State.video_ready,
        rx.hstack(
            rx.button(
                rx.icon("download", size=20),
                rx.text("Download Video", margin_left="0.5em"),
                on_click=State.download_video,
                background=COLORS["black"],
                color=COLORS["white"],
                padding="1em 2em",
                border_radius="8px",
                font_size="1.1em",
                cursor="pointer",
                display="flex",
                align_items="center",
                _hover={"opacity": "0.9"},
            ),
            rx.button(
                rx.icon("x", size=20),
                on_click=State.clear_video,
                background="transparent",
                color=COLORS["black"],
                padding="0.5em",
                border_radius="8px",
                cursor="pointer",
                _hover={"background": "rgba(0, 0, 0, 0.1)"},
            ),
            spacing="2",
            align_items="center",
        ),
    )


def generate_button() -> rx.Component:
    """Create the generate video button."""
    return rx.button(
        rx.cond(
            State.is_generating,
            rx.fragment(
                rx.spinner(size="1"),
                rx.text("Generating...", margin_left="0.5em"),
            ),
            rx.fragment(
                rx.icon("video", size=20),
                rx.text("Generate Video", margin_left="0.5em"),
            ),
        ),
        on_click=State.generate_video,
        disabled=~State.can_generate,
        background=rx.cond(
            State.can_generate,
            COLORS["black"],
            "#666666",
        ),
        color=COLORS["white"],
        padding="1em 2em",
        border_radius="8px",
        font_size="1.1em",
        cursor=rx.cond(State.can_generate, "pointer", "not-allowed"),
        width="100%",
        display="flex",
        align_items="center",
        justify_content="center",
        _hover=rx.cond(
            State.can_generate,
            {"opacity": "0.9"},
            {},
        ),
    )


def progress_bar() -> rx.Component:
    """Create a progress bar for video generation."""
    return rx.cond(
        State.is_generating,
        rx.box(
            rx.vstack(
                rx.text(
                    State.generation_status,
                    color=COLORS["white"],
                    font_size="0.95em",
                    margin_bottom="0.5em",
                ),
                rx.box(
                    rx.box(
                        width=rx.cond(
                            State.generation_progress > 0,
                            f"{State.generation_progress}%",
                            "0%",
                        ),
                        height="100%",
                        background=f"linear-gradient(90deg, {COLORS['red']}, {COLORS['blue']})",
                        border_radius="4px",
                        transition="width 0.3s ease-in-out",
                    ),
                    width="100%",
                    height="12px",
                    background="rgba(255, 255, 255, 0.2)",
                    border_radius="4px",
                    overflow="hidden",
                ),
                rx.text(
                    f"{State.generation_progress}%",
                    color=COLORS["off_white"],
                    font_size="0.85em",
                    margin_top="0.25em",
                ),
                width="100%",
                align_items="center",
            ),
            width="100%",
            max_width="500px",
            margin_top="1em",
        ),
    )


def or_divider_horizontal() -> rx.Component:
    """Create a horizontal 'OR' divider for landscape/desktop mode."""
    return rx.center(
        rx.box(
            rx.text(
                "OR",
                color=COLORS["white"],
                font_weight="bold",
                font_size="1.5em",
            ),
            background=COLORS["black"],
            width="4em",
            height="4em",
            border_radius="50%",
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        height="100%",
        display="flex",
        align_items="center",
    )


def percentage_settings() -> rx.Component:
    """Create the percentage settings section."""
    return rx.box(
        # Show Percentages Toggle
        rx.hstack(
            rx.switch(
                checked=State.show_percentages,
                on_change=State.toggle_show_percentages,
            ),
            rx.text(
                "Show result percentages",
                color=COLORS["white"],
                font_size="1em",
            ),
            spacing="3",
            align_items="center",
        ),
        # Auto-generate toggle (only visible when show_percentages is enabled)
        rx.cond(
            State.show_percentages,
            rx.box(
                rx.hstack(
                    rx.switch(
                        checked=State.auto_percentages,
                        on_change=State.toggle_auto_percentages,
                    ),
                    rx.text(
                        "Auto-generate percentages",
                        color=COLORS["white"],
                        font_size="0.95em",
                    ),
                    spacing="3",
                    align_items="center",
                ),
                margin_top="0.75em",
                margin_left="1em",
            ),
        ),
        # Manual percentage inputs (only visible when show_percentages is enabled and auto is disabled)
        rx.cond(
            State.show_percentages & ~State.auto_percentages,
            rx.box(
                rx.hstack(
                    rx.box(
                        rx.text(
                            "Option 1 %",
                            color=COLORS["white"],
                            font_size="0.9em",
                            margin_bottom="0.25em",
                        ),
                        rx.input(
                            placeholder="e.g., 65",
                            value=State.upper_percentage,
                            on_change=State.set_upper_percentage,
                            width="100%",
                            padding="0.5em",
                            border=f"2px solid {COLORS['red']}",
                            border_radius="6px",
                            background="rgba(255, 255, 255, 0.1)",
                            color=COLORS["white"],
                            _placeholder={"color": "rgba(255, 255, 255, 0.5)"},
                        ),
                        flex="1",
                    ),
                    rx.box(
                        rx.text(
                            "Option 2 %",
                            color=COLORS["white"],
                            font_size="0.9em",
                            margin_bottom="0.25em",
                        ),
                        rx.input(
                            placeholder="e.g., 35",
                            value=State.lower_percentage,
                            on_change=State.set_lower_percentage,
                            width="100%",
                            padding="0.5em",
                            border=f"2px solid {COLORS['blue']}",
                            border_radius="6px",
                            background="rgba(255, 255, 255, 0.1)",
                            color=COLORS["white"],
                            _placeholder={"color": "rgba(255, 255, 255, 0.5)"},
                        ),
                        flex="1",
                    ),
                    spacing="4",
                    width="100%",
                ),
                rx.text(
                    "Percentages must add up to 100%",
                    color="rgba(255, 255, 255, 0.6)",
                    font_size="0.8em",
                    margin_top="0.5em",
                ),
                margin_top="0.75em",
                margin_left="1em",
            ),
        ),
        width="100%",
    )


def tts_settings() -> rx.Component:
    """Create the TTS settings section."""
    return rx.box(
        rx.hstack(
            rx.switch(
                checked=State.enable_tts,
                on_change=State.toggle_tts,
            ),
            rx.text(
                "Enable voice narration",
                color=COLORS["white"],
                font_size="1em",
            ),
            spacing="3",
            align_items="center",
        ),
        rx.cond(
            State.enable_tts,
            rx.box(
                rx.text(
                    'Reads: "Would you rather [Option 1] or [Option 2]?"',
                    color="rgba(255, 255, 255, 0.6)",
                    font_size="0.85em",
                    margin_bottom="0.75em",
                ),
                rx.box(
                    rx.text(
                        "Voice",
                        color=COLORS["white"],
                        font_size="0.9em",
                        margin_bottom="0.25em",
                    ),
                    rx.select(
                        [info["description"] for info in AVAILABLE_VOICES.values()],
                        value=State.selected_voice_description,
                        on_change=State.set_voice_by_description,
                        placeholder="Select a voice",
                        width="100%",
                    ),
                    width="100%",
                    max_width="300px",
                ),
                margin_top="0.5em",
                margin_left="3em",
            ),
        ),
        width="100%",
    )


def video_settings() -> rx.Component:
    """Create the video settings section with percentage and TTS options."""
    return rx.box(
        rx.text(
            "Video Settings",
            font_weight="bold",
            font_size="1.1em",
            color=COLORS["white"],
            margin_bottom="1em",
        ),
        rx.vstack(
            percentage_settings(),
            tts_settings(),
            spacing="4",
            width="100%",
            align_items="start",
        ),
        background="rgba(0, 0, 0, 0.3)",
        padding="1.5em",
        border_radius="12px",
        width="100%",
        margin_top="1.5em",
    )


def options_container() -> rx.Component:
    """Create a responsive container for the two option sections.
    
    Side-by-side on landscape/desktop screens, stacked on portrait/mobile.
    OR divider is always visible between the two options.
    """
    return rx.box(
        # Option 1 (Red/Upper)
        rx.box(
            option_section(
                title="Option 1",
                text_label="Display Text",
                text_placeholder="e.g., Be a chef",
                text_value=State.upper_text,
                text_on_change=State.set_upper_text,
                upload_id="upper_image_upload",
                image_label="Image",
                has_image=State.has_upper_image,
                image_preview=State.upper_image_preview,
                image_name=State.upper_image_name,
                on_upload=State.handle_upper_image_upload,
                on_clear=State.clear_upper_image,
                is_uploading=State.is_uploading_upper,
                color=COLORS["red"],
            ),
            flex=["1 1 100%", "1 1 100%", "1 1 0%", "1 1 0%", "1 1 0%"],
        ),
        # OR Divider - vertical style for portrait, horizontal style for landscape
        rx.box(
            or_divider(),
            display=["block", "block", "none", "none", "none"],
            width="100%",
        ),
        rx.box(
            or_divider_horizontal(),
            display=["none", "none", "flex", "flex", "flex"],
            flex_shrink="0",
            padding_x="0.5em",
        ),
        # Option 2 (Blue/Lower)
        rx.box(
            option_section(
                title="Option 2",
                text_label="Display Text",
                text_placeholder="e.g., Be a doctor",
                text_value=State.lower_text,
                text_on_change=State.set_lower_text,
                upload_id="lower_image_upload",
                image_label="Image",
                has_image=State.has_lower_image,
                image_preview=State.lower_image_preview,
                image_name=State.lower_image_name,
                on_upload=State.handle_lower_image_upload,
                on_clear=State.clear_lower_image,
                is_uploading=State.is_uploading_lower,
                color=COLORS["blue"],
            ),
            flex=["1 1 100%", "1 1 100%", "1 1 0%", "1 1 0%", "1 1 0%"],
        ),
        display="flex",
        flex_direction=["column", "column", "row", "row", "row"],
        flex_wrap=["wrap", "wrap", "nowrap", "nowrap", "nowrap"],
        justify_content="center",
        align_items=["stretch", "stretch", "stretch", "stretch", "stretch"],
        gap=["1.5em", "1.5em", "1em", "1em", "1em"],
        width="100%",
    )


def index() -> rx.Component:
    """Main page component."""
    return rx.box(
        rx.center(
            rx.vstack(
                # Header
                rx.heading(
                    "Would You Rather?",
                    size="8",
                    color=COLORS["white"],
                    text_align="center",
                    margin_bottom="0.5em",
                ),
                rx.text(
                    "Video Generator",
                    font_size="1.3em",
                    color=COLORS["off_white"],
                    margin_bottom="2em",
                ),
                # Status messages
                status_messages(),
                # Options container (responsive layout)
                options_container(),
                # Video settings (percentage and TTS options)
                rx.box(
                    video_settings(),
                    width="100%",
                    max_width=["500px", "500px", "900px", "900px", "900px"],
                ),
                # Generate Button
                rx.box(
                    generate_button(),
                    width="100%",
                    max_width="500px",
                    margin_top="2em",
                ),
                # Progress Bar
                progress_bar(),
                # Download Button
                rx.center(
                    download_button(),
                    width="100%",
                    margin_top="1em",
                ),
                width="100%",
                max_width=["500px", "500px", "900px", "900px", "900px"],
                padding="2em",
                spacing="0",
                align_items="center",
            ),
            width="100%",
            min_height="100vh",
            padding_y="2em",
        ),
        # Floating support button
        floating_support_button(
            icon_name="coffee",
            text="Buy me a coffee",
            href="https://buymeacoffee.com/denverw",  # Placeholder URL - update when actual link is available
        ),
        background=COLORS["background_gray"],
        min_height="100vh",
    )


# Create the Reflex app
app = rx.App(
    style={
        "font_family": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    },
)

app.add_page(index, title="Would You Rather? Video Generator")
