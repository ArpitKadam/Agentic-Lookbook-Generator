import os
import sys
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from src.schemas.schema import MoodClusters, TokenUsage
from src.prompts.prompts import STYLIST_SYSTEM_PROMPT, STYLIST_USER_TEMPLATE
from src.utils.utils import count_tokens
from src.logger import logger
from src.exception import CustomException

load_dotenv()

class StylistAgent:

    def __init__(self, cache_file: str = "data/cache/stylist_cache.json"):
        logger.info("Initializing StylistAgent...")
        try:
            self.structured_llm = ChatGroq(
                model="llama-3.1-8b-instant",
                temperature=0.6,
                max_tokens=512
            ).with_structured_output(MoodClusters)

            self.cache_file = Path(cache_file)
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache = self._load_cache()
            logger.info("StylistAgent initialized successfully.")
        except Exception as e:
            raise CustomException(f"Failed to initialize StylistAgent: {str(e)}", sys)

    def _load_cache(self) -> dict:
        """Loads cache from disk if it exists, otherwise returns empty dict."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.debug(f"Stylist cache loaded successfully from {self.cache_file} ({len(data)} entries found).")
                    return data
            except json.JSONDecodeError as e:
                logger.warning(f"Stylist cache file corrupted or invalid JSON. Initializing empty cache. Error: {str(e)}")
                return {}
            except Exception as e:
                raise CustomException(f"Failed reading stylist cache file from disk: {str(e)}", sys)
        logger.debug("No existing stylist cache file found. Starting fresh.")
        return {}

    def _save_cache(self):
        """Saves current memory cache state back to disk."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=4)
            logger.debug(f"Stylist cache state synchronized out to disk: {self.cache_file}")
        except Exception as e:
            raise CustomException(f"Failed saving stylist cache file to disk: {str(e)}", sys)

    def _generate_cache_key(self, theme_prompt: str, analyses_json: str) -> str:
        """Creates a stable unique hash from the input prompt and image metadata."""
        try:
            combined_payload = f"theme:{theme_prompt}||analyses:{analyses_json}"
            return hashlib.sha256(combined_payload.encode("utf-8")).hexdigest()
        except Exception as e:
            raise CustomException(f"Failed to generate cache key hash signature: {str(e)}", sys)

    def create_moods(
        self,
        theme_prompt: str,
        curator_analyses: list
    ) -> tuple[MoodClusters, TokenUsage]:

        logger.info(f"Processing mood clusters generation for prompt: '{theme_prompt}'")

        try:
            analyses_json = json.dumps(
                [
                    analysis.model_dump()
                    for analysis in curator_analyses
                ],
                indent=2
            )

            cache_key = self._generate_cache_key(theme_prompt, analyses_json)

            if cache_key in self.cache:
                logger.info(f"[CACHE HIT] Reusing cached mood clusters for prompt: '{theme_prompt}'")
                cached_data = self.cache[cache_key]
                
                clusters = MoodClusters(**cached_data["clusters"])
                usage = TokenUsage(**cached_data["usage"])

                usage.agent_name = "Stylist Agent (Cached)"
                usage.input_tokens = 0
                usage.output_tokens = 0
                usage.total_tokens = 0
                
                return clusters, usage

            logger.info(f"[CACHE MISS] Synthesizing mood clusters live via Groq API...")
            
            user_prompt = STYLIST_USER_TEMPLATE.format(
                theme_prompt=theme_prompt,
                n_images=len(curator_analyses),
                max_idx=len(curator_analyses),
                analyses_json=analyses_json
            )

            messages = [
                SystemMessage(content=STYLIST_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt)
            ]

            clusters = self.structured_llm.invoke(messages)

            input_text = STYLIST_SYSTEM_PROMPT + user_prompt
            output_text = clusters.model_dump_json()

            usage = TokenUsage(
                agent_name="Stylist Agent",
                input_tokens=count_tokens(input_text),
                output_tokens=count_tokens(output_text),
                total_tokens=count_tokens(input_text) + count_tokens(output_text)
            )

            self.cache[cache_key] = {
                "clusters": clusters.model_dump(),
                "usage": usage.model_dump()
            }
            self._save_cache()

            logger.info("Successfully processed and cached mood clusters generation.")
            return clusters, usage

        except Exception as e:
            raise CustomException(f"Pipeline error during mood clusters generation: {str(e)}", sys)
