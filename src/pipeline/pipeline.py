import sys
from langgraph.graph import StateGraph, START, END
from src.state.state import LookbookState
from src.agents.curator_agent import CuratorAgent
from src.agents.stylist_agent import StylistAgent
from src.agents.editor_agent import EditorAgent
from src.agents.director_agent import DirectorAgent
from src.logger import logger
from src.exception import CustomException

logger.info("Initializing Agent nodes for LangGraph Lookbook Pipeline...")
try:
    curator = CuratorAgent()
    stylist = StylistAgent()
    editor = EditorAgent()
    director = DirectorAgent()
    logger.info("All Agent nodes initialized successfully.")
except Exception as e:
    raise CustomException(f"Failed to instantiate pipeline agents: {str(e)}", sys)


def curator_node(state: LookbookState) -> dict:
    logger.info(">>> Entering [Curator Node] execution frame")
    try:
        analyses = []
        usages = []

        total_images = len(state["image_paths"])
        logger.info(f"Curator Node received {total_images} images to process.")

        for idx, image_path in enumerate(state["image_paths"], start=1):
            logger.debug(f"Processing image {idx}/{total_images}: {image_path}")
            analysis, usage = curator.analyze_image(
                image_path=image_path,
                image_index=idx
            )
            analyses.append(analysis)
            usages.append(usage)

        logger.info(f"<<< Completed [Curator Node] execution loops safely.")
        return {
            "image_analyses": analyses,
            "token_usages": usages
        }
    except Exception as e:
        raise CustomException(f"Pipeline failure inside [Curator Node]: {str(e)}", sys)


def stylist_node(state: LookbookState) -> dict:
    logger.info(">>> Entering [Stylist Node] execution frame")
    try:
        theme = state["theme_prompt"]
        logger.info(f"Synthesizing creative layout options for theme: '{theme}'")

        clusters, usage = stylist.create_moods(
            theme_prompt=theme,
            curator_analyses=state.get("image_analyses") or []
        )

        logger.info("<<< Completed [Stylist Node] synthesis safely.")
        return {
            "mood_clusters": clusters,
            "token_usages": [usage]
        }
    except Exception as e:
        raise CustomException(f"Pipeline failure inside [Stylist Node]: {str(e)}", sys)


def editor_node(state: LookbookState) -> dict:
    logger.info(">>> Entering [Editor Node] execution frame")
    try:
        theme = state["theme_prompt"]
        logger.info(f"Drafting structural descriptions layout for theme: '{theme}'")

        editorial_cards, usage = editor.create_editorial_cards(
            clusters=state["mood_clusters"],
            analyses=state["image_analyses"],
            theme_prompt=theme
        )

        logger.info("<<< Completed [Editor Node] copywriting safely.")
        return {
            "draft_cards": editorial_cards,
            "token_usages": [usage]
        }
    except Exception as e:
        raise CustomException(f"Pipeline failure inside [Editor Node]: {str(e)}", sys)


def director_node(state: LookbookState) -> dict:
    logger.info(">>> Entering [Director Node] execution frame")
    try:
        theme = state["theme_prompt"]
        logger.info(f"Finalizing lookbook asset generation metrics for theme: '{theme}'")

        lookbook, usage = director.finalize_lookbook(
            editorial_cards=state["draft_cards"],
            clusters=state["mood_clusters"],
            theme_prompt=theme
        )

        logger.info("<<< Completed [Director Node] aggregation safely.")
        return {
            "lookbook": lookbook,
            "token_usages": [usage]
        }
    except Exception as e:
        raise CustomException(f"Pipeline failure inside [Director Node]: {str(e)}", sys)


def build_pipeline():
    logger.info("Compiling Lookbook StateGraph execution structure...")
    try:
        graph = StateGraph(LookbookState)

        graph.add_node("curator", curator_node)
        graph.add_node("stylist", stylist_node)
        graph.add_node("editor", editor_node)
        graph.add_node("director", director_node)

        graph.add_edge(START, "curator")
        graph.add_edge("curator", "stylist")
        graph.add_edge("stylist", "editor")
        graph.add_edge("editor", "director")
        graph.add_edge("director", END)

        compiled_graph = graph.compile()
        logger.info("StateGraph compiled successfully. Lookbook pipeline is active.")

        image_data = compiled_graph.get_graph().draw_mermaid_png()

        with open("pipeline_graph.png", "wb") as f:
            f.write(image_data)
            logger.info("Pipeline graph visualization saved as 'pipeline_graph.png'")
        
        return compiled_graph
    except Exception as e:
        raise CustomException(f"Failed compiling Lookbook StateGraph configuration: {str(e)}", sys)
