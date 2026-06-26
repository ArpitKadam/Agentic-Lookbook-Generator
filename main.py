import sys
import json
from src.pipeline.pipeline import build_pipeline
from src.state.state import LookbookState
from src.logger import logger
from src.exception import CustomException
from dotenv import load_dotenv
import os

load_dotenv()

os.environ['LANGSMITH_API_KEY'] = os.getenv("LANGSMITH_API_KEY", "")
os.environ['LANGSMITH_TRACING'] = "true"

logger.info("============================================================")
logger.info("STARTING AGENTIC LOOKBOOK GENERATION RUNNER ENGINE")
logger.info("============================================================")

try:
    logger.info("Building lookbook orchestration pipeline graph...")
    graph = build_pipeline()

    initial_state: LookbookState = {
        "image_paths": [
            "data/Anime Tshirt.jpg",
            "data/Quiet Luxury Style Shirt.jpg",
            "data/Summer Luxury Streetwear.jpg",
            "data/Girl's Anime Long Sleeve T-shirt.jpg"
        ],
        "theme_prompt": "Tokyo after midnight — neon-soaked minimalism meets Showa-era nostalgia",
        "image_analyses": [],
        "mood_clusters": None,
        "draft_cards": None,
        "lookbook": None,
        "token_usages": []
    }

    logger.info(f"Loaded target theme prompt: '{initial_state['theme_prompt']}'")
    logger.info(f"Queued images for generation processing: {len(initial_state['image_paths'])} source files found.")

    logger.info("Invoking lookbook graph pipeline processing. Standing by...")
    result = graph.invoke(initial_state)
    logger.info("Lookbook graph execution completed successfully.")

    logger.info("Parsing lookbook payload results mapping configuration...")
    lookbook_data = result["lookbook"].model_dump()
    
    logger.info("\n--- FINAL COMPILED WEEKLY LOOKBOOK DESIGN DATA ---")
    logger.info(json.dumps(lookbook_data, indent=2, ensure_ascii=False))
    logger.info("--------------------------------------------------\n")

    logger.info("Compiling cross-agent total execution telemetry metrics...")
    
    logger.info("\n============================================================")
    logger.info("               AGENT TOKEN USAGE BREAKDOWN                  ")
    logger.info("============================================================")
    
    for usage in result["token_usages"]:
        logger.info(
            f"-> {usage.agent_name:<25} | "
            f"Input: {usage.input_tokens:<5} | "
            f"Output: {usage.output_tokens:<5} | "
            f"Total: {usage.total_tokens:<5}"
        )

    total_input_tokens = sum(usage.input_tokens for usage in result["token_usages"])
    total_output_tokens = sum(usage.output_tokens for usage in result["token_usages"])
    total_tokens = sum(usage.total_tokens for usage in result["token_usages"])

    logger.info("\n" + "=" * 60)
    logger.info("                TOTAL PIPELINE CONSOLE SUMMARY              ")
    logger.info("=" * 60)
    logger.info(f" Total Input Tokens  : {total_input_tokens:,}")
    logger.info(f" Total Output Tokens : {total_output_tokens:,}")
    logger.info(f" Total Pipeline Cost : {total_tokens:,} tokens")
    logger.info("=" * 60 + "\n")

    logger.info("Agentic Lookbook Generator completed execution without errors.")

except Exception as e:
    raise CustomException(f"Global pipeline orchestrator encountered an unhandled run failure: {str(e)}", sys)
