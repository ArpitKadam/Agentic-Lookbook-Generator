import os
import sys
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from src.schemas.schema import WeeklyLookbook, TokenUsage
from src.prompts.prompts import DIRECTOR_SYSTEM_PROMPT, DIRECTOR_USER_TEMPLATE
from src.utils.utils import count_tokens

# Import your custom logger and exception blocks
from src.logger import logger
from src.exception import CustomException

load_dotenv()

class DirectorAgent:

    def __init__(self, cache_file: str = "data/cache/director_cache.json"):
        logger.info("Initializing DirectorAgent...")
        try:
            self.structured_llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=0.8,
                max_tokens=1200
            ).with_structured_output(WeeklyLookbook)

            self.cache_file = Path(cache_file)
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache = self._load_cache()
            logger.info("DirectorAgent initialized successfully.")
        except Exception as e:
            raise CustomException(f"Failed to initialize DirectorAgent: {str(e)}", sys)

    def _load_cache(self) -> dict:
        """Loads cache from disk if it exists, otherwise returns an empty dict."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.debug(f"Director cache loaded successfully from {self.cache_file} ({len(data)} entries found).")
                    return data
            except json.JSONDecodeError as e:
                logger.warning(f"Director cache file corrupted or invalid JSON. Initializing empty cache. Error: {str(e)}")
                return {}
            except Exception as e:
                raise CustomException(f"Failed reading director cache file from disk: {str(e)}", sys)
        logger.debug("No existing director cache file found. Starting fresh.")
        return {}

    def _save_cache(self):
        """Saves current memory cache state back to disk."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=4)
            logger.debug(f"Director cache state synchronized out to disk: {self.cache_file}")
        except Exception as e:
            raise CustomException(f"Failed saving director cache file to disk: {str(e)}", sys)

    def finalize_lookbook(
        self,
        editorial_cards,
        clusters,
        theme_prompt
    ) -> tuple[WeeklyLookbook, TokenUsage]:

        logger.info(f"Finalizing lookbook compilation for theme: '{theme_prompt}'")

        try:
            draft_cards = []

            for idx, (cluster, card) in enumerate(zip(clusters.clusters, editorial_cards.cards), start=1):
                draft_cards.append({
                    "card_number": str(idx).zfill(2),
                    "mood_title": cluster.mood_title,
                    "sub_tags": cluster.sub_tags,
                    "brand_or_designer": card.brand_or_designer,
                    "product_type": card.product_type,
                    "vibe_description": card.vibe_description
                })

            draft = {
                "total_moods": len(draft_cards),
                "collection": draft_cards
            }

            draft_json = json.dumps(draft, indent=2)
        
            combined_payload = f"theme:{theme_prompt}||draft:{draft_json}"
            cache_key = hashlib.sha256(combined_payload.encode("utf-8")).hexdigest()

            if cache_key in self.cache:
                logger.info(f"[CACHE HIT] Reusing cached lookbook finalization for theme: '{theme_prompt}'")
                cached = self.cache[cache_key]

                lookbook = WeeklyLookbook(**cached["lookbook"])
                usage = TokenUsage(**cached["usage"])

                usage.agent_name = "Director Agent (Cached)"
                usage.input_tokens = 0
                usage.output_tokens = 0
                usage.total_tokens = 0

                return lookbook, usage

            logger.info(f"[CACHE MISS] Compiling final weekly lookbook live via Llama-3.3-70b...")

            user_prompt = DIRECTOR_USER_TEMPLATE.format(
                theme_prompt=theme_prompt,
                draft_json=draft_json
            )

            messages = [
                SystemMessage(content=DIRECTOR_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt)
            ]

            lookbook = self.structured_llm.invoke(messages)

            input_text = DIRECTOR_SYSTEM_PROMPT + user_prompt
            output_text = lookbook.model_dump_json()

            usage = TokenUsage(
                agent_name="Director Agent",
                input_tokens=count_tokens(input_text),
                output_tokens=count_tokens(output_text),
                total_tokens=count_tokens(input_text) + count_tokens(output_text)
            )

            self.cache[cache_key] = {
                "lookbook": lookbook.model_dump(),
                "usage": usage.model_dump()
            }
            self._save_cache()

            logger.info("Successfully compiled and cached weekly fashion lookbook.")
            return lookbook, usage

        except Exception as e:
            raise CustomException(f"Pipeline error during final lookbook generation: {str(e)}", sys)
