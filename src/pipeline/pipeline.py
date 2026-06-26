from langgraph.graph import StateGraph, START, END
from src.state.state import LookbookState
from src.agents.curator_agent import CuratorAgent
from src.agents.stylist_agent import StylistAgent
from src.agents.editor_agent import EditorAgent
from src.agents.director_agent import DirectorAgent

curator = CuratorAgent()
stylist = StylistAgent()
editor = EditorAgent()
director = DirectorAgent()

def curator_node(
    state: LookbookState
) -> dict:

    analyses = []
    usages = []

    for idx, image_path in enumerate(
        state["image_paths"],
        start=1
    ):

        analysis, usage = curator.analyze_image(
            image_path=image_path,
            image_index=idx
        )

        analyses.append(analysis)
        usages.append(usage)

    return {
        "image_analyses": analyses,
        "token_usages": usages
    }


def stylist_node(
    state: LookbookState
) -> dict:

    clusters, usage = stylist.create_moods(
        theme_prompt=state["theme_prompt"],
        curator_analyses=state["image_analyses"]
    )

    return {
        "mood_clusters": clusters,
        "token_usages": [usage]
    }


def editor_node(
    state: LookbookState
) -> dict:

    editorial_cards, usage = (
        editor.create_editorial_cards(
            clusters=state["mood_clusters"],
            analyses=state["image_analyses"],
            theme_prompt=state["theme_prompt"]
        )
    )

    return {
        "draft_cards": editorial_cards,
        "token_usages": [usage]
    }


def director_node(
    state: LookbookState
) -> dict:

    lookbook, usage = director.finalize_lookbook(
        editorial_cards=state["draft_cards"],
        clusters=state["mood_clusters"],
        theme_prompt=state["theme_prompt"]
    )

    return {
        "lookbook": lookbook,
        "token_usages": [usage]
    }


def build_pipeline():

    graph = StateGraph(LookbookState)

    graph.add_node("curator", curator_node)
    graph.add_node("stylist", stylist_node)
    graph.add_node("editor", editor_node)
    graph.add_node("director",director_node)

    graph.add_edge(START, "curator")
    graph.add_edge("curator", "stylist")
    graph.add_edge("stylist", "editor")
    graph.add_edge("editor","director")
    graph.add_edge("director",END)

    return graph.compile()