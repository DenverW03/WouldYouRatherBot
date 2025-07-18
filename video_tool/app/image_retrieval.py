from ddgs import DDGS
from PIL import Image
from io import BytesIO
import requests

def get_image(search_term) -> Image:
    # Get image search result
    res = DDGS().images(
        query="cartoon " + search_term,
        safesearch="on",
        page=1,
    )
    imageUrl = res[0].get("image")

    # Retrieving the image
    imageData = requests.get(imageUrl).content
    imageFile = BytesIO(imageData)

    return Image.open(imageFile)