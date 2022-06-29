# This was used to create duplicatedata.json. It's not actually used at runtime.

from collections import defaultdict
from itertools import starmap
from pathlib import Path
from Sprite import Sprite
import json


def generate_duplicate_data(
    base_path: Path, output_path: Path, *, debug: bool = False
) -> None:
    duplicates = defaultdict(list)
    if debug:
        print("Starting...")

    # check all SpriteInfo files
    for info_path in base_path.rglob("SpriteInfo.json"):
        if debug:
            print(f"Checking {info_path.parents[1].name}")
        with open(info_path) as f:
            data = json.load(f)

            # add each sprite in SpriteInfo.json to its hash bin
            for sprite in starmap(
                Sprite,
                zip(
                    data["sid"],
                    data["sx"],
                    data["sy"],
                    data["sxr"],
                    data["syr"],
                    data["swidth"],
                    data["sheight"],
                    data["sfilpped"],
                    map(base_path.joinpath, data["spath"]),
                    data["scollectionname"],
                ),
            ):
                image_hash = str(sprite.image_hash)
                rel_path = str(sprite.path.relative_to(base_path))
                duplicates[image_hash].append(rel_path)

    # filter out image hashes with only one matching sprite
    duplicates = {k: v for k, v in duplicates.items() if len(v) > 1}
    with open(output_path, "w+") as f:
        json.dump(duplicates, f)
    if debug:
        print(f"\nSaved duplicate data to {output_path}.")


if __name__ == "__main__":
    # set `in_path` to a directory containing every base animation folder
    sprite_path = Path(r"C:\Users\sprite\path")
    out_path = Path.cwd().joinpath("resources", "duplicatedata.json")

    generate_duplicate_data(sprite_path, out_path, debug=True)
