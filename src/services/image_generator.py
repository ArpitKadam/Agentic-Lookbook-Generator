import base64
import hashlib
import json
from io import BytesIO
from pathlib import Path
import requests
from PIL import Image
from src.logger import logger
from src.schemas.schema import GeneratedImage

class ImageGenerator:

    def __init__(
        self,
        api_url: str,
        model_name: str = "stable-diffusion-xl-base-1.0",
        cache_file: str = "data/cache/image_cache.json",
        output_dir: str = "data/generated",
        timeout: int = 180,
    ):

        self.api_url = api_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        self.cache = self._load_cache()

    def _load_cache(self) -> dict:

        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                logger.warning("Image cache corrupted. Starting fresh.")
                return {}

        return {}

    def _save_cache(self):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(
                self.cache,
                f,
                indent=4,
            )


    def _generate_cache_key(
        self,
        positive_prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        guidance_scale: float,
    ) -> str:

        payload = {
            "model": self.model_name,
            "positive_prompt": positive_prompt.strip(),
            "negative_prompt": negative_prompt.strip(),
            "width": width,
            "height": height,
            "steps": steps,
            "guidance_scale": guidance_scale,
        }

        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def _compute_image_hash(self, image_path: Path) -> str:

        with open(image_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()


    def generate(
        self,
        positive_prompt: str,
        negative_prompt: str,
        filename: str,
        width: int = 832,
        height: int = 1024,
        steps: int = 30,
        guidance_scale: float = 7.5,
        seed: int = -1,
    ) -> GeneratedImage:

        cache_key = self._generate_cache_key(
            positive_prompt,
            negative_prompt,
            width,
            height,
            steps,
            guidance_scale,
        )

        cached = self.cache.get(cache_key)

        if cached:

            image_path = Path(cached["image_path"])

            if image_path.exists():

                logger.info(
                    f"[ImageGenerator] Cache hit -> {image_path.name}"
                )

                return GeneratedImage(
                    image_path=str(image_path),
                    image_hash=cached["image_hash"],
                    seed=cached["seed"],
                    cached=True,
                )

            logger.warning(
                f"[ImageGenerator] Cached file missing. Regenerating..."
            )

        logger.info(
            f"[ImageGenerator] Generating image: {filename}"
        )

        response = requests.post(
            f"{self.api_url}/generate",
            json={
                "prompt": positive_prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "steps": steps,
                "guidance_scale": guidance_scale,
                "seed": seed,
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        image = Image.open(
            BytesIO(
                base64.b64decode(
                    data["image_base64"]
                )
            )
        )

        image_path = self.output_dir / f"{filename}.png"

        image.save(image_path)

        image_hash = self._compute_image_hash(image_path)

        generated = GeneratedImage(
            image_path=str(image_path),
            image_hash=image_hash,
            seed=data["seed_used"],
            cached=False,
        )

        self.cache[cache_key] = {
            "model": self.model_name,
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "image_path": generated.image_path,
            "image_hash": generated.image_hash,
            "seed": generated.seed,
        }

        self._save_cache()

        logger.info(
            f"[ImageGenerator] Saved -> {image_path.name}"
        )

        return generated