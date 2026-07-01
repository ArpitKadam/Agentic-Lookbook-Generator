import sys
import json
import os

from dotenv import load_dotenv

from src.pipeline.pipeline import build_pipeline
from src.state.state import LookbookState
from src.logger import logger
from src.exception import CustomException

load_dotenv()

os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["LANGSMITH_TRACING"] = "true"

logger.info("=" * 60)
logger.info("STARTING AGENTIC LOOKBOOK GENERATION RUNNER ENGINE")
logger.info("=" * 60)

from pathlib import Path

image_paths = []

for extension in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
    image_paths.extend(
        sorted(
            str(path)
            for path in Path("data").glob(extension)
        )
    )

logger.info(f"Found {len(image_paths)} image(s) in the 'data' directory.")

try:

    logger.info("Building lookbook orchestration pipeline graph...")
    graph = build_pipeline()

    initial_state: LookbookState = {

        "image_paths": image_paths,
        "theme_prompt": "Tokyo after midnight — neon-soaked minimalism meets Showa-era nostalgia",
        "image_analyses": [],
        "mood_clusters": None,
        "draft_cards": None,
        "lookbook": None,
        "visual_lookbook": None,
        "token_usages": [],
    }

    logger.info(f"Loaded theme prompt: '{initial_state['theme_prompt']}'")
    logger.info(f"Queued {len(initial_state['image_paths'])} images.")

    logger.info("Invoking LangGraph pipeline...")

    result = graph.invoke(initial_state)

    logger.info("Pipeline execution completed successfully.")

    logger.info("\n" + "=" * 60)

    logger.info("FINAL WEEKLY LOOKBOOK")

    logger.info("=" * 60)

    logger.info(
        json.dumps(
            result["lookbook"].model_dump(),
            indent=2,
            ensure_ascii=False,
        )
    )

    logger.info("\n" + "=" * 60)

    logger.info("VISUAL LOOKBOOK")

    logger.info("=" * 60)

    visual = result["visual_lookbook"]

    logger.info(f"Edition Cover : {visual.cover.image_path}")

    logger.info(f"Image Hash    : {visual.cover.image_hash}")

    logger.info("")

    for mood in visual.moods:

        logger.info(f"[Card {mood.card_number}] {mood.mood_title}")
        logger.info(f"Image : {mood.image_path}")
        logger.info(f"Hash  : {mood.image_hash}")
        logger.info("")

    logger.info("=" * 60)

    logger.info("AGENT TOKEN USAGE BREAKDOWN")

    logger.info("=" * 60)

    for usage in result["token_usages"]:

        logger.info(
            f"{usage.agent_name:<32}"
            f"Input={usage.input_tokens:<6}"
            f"Output={usage.output_tokens:<6}"
            f"Total={usage.total_tokens:<6}"
        )

    total_input_tokens = sum(
        usage.input_tokens
        for usage in result["token_usages"]
    )

    total_output_tokens = sum(
        usage.output_tokens
        for usage in result["token_usages"]
    )

    total_tokens = sum(
        usage.total_tokens
        for usage in result["token_usages"]
    )

    logger.info("=" * 60)

    logger.info(
        "PIPELINE SUMMARY"
    )

    logger.info("=" * 60)

    logger.info(f"Total Input Tokens  : {total_input_tokens:,}")
    logger.info(f"Total Output Tokens : {total_output_tokens:,}")
    logger.info(f"Total Tokens Used   : {total_tokens:,}")

    logger.info(f"Images Processed    : {len(initial_state['image_paths'])}")

    logger.info(f"Mood Cards Created  : {result['lookbook'].total_moods}")
    logger.info(f"Edition Title       : {result['lookbook'].edition_title}")

    logger.info("=" * 60)
    logger.info("Agentic Lookbook Generator completed successfully.")

except Exception as e:
    raise CustomException(
        f"Global pipeline orchestrator encountered an unhandled failure: {str(e)}",
        sys,
    )