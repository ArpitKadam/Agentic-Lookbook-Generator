import os
import sys
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, SystemMessage
from src.schemas.schema import ImageAnalysis, TokenUsage
from src.utils.utils import encode_image, count_tokens
from src.prompts.prompts import CURATOR_SYSTEM_PROMPT
from src.logger import logger
from src.exception import CustomException

load_dotenv()

class CuratorAgent:

    def __init__(self, cache_file: str = "data/cache/curator_cache.json"):
        logger.info("Initializing CuratorAgent...")
        try:
            self.structured_llm = ChatNVIDIA(
                model="meta/llama-3.2-90b-vision-instruct",
                api_key=os.getenv("NVIDIA_API_KEY"),
                temperature=0.5,
                max_tokens=150
            ).with_structured_output(ImageAnalysis)

            self.cache_file = Path(cache_file)
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache = self._load_cache()
            logger.info("CuratorAgent initialized successfully.")
        except Exception as e:
            raise CustomException(f"Failed to initialize CuratorAgent: {str(e)}", sys)

    def _load_cache(self) -> dict:
        """Loads cache from disk if it exists, otherwise returns empty dict."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.debug(f"Curator cache loaded successfully from {self.cache_file} ({len(data)} entries found).")
                    return data
            except json.JSONDecodeError as e:
                logger.warning(f"Curator cache file corrupted or invalid JSON. Initializing empty cache. Error: {str(e)}")
                return {}
            except Exception as e:
                raise CustomException(f"Failed reading cache file from disk: {str(e)}", sys)
        logger.debug("No existing curator cache file found. Starting fresh.")
        return {}

    def _save_cache(self):
        """Saves current memory cache state back to disk."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=4)
            logger.debug(f"Curator cache state synchronized out to disk: {self.cache_file}")
        except Exception as e:
            raise CustomException(f"Failed saving cache file to disk: {str(e)}", sys)

    def _get_image_cache_key(self, image_path: str) -> str:
        """Generates a unique cache key from the image content bytes."""
        path = Path(image_path)
        if not path.exists():
            logger.warning(f"Target image path does not exist for key generation: {image_path}")
            return path.name
            
        try:
            with open(image_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            raise CustomException(f"Failed to compute file hash for {image_path}: {str(e)}", sys)

    def analyze_image(
        self,
        image_path: str,
        image_index: int
    ) -> tuple[ImageAnalysis, TokenUsage]:
        
        filename = Path(image_path).name
        logger.info(f"Processing image analysis for: {filename} (Index: {image_index})")

        try:
            cache_key = self._get_image_cache_key(image_path)

            if cache_key in self.cache:
                logger.info(f"[CACHE HIT] Reusing cached analysis for file: {filename}")
                cached_data = self.cache[cache_key]

                parsed = ImageAnalysis(**cached_data["parsed"])
                usage = TokenUsage(**cached_data["usage"])

                parsed.image_index = image_index
                parsed.filename = filename

                usage.agent_name = "Curator Agent (Cached)"
                usage.input_tokens = 0
                usage.output_tokens = 0
                usage.total_tokens = 0
                
                return parsed, usage

            logger.info(f"[CACHE MISS] Analyzing image live via Nvidia API for file: {filename}")
            
            if not Path(image_path).exists():
                raise FileNotFoundError(f"Image asset missing at location: {image_path}")

            encoded_image = encode_image(image_path)

            messages = [
                SystemMessage(content=CURATOR_SYSTEM_PROMPT),
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": f"\nAnalyze this fashion image.\n\nFilename: {filename}\n\nReturn analysis using the exact JSON schema.\n"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}"
                            }
                        }
                    ]
                )
            ]

            parsed = self.structured_llm.invoke(messages)

            messages_for_counting = messages.copy()
            messages_for_counting[1].content[1] = {
                "type": "image_url",
                "image_url": "[IMAGE_REMOVED]"
            }

            input_text = CURATOR_SYSTEM_PROMPT + str(messages_for_counting)
            output_text = parsed.model_dump_json()

            usage = TokenUsage(
                agent_name="Curator Agent",
                input_tokens=count_tokens(input_text),
                output_tokens=count_tokens(output_text),
                total_tokens=count_tokens(input_text) + count_tokens(output_text)
            )

            parsed.image_index = image_index
            parsed.filename = filename

            self.cache[cache_key] = {
                "parsed": parsed.model_dump(),
                "usage": usage.model_dump()
            }
            self._save_cache()

            logger.info(f"Successfully processed and cached live analysis for file: {filename}")
            return parsed, usage

        except Exception as e:
            raise CustomException(f"Pipeline error during image processing for {filename}: {str(e)}", sys)
