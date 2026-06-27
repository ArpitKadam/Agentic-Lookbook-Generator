import os
import sys
import hashlib
from pathlib import Path
from typing import List
import asyncio
import httpx
from pydantic import BaseModel, HttpUrl
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from src.pipeline.pipeline import build_pipeline
from src.state.state import LookbookState
from src.logger import logger
from src.exception import CustomException

load_dotenv()

os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["LANGSMITH_TRACING"] = "true"


# ==========================================================
# APP INITIALIZATION
# ==========================================================

app = FastAPI(
    title="Agentic Lookbook Generator API",
    description="AI-native editorial lookbook generation platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("Loading LangGraph Pipeline...")
graph = build_pipeline()
logger.info("Pipeline ready.")


UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================================
# HEALTH CHECK
# ==========================================================

@app.get("/health")
async def health_check():

    return {
        "status": "healthy",
        "service": "Agentic Lookbook Generator API"
    }


# ==========================================================
# RUN USING IMAGES ALREADY PRESENT INSIDE data/
# ==========================================================

@app.post("/generate-from-data")
async def generate_from_data(
    theme_prompt: str
):

    try:
        image_paths = []

        for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:

            image_paths.extend(
                [str(p) for p in Path("data").glob(ext)]
            )

        if not image_paths:
            raise CustomException("No images found inside data directory.", sys)

        logger.info(
            f"Running pipeline on {len(image_paths)} images."
        )

        initial_state: LookbookState = {
            "image_paths": image_paths,
            "theme_prompt": theme_prompt,
            "image_analyses": [],
            "mood_clusters": None,
            "draft_cards": None,
            "lookbook": None,
            "token_usages": []
        }

        result = graph.invoke(initial_state)

        total_tokens = sum(
            usage.total_tokens
            for usage in result["token_usages"]
        )

        return {
            "lookbook": result["lookbook"].model_dump(),
            "token_usage": [
                usage.model_dump()
                for usage in result["token_usages"]
            ],
            "total_tokens": total_tokens
        }

    except Exception as e:
        logger.exception(e)
        raise CustomException("Failed to generate lookbook.", sys)


# ==========================================================
# UPLOAD IMAGES LINKS + RUN PIPELINE
# ==========================================================

class Request(BaseModel):
    theme_prompt: str
    image_urls: list[HttpUrl]


async def download_image(client: httpx.AsyncClient, url: str) -> str:
    """Downloads an image from a URL and saves it to the upload directory with a cache hit check."""
    try:
        url_path = Path(url.split("?")[0])
        extension = url_path.suffix or ".jpg"
        if extension.lower() not in [".jpg", ".jpeg", ".png", ".webp"]:
            extension = ".jpg"

        url_hash = hashlib.md5(str(url).encode("utf-8")).hexdigest()
        unique_name = f"{url_hash}{extension}"
        save_path = UPLOAD_DIR / unique_name

        if save_path.exists():
            logger.info(f"Cache hit! Skipping download for: {url}")
            return str(save_path)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        response = await client.get(str(url), headers=headers, timeout=15.0)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

        logger.info(f"Successfully downloaded: {url}")
        return str(save_path)

    except Exception as e:
        logger.error(f"Failed to download image from {url}: {e}")
        raise e

@app.post("/generate")
async def generate_lookbook(request: Request):
    try:
        if not request.image_urls:
            raise CustomException("No image URLs provided.", sys)

        logger.info(request.image_urls)
        logger.info(request.theme_prompt)

        logger.info(f"Downloading {len(request.image_urls)} images...")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            tasks = [download_image(client, str(url)) for url in request.image_urls]
            image_paths = await asyncio.gather(*tasks)

        logger.info(f"Successfully downloaded and saved {len(image_paths)} images.")

        initial_state: LookbookState = {
            "image_paths": image_paths,
            "theme_prompt": request.theme_prompt,
            "image_analyses": [],
            "mood_clusters": None,
            "draft_cards": None,
            "lookbook": None,
            "token_usages": []
        }

        result = graph.invoke(initial_state)

        total_tokens = sum(
            usage.total_tokens
            for usage in result["token_usages"]
        )

        return {
            "lookbook": result["lookbook"].model_dump(),
            "token_usage": [
                usage.model_dump()
                for usage in result["token_usages"]
            ],
            "total_tokens": total_tokens
        }

    except Exception as e:
        logger.exception(e)
        raise CustomException("Failed to generate lookbook from URLs.", sys)