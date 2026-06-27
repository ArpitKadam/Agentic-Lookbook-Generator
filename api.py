import os
import sys
import hashlib
import base64
import re
from pathlib import Path
import asyncio
import httpx
from pydantic import BaseModel, HttpUrl
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from src.pipeline.pipeline import build_pipeline
from src.state.state import LookbookState
from src.logger import logger
from src.exception import CustomException

load_dotenv()

os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["LANGSMITH_TRACING"] = "true"

app = FastAPI(
    title="Agentic Lookbook Generator API",
    description="AI-native editorial lookbook generation platform",
    version="1.0.0"
)

Path("static").mkdir(parents=True, exist_ok=True)
Path("templates").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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

    
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Agentic Lookbook Generator API"
    }


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


class LookbookRequest(BaseModel):
    theme_prompt: str
    image_urls: list[str]


async def process_image_source(client: httpx.AsyncClient, image_source: str) -> str:
    """
    Processes an image source - either a base64 data URL or an HTTP(S) URL.
    Returns the path to the saved image file.
    """
    try:
        # Check if it's a base64 data URL
        if image_source.startswith("data:image/"):
            return await handle_base64_image(image_source)
        else:
            # Regular HTTPS URL
            return await download_image(client, image_source)
    except Exception as e:
        logger.error(f"Failed to process image source: {e}")
        raise e


async def handle_base64_image(data_url: str) -> str:
    """Converts a base64 data URL to an image file and saves it directly to uploads."""
    try:
        # Extract the image format and base64 data - handle with or without charset
        match = re.match(r"data:image/([a-zA-Z0-9]+)(?:;[^,]*)?;base64,(.+)$", data_url)
        if not match:
            logger.error(f"Failed to parse base64 URL: {data_url[:100]}...")
            raise ValueError("Invalid base64 data URL format")
        
        image_format, base64_data = match.groups()
        logger.info(f"Parsing base64 image - Format: {image_format}, Data length: {len(base64_data)}")
        
        # Map common formats to extensions
        format_map = {
            "jpeg": ".jpg",
            "jpg": ".jpg",
            "png": ".png",
            "gif": ".gif",
            "webp": ".webp",
            "svg+xml": ".svg"
        }
        extension = format_map.get(image_format.lower(), ".jpg")
        
        # Decode base64 data
        try:
            image_bytes = base64.b64decode(base64_data)
            logger.info(f"Decoded base64 to {len(image_bytes)} bytes")
        except Exception as decode_err:
            logger.error(f"Failed to decode base64: {decode_err}")
            raise ValueError(f"Failed to decode base64 image: {decode_err}")
        
        # Create a hash of the image bytes for the filename
        data_hash = hashlib.md5(image_bytes).hexdigest()
        unique_name = f"uploaded_{data_hash}{extension}"
        save_path = UPLOAD_DIR / unique_name
        
        # Check if already exists
        if save_path.exists():
            logger.info(f"Cache hit! Image already saved: {unique_name}")
            return str(save_path)
        
        # Ensure upload directory exists
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Save the image directly
        with open(save_path, "wb") as f:
            f.write(image_bytes)
        
        logger.info(f"Successfully saved base64 image to: {save_path}")
        return str(save_path)
    
    except Exception as e:
        logger.error(f"Failed to handle base64 image: {e}")
        raise e


async def download_image(client: httpx.AsyncClient, url: str) -> str:
    """Downloads an image from a URL and saves it to the upload directory with a cache hit check."""
    try:
        url_path = Path(url.split("?")[0])
        extension = url_path.suffix or ".jpg"
        if extension.lower() not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            extension = ".jpg"

        url_hash = hashlib.md5(str(url).encode("utf-8")).hexdigest()
        unique_name = f"url_{url_hash}{extension}"
        save_path = UPLOAD_DIR / unique_name

        if save_path.exists():
            logger.info(f"Cache hit! Using existing file: {unique_name}")
            return str(save_path)

        # Ensure upload directory exists
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        logger.info(f"Downloading image from URL: {url}")
        response = await client.get(str(url), headers=headers, timeout=15.0)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

        logger.info(f"Successfully downloaded and saved to: {save_path}")
        return str(save_path)

    except Exception as e:
        logger.error(f"Failed to download image from {url}: {e}")
        raise e


@app.post("/generate")
async def generate_lookbook(request: LookbookRequest):
    try:
        # Validate request
        if not request.image_urls:
            raise CustomException("No image URLs provided.", sys)
        
        if len(request.image_urls) < 2:
            raise CustomException("Please provide at least 2 image URLs.", sys)
        
        if not request.theme_prompt or len(request.theme_prompt.strip()) < 5:
            raise CustomException("Please provide a theme prompt (minimum 5 characters).", sys)

        logger.info(f"Theme: {request.theme_prompt}")
        logger.info(f"Processing {len(request.image_urls)} images...")

        # Process images (download URLs or decode base64)
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            tasks = [process_image_source(client, str(url)) for url in request.image_urls]
            image_paths = await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info(f"Processing complete. Results: {image_paths}")
            
            # Separate successful and failed processes
            successful_paths = []
            failed_processes = []
            
            for idx, result in enumerate(image_paths):
                if isinstance(result, Exception):
                    failed_processes.append(f"Image {idx + 1}: {str(result)}")
                    logger.error(f"Failed to process image {idx + 1}: {result}")
                else:
                    successful_paths.append(result)
                    logger.info(f"Successfully processed image {idx + 1}: {result}")
            
            if failed_processes:
                logger.warning(f"Failed to process {len(failed_processes)} images:")
                for failure in failed_processes:
                    logger.warning(f"  - {failure}")
            
            if not successful_paths:
                error_msg = "Failed to process any images. Please check the URLs or try uploading again."
                logger.error(error_msg)
                raise CustomException(error_msg, sys)
            
            image_paths = successful_paths
            logger.info(f"Successfully processed {len(image_paths)} images.")

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
