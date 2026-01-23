"""Floating button component for support/donation links."""

import reflex as rx


def floating_support_button(
    icon_name: str = "coffee",
    text: str = "Buy me a coffee",
    href: str = "#",
) -> rx.Component:
    """Create a floating support button in the bottom right corner.
    
    On mobile (portrait) screens, displays as a circular icon button.
    On landscape/desktop screens, displays as a rounded rectangle with text,
    taking up no more than 10% of the screen width.
    
    Args:
        icon_name: The Lucide icon name to display.
        text: The text to display alongside the icon (landscape only).
        href: The URL to link to when clicked.
    
    Returns:
        A responsive floating button component.
    """
    # Common styles for the button container
    container_style = {
        "position": "fixed",
        "bottom": "1.5em",
        "right": "1.5em",
        "z_index": "1000",
        "cursor": "pointer",
        "transition": "transform 0.2s ease, box-shadow 0.2s ease",
        "_hover": {
            "transform": "scale(1.05)",
            "box_shadow": "0 6px 20px rgba(0, 0, 0, 0.3)",
        },
    }
    
    # Coffee/support button color (warm amber/gold)
    button_color = "#FFDD00"
    text_color = "#000000"
    
    return rx.fragment(
        # Mobile version (portrait) - circular button
        rx.link(
            rx.box(
                rx.icon(icon_name, size=24, color=text_color),
                background=button_color,
                width="3.5em",
                height="3.5em",
                border_radius="50%",
                display="flex",
                align_items="center",
                justify_content="center",
                box_shadow="0 4px 12px rgba(0, 0, 0, 0.2)",
                **container_style,
            ),
            href=href,
            is_external=True,
            display=["flex", "flex", "none", "none", "none"],
            _hover={"text_decoration": "none"},
        ),
        # Desktop/landscape version - rounded rectangle
        rx.link(
            rx.box(
                rx.hstack(
                    rx.icon(icon_name, size=20, color=text_color),
                    rx.text(
                        text,
                        color=text_color,
                        font_weight="600",
                        font_size="0.9em",
                        white_space="nowrap",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                background=button_color,
                padding="0.75em 1.25em",
                border_radius="2em",
                box_shadow="0 4px 12px rgba(0, 0, 0, 0.2)",
                max_width="10vw",
                min_width="fit-content",
                **container_style,
            ),
            href=href,
            is_external=True,
            display=["none", "none", "flex", "flex", "flex"],
            _hover={"text_decoration": "none"},
        ),
    )
