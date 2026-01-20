"""Would You Rather Bot - Main Reflex Application."""

import os
import uuid
from datetime import datetime
from pathlib import Path

import reflex as rx

from .services.video_generator import VideoGenerator, VideoGeneratorError


# Color constants matching the video style
COLORS = {
    "red": "#ED1C24",  # Upper section red
    "blue": "#3D9AE8",  # Lower section blue
    "black": "#000000",
    "white": "#FFFFFF",
    "dark_gray": "#1a1a1a",
    "light_gray": "#f5f5f5",
}


class State(rx.State):
    """Application state for the video generator."""

    # Form inputs
    upper_text: str = ""
    lower_text: str = ""
    upper_image_search: str = ""
    lower_image_search: str = ""

    # Status tracking
    is_generating: bool = False
    error_message: str = ""
    success_message: str = ""
    video_filename: str = ""

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
    def set_upper_image_search(self, value: str):
        """Set the upper image search term."""
        self.upper_image_search = value
        self.clear_messages()

    @rx.event
    def set_lower_image_search(self, value: str):
        """Set the lower image search term."""
        self.lower_image_search = value
        self.clear_messages()

    def _validate_inputs(self) -> bool:
        """Validate all form inputs.

        Returns:
            True if all inputs are valid, False otherwise.
        """
        if not self.upper_text.strip():
            self.error_message = "Please enter text for the first option."
            return False
        if not self.lower_text.strip():
            self.error_message = "Please enter text for the second option."
            return False
        if not self.upper_image_search.strip():
            self.error_message = "Please enter an image search term for the first option."
            return False
        if not self.lower_image_search.strip():
            self.error_message = "Please enter an image search term for the second option."
            return False
        return True

    @rx.event(background=True)
    async def generate_video(self):
        """Generate the video based on form inputs."""
        async with self:
            self.error_message = ""
            self.success_message = ""
            self.video_filename = ""

            # Validate inputs
            if not self._validate_inputs():
                return

            self.is_generating = True

        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"would_you_rather_{timestamp}_{unique_id}.mp4"

            # Get output path
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            output_path = str(output_dir / filename)

            # Generate the video
            generator = VideoGenerator()
            generator.generate(
                upper_text=self.upper_text.strip(),
                lower_text=self.lower_text.strip(),
                upper_image_search=self.upper_image_search.strip(),
                lower_image_search=self.lower_image_search.strip(),
                output_path=output_path,
            )

            async with self:
                self.success_message = f"Video generated successfully!"
                self.video_filename = filename
                self.is_generating = False

        except VideoGeneratorError as e:
            async with self:
                self.error_message = str(e)
                self.is_generating = False
        except Exception as e:
            async with self:
                self.error_message = f"An unexpected error occurred: {str(e)}"
                self.is_generating = False

    @rx.var
    def can_generate(self) -> bool:
        """Check if the generate button should be enabled."""
        return (
            bool(self.upper_text.strip())
            and bool(self.lower_text.strip())
            and bool(self.upper_image_search.strip())
            and bool(self.lower_image_search.strip())
            and not self.is_generating
        )

    @rx.var
    def video_download_url(self) -> str:
        """Get the download URL for the generated video."""
        if self.video_filename:
            return f"/output/{self.video_filename}"
        return ""


def input_field(
    label: str,
    placeholder: str,
    value: rx.Var,
    on_change: rx.EventHandler,
    color: str,
) -> rx.Component:
    """Create a styled input field.

    Args:
        label: The label text.
        placeholder: Placeholder text for the input.
        value: The state variable for the value.
        on_change: Event handler for value changes.
        color: The accent color for the field.

    Returns:
        A styled input component.
    """
    return rx.box(
        rx.text(
            label,
            font_weight="bold",
            font_size="1.1em",
            color=color,
            margin_bottom="0.5em",
        ),
        rx.input(
            placeholder=placeholder,
            value=value,
            on_change=on_change,
            width="100%",
            padding="0.75em",
            border=f"2px solid {color}",
            border_radius="8px",
            font_size="1em",
            _focus={
                "border_color": color,
                "box_shadow": f"0 0 0 3px {color}33",
            },
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
    image_label: str,
    image_placeholder: str,
    image_value: rx.Var,
    image_on_change: rx.EventHandler,
    color: str,
) -> rx.Component:
    """Create a section for one 'Would You Rather' option.

    Args:
        title: Section title.
        text_label: Label for text input.
        text_placeholder: Placeholder for text input.
        text_value: State variable for text.
        text_on_change: Handler for text changes.
        image_label: Label for image search input.
        image_placeholder: Placeholder for image search.
        image_value: State variable for image search.
        image_on_change: Handler for image search changes.
        color: Accent color for the section.

    Returns:
        A styled section component.
    """
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
            color=COLORS["white"],
        ),
        input_field(
            label=image_label,
            placeholder=image_placeholder,
            value=image_value,
            on_change=image_on_change,
            color=COLORS["white"],
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
            padding="1em 1.5em",
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
                rx.text(
                    State.error_message,
                    color=COLORS["white"],
                ),
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
                rx.text(
                    State.success_message,
                    color=COLORS["white"],
                ),
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
        State.video_filename != "",
        rx.link(
            rx.button(
                rx.icon("download", size=20),
                rx.text("Download Video", margin_left="0.5em"),
                background=COLORS["black"],
                color=COLORS["white"],
                padding="1em 2em",
                border_radius="8px",
                font_size="1.1em",
                cursor="pointer",
                display="flex",
                align_items="center",
                _hover={
                    "opacity": "0.9",
                },
            ),
            href=State.video_download_url,
            is_external=True,
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


def index() -> rx.Component:
    """Main page component."""
    return rx.box(
        rx.center(
            rx.vstack(
                # Header
                rx.heading(
                    "Would You Rather?",
                    size="8",
                    color=COLORS["black"],
                    text_align="center",
                    margin_bottom="0.5em",
                ),
                rx.text(
                    "Video Generator",
                    font_size="1.3em",
                    color="#666666",
                    margin_bottom="2em",
                ),
                # Status messages
                status_messages(),
                # Option 1 (Red/Upper)
                option_section(
                    title="Option 1",
                    text_label="Display Text",
                    text_placeholder="e.g., Be a chef",
                    text_value=State.upper_text,
                    text_on_change=State.set_upper_text,
                    image_label="Image Search Term",
                    image_placeholder="e.g., Chef",
                    image_value=State.upper_image_search,
                    image_on_change=State.set_upper_image_search,
                    color=COLORS["red"],
                ),
                # OR Divider
                or_divider(),
                # Option 2 (Blue/Lower)
                option_section(
                    title="Option 2",
                    text_label="Display Text",
                    text_placeholder="e.g., Be a doctor",
                    text_value=State.lower_text,
                    text_on_change=State.set_lower_text,
                    image_label="Image Search Term",
                    image_placeholder="e.g., Doctor",
                    image_value=State.lower_image_search,
                    image_on_change=State.set_lower_image_search,
                    color=COLORS["blue"],
                ),
                # Generate Button
                rx.box(
                    generate_button(),
                    width="100%",
                    margin_top="2em",
                ),
                # Download Button
                rx.center(
                    download_button(),
                    width="100%",
                    margin_top="1em",
                ),
                width="100%",
                max_width="500px",
                padding="2em",
                spacing="0",
            ),
            width="100%",
            min_height="100vh",
            padding_y="2em",
        ),
        background=f"linear-gradient(180deg, {COLORS['red']}22 0%, {COLORS['white']} 30%, {COLORS['white']} 70%, {COLORS['blue']}22 100%)",
        min_height="100vh",
    )


# Create the Reflex app
app = rx.App(
    style={
        "font_family": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    },
    stylesheets=[],
)

app.add_page(index, title="Would You Rather? Video Generator")
