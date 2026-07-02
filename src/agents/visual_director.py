import os
import sys
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from src.prompts.prompts import VISUAL_DIRECTOR_SYSTEM_PROMPT, VISUAL_DIRECTOR_USER_TEMPLATE
from src.schemas.schema import WeeklyLookbook,VisualLookbook,TokenUsage
from src.services.image_generator import ImageGenerator
from src.utils.utils import count_tokens
from src.logger import logger
from src.exception import CustomException

load_dotenv()


class VisualDirectorAgent:

    def __init__(self, cache_file: str = "data/cache/visual_director_cache.json"):
        logger.info("Initializing VisualDirectorAgent...")
        try:
            self.structured_llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=2048,
            ).with_structured_output(VisualLookbook)
        

            self.image_generator = ImageGenerator(api_url=os.getenv("IMAGE_GENERATION_API", ""))
            self.cache_file = Path(cache_file)
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache = self._load_cache()
            logger.info("VisualDirectorAgent initialized successfully.")
        except Exception as e:
            raise CustomException(f"Failed to initialize VisualDirectorAgent: {str(e)}",sys)

    def _load_cache(self) -> dict:
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_cache(self):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2)

    def _generate_cache_key(self, lookbook: WeeklyLookbook) -> str:
        """Generates a unique cache key from the complete WeeklyLookbook."""
        try:
            payload = json.dumps(
                {
                    "lookbook": lookbook.model_dump(),
                    "image_model": "stable-diffusion-xl-base-1.0",
                },
                sort_keys=True,
            )
            return hashlib.sha256(payload.encode("utf-8")).hexdigest()
        except Exception as e:
            raise CustomException(f"Failed to generate cache key: {str(e)}", sys)

    def create_visuals(
        self,
        lookbook: WeeklyLookbook,
        theme_prompt: str
    ) -> tuple[VisualLookbook, TokenUsage]:

        try:
            cache_key = self._generate_cache_key(lookbook)

            if cache_key in self.cache:
                cached_data = self.cache[cache_key]

                visual = VisualLookbook(**cached_data["visual_lookbook"])

                cover_exists = (
                    visual.cover.image_path is not None
                    and Path(visual.cover.image_path).exists()
                )

                moods_exist = all(
                    mood.image_path is not None
                    and Path(mood.image_path).exists()
                    for mood in visual.moods
                )

                if cover_exists and moods_exist:
                    logger.info("Visual Director cache hit.")
                    usage = TokenUsage(**cached_data["usage"])
                    usage.agent_name = "Visual Director Agent (Cached)"
                    usage.input_tokens = 0
                    usage.output_tokens = 0
                    usage.total_tokens = 0
                    return visual, usage

                logger.warning("Cached visual assets are missing. Regenerating...")
                del self.cache[cache_key]
                self._save_cache()

            # --- Generation Logic ---
            draft_json = json.dumps(
                lookbook.model_dump(),
                indent=2,
                ensure_ascii=False,
            )

            user_prompt = VISUAL_DIRECTOR_USER_TEMPLATE.format(
                theme_prompt=theme_prompt,
                lookbook_json=draft_json,
            )

            messages = [
                SystemMessage(content=VISUAL_DIRECTOR_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt)
            ]

            logger.info("Generating visual prompts...")
            visual = self.structured_llm.invoke(messages)

            if len(visual.moods) != lookbook.total_moods:
                raise ValueError(
                    f"Expected {lookbook.total_moods} mood prompts "
                    f"but received {len(visual.moods)}."
                )

            input_text = (
                VISUAL_DIRECTOR_SYSTEM_PROMPT +
                user_prompt
            )

            output_text = visual.model_dump_json()

            usage = TokenUsage(
                agent_name="Visual Director Agent",
                input_tokens=count_tokens(input_text),
                output_tokens=count_tokens(output_text),
                total_tokens=(
                    count_tokens(input_text)
                    + count_tokens(output_text)
                ),
            )

            logger.info(f"Generating {len(visual.moods) + 1} visual assets...")

            cover_payload = (
                visual.cover.positive_prompt +
                visual.cover.negative_prompt
            )

            safe_title = (
                visual.cover.edition_title
                .lower()
                .replace(" ", "_")
                .replace("/", "_")
            )

            cover_filename = (
                f"{safe_title}_"
                + hashlib.sha256(
                    cover_payload.encode("utf-8")
                ).hexdigest()[:16]
            )

            logger.info("Generating cover artwork...")

            try:
                cover = self.image_generator.generate(
                    positive_prompt=visual.cover.positive_prompt,
                    negative_prompt=visual.cover.negative_prompt,
                    filename=cover_filename,
                )

            except Exception as e:
                logger.exception(e)
                raise CustomException("Failed generating cover artwork.", sys) from e

            visual.cover.image_path = cover.image_path
            visual.cover.image_hash = cover.image_hash

            shared_context = f"""
            Visual Language:
            {visual.cover.visual_language}

            Camera Style:
            {visual.cover.camera_style}

            Color Palette:
            {", ".join(visual.cover.color_palette)}
            """

            for mood in visual.moods:
                logger.info(
                    f"Generating artwork for Card {mood.card_number} "
                    f"({mood.mood_title})..."
                )

                generation_prompt = (
                    shared_context.strip()
                    + "\n\n"
                    + mood.positive_prompt
                )

                payload = (
                    mood.positive_prompt +
                    mood.negative_prompt
                )

                safe_mood = (
                    mood.mood_title
                    .lower()
                    .replace(" ", "_")
                    .replace("/", "_")
                )

                filename_hash = hashlib.sha256(
                    payload.encode("utf-8")
                ).hexdigest()[:16]

                filename = (
                    f"{mood.card_number}_"
                    f"{safe_mood}_"
                    f"{filename_hash}"
                )

                try:
                    generated = self.image_generator.generate(
                        positive_prompt=generation_prompt,
                        negative_prompt=mood.negative_prompt,
                        filename=filename,
                    )

                except Exception as e:
                    logger.exception(e)
                    raise CustomException(
                        f"Failed generating artwork for Card {mood.card_number}.", sys) from e

                mood.image_path = generated.image_path
                mood.image_hash = generated.image_hash

            self.cache[cache_key] = {
                "visual_lookbook": visual.model_dump(),
                "usage": usage.model_dump(),
            }
            self._save_cache()

            logger.info(f"Visual lookbook '{lookbook.edition_title}' generated successfully.")

            return visual, usage
        
        except Exception as e:
            raise CustomException(f"Pipeline error during visual lookbook generation: {str(e)}", sys) from e