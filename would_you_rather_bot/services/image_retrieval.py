"""Image retrieval service using DuckDuckGo image search."""

from io import BytesIO
from typing import Optional

import requests
from duckduckgo_search import DDGS
from PIL import Image


class ImageRetriever:
    """Handles image retrieval from web searches."""

    @staticmethod
    def get_image(search_term: str) -> Optional[Image.Image]:
        """Search for and retrieve an image based on a search term.

        Args:
            search_term: The term to search for images.

        Returns:
            A PIL Image object if successful, None otherwise.

        Raises:
            ImageRetrievalError: If the image cannot be retrieved.
        """
        try:
            # Perform image search with DuckDuckGo
            results = DDGS().images(
                keywords=f"cartoon {search_term} without watermark",
                safesearch="on",
                max_results=5,
            )

            # Try to get an image from the results
            for result in results:
                image_url = result.get("image")
                if not image_url:
                    continue

                try:
                    # Download the image
                    response = requests.get(image_url, timeout=10)
                    response.raise_for_status()

                    # Open and return the image
                    image_data = BytesIO(response.content)
                    image = Image.open(image_data)

                    # Convert to RGB if necessary (for consistency)
                    if image.mode in ("RGBA", "P"):
                        image = image.convert("RGB")

                    return image

                except (requests.RequestException, IOError):
                    # Try next result if this one fails
                    continue

            raise ImageRetrievalError(f"No valid images found for '{search_term}'")

        except Exception as e:
            raise ImageRetrievalError(f"Failed to retrieve image for '{search_term}': {str(e)}")


class ImageRetrievalError(Exception):
    """Exception raised when image retrieval fails."""

    pass
