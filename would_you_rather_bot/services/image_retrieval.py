"""Image handling service for processing uploaded images."""

import base64
from io import BytesIO
from pathlib import Path
from typing import Optional, Union

from PIL import Image


class ImageProcessingError(Exception):
    """Exception raised when image processing fails."""

    pass


class ImageProcessor:
    """Handles image processing for uploaded images."""

    # Supported image formats
    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    
    # Maximum image dimensions (will be resized if larger)
    MAX_DIMENSION = 2000

    @classmethod
    def process_uploaded_image(
        cls,
        image_data: Union[bytes, str],
        filename: Optional[str] = None,
    ) -> Image.Image:
        """Process an uploaded image from bytes or base64 string.

        Args:
            image_data: Raw image bytes or base64-encoded string.
            filename: Optional filename for format validation.

        Returns:
            A processed PIL Image object in RGB format.

        Raises:
            ImageProcessingError: If the image cannot be processed.
        """
        try:
            # Handle base64-encoded data
            if isinstance(image_data, str):
                # Remove data URL prefix if present (e.g., "data:image/png;base64,")
                if "," in image_data:
                    image_data = image_data.split(",", 1)[1]
                image_data = base64.b64decode(image_data)

            # Validate file extension if filename provided
            if filename:
                ext = Path(filename).suffix.lower()
                if ext and ext not in cls.SUPPORTED_FORMATS:
                    raise ImageProcessingError(
                        f"Unsupported image format: {ext}. "
                        f"Supported formats: {', '.join(cls.SUPPORTED_FORMATS)}"
                    )

            # Open the image
            image_buffer = BytesIO(image_data)
            image = Image.open(image_buffer)
            
            # Verify the image is valid by loading it
            image.load()

            # Convert to RGB format for video compatibility
            image = cls._convert_to_rgb(image)

            # Resize if too large
            image = cls._resize_if_needed(image)

            return image

        except ImageProcessingError:
            raise
        except Exception as e:
            raise ImageProcessingError(f"Failed to process image: {str(e)}")

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> Image.Image:
        """Load and process an image from a file path.

        Args:
            file_path: Path to the image file.

        Returns:
            A processed PIL Image object in RGB format.

        Raises:
            ImageProcessingError: If the image cannot be loaded or processed.
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise ImageProcessingError(f"Image file not found: {file_path}")

            ext = file_path.suffix.lower()
            if ext not in cls.SUPPORTED_FORMATS:
                raise ImageProcessingError(
                    f"Unsupported image format: {ext}. "
                    f"Supported formats: {', '.join(cls.SUPPORTED_FORMATS)}"
                )

            image = Image.open(file_path)
            image.load()

            # Convert to RGB format
            image = cls._convert_to_rgb(image)

            # Resize if too large
            image = cls._resize_if_needed(image)

            return image

        except ImageProcessingError:
            raise
        except Exception as e:
            raise ImageProcessingError(f"Failed to load image from {file_path}: {str(e)}")

    @classmethod
    def _convert_to_rgb(cls, image: Image.Image) -> Image.Image:
        """Convert an image to RGB format, handling transparency.

        Args:
            image: PIL Image in any format.

        Returns:
            PIL Image in RGB format.
        """
        if image.mode == "RGB":
            return image

        if image.mode in ("RGBA", "LA", "P"):
            # Handle transparency by compositing onto white background
            if image.mode == "P":
                image = image.convert("RGBA")
            
            # Create white background
            background = Image.new("RGB", image.size, (255, 255, 255))
            
            # Paste image onto background using alpha channel as mask
            if image.mode in ("RGBA", "LA"):
                # Split to get alpha channel
                if image.mode == "LA":
                    image = image.convert("RGBA")
                background.paste(image, mask=image.split()[3])
            else:
                background.paste(image)
            
            return background

        # For other modes (L, 1, etc.), just convert directly
        return image.convert("RGB")

    @classmethod
    def _resize_if_needed(cls, image: Image.Image) -> Image.Image:
        """Resize image if it exceeds maximum dimensions.

        Args:
            image: PIL Image to potentially resize.

        Returns:
            Original or resized PIL Image.
        """
        width, height = image.size
        
        if width <= cls.MAX_DIMENSION and height <= cls.MAX_DIMENSION:
            return image

        # Calculate new size maintaining aspect ratio
        if width > height:
            new_width = cls.MAX_DIMENSION
            new_height = int(height * (cls.MAX_DIMENSION / width))
        else:
            new_height = cls.MAX_DIMENSION
            new_width = int(width * (cls.MAX_DIMENSION / height))

        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    @classmethod
    def create_placeholder(
        cls,
        width: int = 500,
        height: int = 500,
        color: tuple = (200, 200, 200),
        text: Optional[str] = None,
    ) -> Image.Image:
        """Create a placeholder image.

        Args:
            width: Image width in pixels.
            height: Image height in pixels.
            color: RGB tuple for background color.
            text: Optional text to display on the placeholder.

        Returns:
            A placeholder PIL Image.
        """
        image = Image.new("RGB", (width, height), color)
        
        # Note: Text rendering would require PIL's ImageDraw and a font
        # Keeping it simple for now with just a colored rectangle
        
        return image
