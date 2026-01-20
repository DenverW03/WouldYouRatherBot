"""Image retrieval service using DuckDuckGo image search."""

import random
import time
from io import BytesIO
from typing import Optional, List, Dict

import requests
from duckduckgo_search import DDGS
from PIL import Image


class ImageRetrievalError(Exception):
    """Exception raised when image retrieval fails."""

    pass


class ImageRetriever:
    """Handles image retrieval from web searches with rate limit handling."""

    # Realistic browser user agents to rotate through
    USER_AGENTS: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    ]

    # Retry configuration
    MAX_RETRIES: int = 3
    BASE_DELAY: float = 1.0  # Base delay in seconds
    MAX_DELAY: float = 10.0  # Maximum delay between retries
    JITTER_RANGE: tuple = (0.5, 1.5)  # Random multiplier range for delay

    @classmethod
    def _get_random_headers(cls) -> Dict[str, str]:
        """Generate realistic browser headers with a random user agent.

        Returns:
            Dictionary of HTTP headers.
        """
        return {
            "User-Agent": random.choice(cls.USER_AGENTS),
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "image",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "cross-site",
            "Referer": "https://duckduckgo.com/",
        }

    @classmethod
    def _calculate_backoff_delay(cls, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter.

        Args:
            attempt: The current attempt number (0-indexed).

        Returns:
            Delay in seconds.
        """
        # Exponential backoff: 1s, 2s, 4s, 8s, etc.
        delay = cls.BASE_DELAY * (2 ** attempt)
        # Cap at maximum delay
        delay = min(delay, cls.MAX_DELAY)
        # Add random jitter to prevent thundering herd
        jitter = random.uniform(*cls.JITTER_RANGE)
        return delay * jitter

    @classmethod
    def _download_image_with_retry(
        cls, 
        url: str, 
        session: requests.Session
    ) -> Optional[Image.Image]:
        """Download an image with retry logic for rate limiting.

        Args:
            url: The image URL to download.
            session: Requests session to use.

        Returns:
            PIL Image if successful, None otherwise.
        """
        last_error = None

        for attempt in range(cls.MAX_RETRIES):
            try:
                # Add small random delay before each request to avoid rate limits
                if attempt > 0:
                    delay = cls._calculate_backoff_delay(attempt)
                    time.sleep(delay)
                else:
                    # Small initial delay with jitter
                    time.sleep(random.uniform(0.2, 0.8))

                # Make request with fresh headers
                headers = cls._get_random_headers()
                response = session.get(url, headers=headers, timeout=15)

                # Handle rate limiting specifically
                if response.status_code == 403:
                    last_error = f"403 Forbidden (attempt {attempt + 1})"
                    continue
                elif response.status_code == 429:
                    last_error = f"429 Too Many Requests (attempt {attempt + 1})"
                    # Longer delay for explicit rate limiting
                    time.sleep(cls._calculate_backoff_delay(attempt + 1))
                    continue

                response.raise_for_status()

                # Verify it's actually an image
                content_type = response.headers.get("Content-Type", "")
                if not content_type.startswith("image/"):
                    last_error = f"Invalid content type: {content_type}"
                    continue

                # Open and validate the image
                image_data = BytesIO(response.content)
                image = Image.open(image_data)
                
                # Force load to verify image is valid
                image.load()

                # Convert to RGB if necessary (for consistency with video generation)
                if image.mode in ("RGBA", "P", "LA"):
                    # Create white background for transparent images
                    if image.mode in ("RGBA", "LA", "P"):
                        background = Image.new("RGB", image.size, (255, 255, 255))
                        if image.mode == "P":
                            image = image.convert("RGBA")
                        background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
                        image = background
                    else:
                        image = image.convert("RGB")
                elif image.mode != "RGB":
                    image = image.convert("RGB")

                return image

            except requests.exceptions.Timeout:
                last_error = f"Timeout (attempt {attempt + 1})"
                continue
            except requests.exceptions.RequestException as e:
                last_error = f"Request error: {str(e)} (attempt {attempt + 1})"
                continue
            except (IOError, OSError) as e:
                last_error = f"Image processing error: {str(e)} (attempt {attempt + 1})"
                continue

        return None

    @classmethod
    def get_image(cls, search_term: str) -> Image.Image:
        """Search for and retrieve an image based on a search term.

        Args:
            search_term: The term to search for images.

        Returns:
            A PIL Image object.

        Raises:
            ImageRetrievalError: If the image cannot be retrieved.
        """
        try:
            # Add small delay before search to avoid rate limiting the search API
            time.sleep(random.uniform(0.3, 0.7))

            # Perform image search with DuckDuckGo
            # Request more results to have fallbacks if some fail
            results = list(DDGS().images(
                keywords=f"cartoon {search_term} without watermark",
                safesearch="on",
                max_results=15,
            ))

            if not results:
                raise ImageRetrievalError(f"No search results found for '{search_term}'")

            # Shuffle results to distribute load across different sources
            random.shuffle(results)

            # Create a session for connection pooling
            session = requests.Session()
            
            # Track errors for debugging
            errors = []

            # Try to get an image from the results
            for result in results:
                image_url = result.get("image")
                if not image_url:
                    continue

                # Skip known problematic domains
                problematic_domains = ["pinterest.", "facebook.", "instagram."]
                if any(domain in image_url.lower() for domain in problematic_domains):
                    continue

                image = cls._download_image_with_retry(image_url, session)
                if image is not None:
                    session.close()
                    return image
                else:
                    errors.append(f"Failed to download: {image_url[:50]}...")

            session.close()
            
            error_summary = "; ".join(errors[:3])  # Show first 3 errors
            raise ImageRetrievalError(
                f"Could not retrieve any valid images for '{search_term}'. "
                f"Tried {len(results)} sources. Errors: {error_summary}"
            )

        except ImageRetrievalError:
            raise
        except Exception as e:
            raise ImageRetrievalError(
                f"Failed to retrieve image for '{search_term}': {str(e)}"
            )
