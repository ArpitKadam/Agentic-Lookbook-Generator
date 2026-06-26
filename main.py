from src.pipeline.pipeline import build_pipeline
from src.state.state import LookbookState

graph = build_pipeline()

initial_state: LookbookState = {
    "image_paths": [
        "data/Anime Tshirt.jpg",
        "data/Quiet Luxury Style Shirt.jpg",
        "data/Summer Luxury Streetwear.jpg",
        "data/Girl's Anime Long Sleeve T-shirt.jpg"
    ],

    "theme_prompt":
        "Tokyo after midnight — neon-soaked minimalism meets Showa-era nostalgia",

    "image_analyses": [],
    "mood_clusters": None,
    "draft_cards": None,
    "lookbook": None,
    "token_usages": []
}

result = graph.invoke(initial_state)

print(result["lookbook"].model_dump())

print("\nTOKEN USAGE BREAKDOWN\n")

for usage in result["token_usages"]:
    print(usage)

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

print("\n" + "=" * 60)
print("TOTAL PIPELINE TOKEN USAGE")
print("=" * 60)

print(f"Input Tokens  : {total_input_tokens}")
print(f"Output Tokens : {total_output_tokens}")
print(f"Total Tokens  : {total_tokens}")