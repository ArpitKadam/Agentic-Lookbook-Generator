import base64
from pathlib import Path
import tiktoken
import re

ENCODER = tiktoken.get_encoding("o200k_base")

def encode_image(image_path: str | Path) -> str:
    """
    Encode image as base64 string for multimodal models.
    """

    image_path = Path(image_path)

    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")

    return encoded


def strip_markdown_fences(text: str) -> str:
    """
    Remove markdown code fences if the model accidentally returns them.
    """

    text = text.strip()

    text = re.sub(r"^```(?:json)?", "", text)
    text = re.sub(r"```$", "", text)

    return text.strip()


def count_tokens(text: str) -> int:
    return len(ENCODER.encode(text))