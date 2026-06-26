import os
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, SystemMessage
from src.schemas.schema import ImageAnalysis, TokenUsage
from src.utils.utils import encode_image, count_tokens
from src.prompts.prompts import CURATOR_SYSTEM_PROMPT

load_dotenv()

class CuratorAgent:

    def __init__(self, cache_file: str = "data/cache/curator_cache.json"):
        self.structured_llm = ChatNVIDIA(
            model="meta/llama-3.2-90b-vision-instruct",
            api_key=os.getenv("NVIDIA_API_KEY"),
            temperature=0.5,
            max_tokens=150
        ).with_structured_output(ImageAnalysis)

        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        """Loads cache from disk if it exists, otherwise returns empty dict."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_cache(self):
        """Saves current memory cache state back to disk."""
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=4)

    def _get_image_cache_key(self, image_path: str) -> str:
        """Generates a cache key from the image content."""
        path = Path(image_path)
        if not path.exists():
            return path.name
            
        with open(image_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def analyze_image(
        self,
        image_path: str,
        image_index: int
    ) -> tuple[ImageAnalysis, TokenUsage]:

        cache_key = self._get_image_cache_key(image_path)
        filename = Path(image_path).name

        if cache_key in self.cache:
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

        return parsed, usage