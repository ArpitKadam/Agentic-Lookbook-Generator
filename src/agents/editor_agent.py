import os
import sys
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from src.schemas.schema import EditorialCards, TokenUsage
from src.prompts.prompts import EDITOR_SYSTEM_PROMPT, EDITOR_USER_TEMPLATE
from src.utils.utils import count_tokens
from src.logger import logger
from src.exception import CustomException

load_dotenv()

class EditorAgent:

    def __init__(self, cache_file: str = "data/cache/editor_cache.json"):
        logger.info("Initializing EditorAgent...")
        try:
            self.structured_llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=1024
            ).with_structured_output(EditorialCards)

            self.cache_file = Path(cache_file)
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache = self._load_cache()
            logger.info("EditorAgent initialized successfully.")
        except Exception as e:
            raise CustomException(f"Failed to initialize EditorAgent: {str(e)}", sys)

    def _load_cache(self) -> dict:
        """Loads cache from disk if it exists, otherwise returns empty dict."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.debug(f"Editor cache loaded successfully from {self.cache_file} ({len(data)} entries found).")
                    return data
            except json.JSONDecodeError as e:
                logger.warning(f"Editor cache file corrupted or invalid JSON. Initializing empty cache. Error: {str(e)}")
                return {}
            except Exception as e:
                raise CustomException(f"Failed reading editor cache file from disk: {str(e)}", sys)
        logger.debug("No existing editor cache file found. Starting fresh.")
        return {}

    def _save_cache(self):
        """Saves current memory cache state back to disk."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=4)
            logger.debug(f"Editor cache state synchronized out to disk: {self.cache_file}")
        except Exception as e:
            raise CustomException(f"Failed saving editor cache file to disk: {str(e)}", sys)

    def _generate_cache_key(self, theme_prompt: str, cards_json: str) -> str:
        """Generates a stable, unique cryptographic hash of input prompts and payload briefs."""
        try:
            combined_payload = f"theme:{theme_prompt}||briefs:{cards_json}"
            return hashlib.sha256(combined_payload.encode("utf-8")).hexdigest()
        except Exception as e:
            raise CustomException(f"Failed to generate editor cache key signature: {str(e)}", sys)
    
    def create_editorial_cards(
        self,
        clusters,
        analyses,
        theme_prompt
    ) -> tuple[EditorialCards, TokenUsage]:

        logger.info(f"Processing editorial cards generation for theme: '{theme_prompt}'")

        try:
            analysis_lookup = {analysis.image_index: analysis for analysis in analyses}
            card_briefs = []

            for card_idx, cluster in enumerate(clusters.clusters, start=1):
                primary_idx = cluster.image_indices[0]
                analysis = analysis_lookup.get(primary_idx)

                brief = {
                    "card_index": card_idx,
                    "mood_title": cluster.mood_title,
                    "sub_tags": cluster.sub_tags,
                    "styling_rationale": cluster.styling_rationale,
                    "curator_notes": {
                        "garment_type": analysis.garment_type if analysis else "",
                        "color_palette": analysis.color_palette if analysis else [],
                        "silhouette": analysis.silhouette if analysis else "",
                        "texture_or_fabric": analysis.texture_or_fabric if analysis else "",
                        "style_era": analysis.style_era if analysis else "",
                        "occasion": analysis.occasion if analysis else "",
                        "standout_detail": analysis.standout_detail if analysis else ""
                    }
                }
                card_briefs.append(brief)

            cards_json = json.dumps(card_briefs, indent=2)

            cache_key = self._generate_cache_key(theme_prompt, cards_json)

            if cache_key in self.cache:
                logger.info(f"[CACHE HIT] Reusing cached editorial cards for theme: '{theme_prompt}'")
                cached_data = self.cache[cache_key]
                
                editorial_cards = EditorialCards(**cached_data["editorial_cards"])
                usage = TokenUsage(**cached_data["usage"])

                usage.agent_name = "Editor Agent (Cached)"
                usage.input_tokens = 0
                usage.output_tokens = 0
                usage.total_tokens = 0
                
                return editorial_cards, usage

            logger.info(f"[CACHE MISS] Synthesizing editorial cards live via Llama-3.3-70b...")
            
            user_prompt = EDITOR_USER_TEMPLATE.format(
                n_cards=len(card_briefs),
                theme_prompt=theme_prompt,
                cards_json=cards_json
            )

            messages = [
                SystemMessage(content=EDITOR_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt)
            ]

            editorial_cards = self.structured_llm.invoke(messages)

            input_text = EDITOR_SYSTEM_PROMPT + user_prompt
            output_text = editorial_cards.model_dump_json()

            usage = TokenUsage(
                agent_name="Editor Agent",
                input_tokens=count_tokens(input_text),
                output_tokens=count_tokens(output_text),
                total_tokens=count_tokens(input_text) + count_tokens(output_text)
            )

            self.cache[cache_key] = {
                "editorial_cards": editorial_cards.model_dump(),
                "usage": usage.model_dump()
            }
            self._save_cache()

            logger.info("Successfully processed and cached editorial cards generation.")
            return editorial_cards, usage

        except Exception as e:
            raise CustomException(f"Pipeline error during editorial cards extraction: {str(e)}", sys)
