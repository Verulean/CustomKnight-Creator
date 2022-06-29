from collections import defaultdict
from pathlib import Path
import json


def generate_collection_sources(
    base_path: Path, output_path: Path, *, debug: bool = False
) -> None:
    appearances = defaultdict(set)
    if debug:
        print("Starting...")

    # check all SpriteInfo files
    for info_path in base_path.rglob("SpriteInfo.json"):
        if debug:
            print(f"Checking {info_path.parents[1].name}")
        with open(info_path) as f:
            data = json.load(f)

            for collection in set(data["scollectionname"]):
                appearances[collection].add(info_path.parents[1].name)

    sources = {k: sorted(v) for k, v in appearances.items()}
    with open(output_path, "w+") as f:
        json.dump(sources, f)
    if debug:
        print(f"\nSaved sheet source data to {output_path}.")


if __name__ == "__main__":
    sprite_path = Path(r"C:\Users\sprite\path")
    out_path = Path.cwd().joinpath("resources", "sheetsources.json")

    generate_collection_sources(sprite_path, out_path, debug=True)
