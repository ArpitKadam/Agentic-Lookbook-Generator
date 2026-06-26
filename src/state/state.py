from typing import Annotated, List, Optional, Tuple
from typing_extensions import TypedDict
import operator

from src.schemas.schema import (
    ImageAnalysis,
    MoodClusters,
    EditorialCards,
    WeeklyLookbook,
    TokenUsage
)


class LookbookState(TypedDict):
    """Typed state object shared across all agent nodes."""

    image_paths: List[str]
    theme_prompt: str
    image_analyses: Optional[List[ImageAnalysis]]
    mood_clusters: Optional[MoodClusters]
    draft_cards: Optional[EditorialCards]
    lookbook: Optional[WeeklyLookbook]
    token_usages: Annotated[List[TokenUsage], operator.add]