from collections import defaultdict
from itertools import starmap
from pathlib import Path
from PIL import Image
from Sprite import Sprite
from typing import Iterable, Optional
import json
import util


class SpriteHandler:
    def __init__(
        self, *, base_path: Optional[Path] = None, sprite_path: Optional[Path] = None
    ) -> None:
        self.base_path: Path = Path(__file__).parent if base_path is None else base_path
        self.sprite_path: Path = Path("") if sprite_path is None else sprite_path
        self.__sprites: dict[Path, Sprite] = {}
        self.__s_by_collection: dict[str, list[Path]] = defaultdict(list)
        self.__s_by_animation: dict[str, list[Path]] = defaultdict(list)
        self.duplicates: dict[str, set[Path]] = {}

    def __getitem__(self, index: Path) -> Sprite:
        return self.__sprites[index]

    def load_sprite_info(self, paths: Iterable[Path]) -> list[str]:
        raw_data: list[dict[str, list[str]]] = []
        collections = set()
        for path in paths:
            if not path.is_absolute():
                path = self.sprite_path.joinpath(path)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            raw_data.append(data)
            collections.update(data["scollectionname"])

        self.__sprites = {
            sprite.path: sprite
            for data in raw_data
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
                    map(self.sprite_path.joinpath, data["spath"]),
                    data["scollectionname"],
                ),
            )
        }
        self.__populate_sprites()

        return sorted(collections)

    def load_duplicate_info(self) -> None:
        info_path = self.base_path.joinpath("resources", "duplicatedata.json")
        self.duplicates = {
            image_hash: set(map(self.sprite_path.joinpath, dups))
            for image_hash, dups in json.load(open(info_path, encoding="utf-8")).items()
        }

    def get_duplicates(self, animation_name: str) -> dict[str, list[str]]:
        if not animation_name:
            return {
                image_hash: loaded_sprites
                for image_hash in self.duplicates
                if (loaded_sprites := self.sorted_duplicates(image_hash))
            }
        else:
            d = {}
            for path in self.__s_by_animation[animation_name]:
                try:
                    image_hash = next(
                        im_hash
                        for im_hash, dups in self.duplicates.items()
                        if path in dups
                    )
                    loaded_sprites = self.sorted_duplicates(image_hash)
                    if loaded_sprites:
                        d[image_hash] = loaded_sprites
                except StopIteration:
                    continue
            return d

    def __populate_sprites(self) -> None:
        self.__s_by_animation.clear()
        self.__s_by_collection.clear()

        for path, sprite in self.__sprites.items():
            self.__s_by_collection[sprite.collection].append(path)
            self.__s_by_animation[sprite.animation].append(path)

    def get_animation_sprites(self, animation: str) -> list[Sprite]:
        return [self.__sprites[i].path.name for i in self.__s_by_animation[animation]]

    def pack_sheets(
        self,
        collections: dict[str, bool],
        output_path: Optional[Path] = None,
    ) -> bool:
        if output_path is None:
            output_path = self.base_path

        for collection_name, enabled in collections.items():
            if not enabled:
                continue
            max_width = 0
            max_height = 0
            for sprite_id in self.__s_by_collection[collection_name]:
                sprite = self.__sprites[sprite_id]
                if sprite.flipped:
                    max_width = max(max_width, sprite.x + sprite.h)
                    max_height = max(max_height, sprite.y + sprite.w)
                else:
                    max_width = max(max_width, sprite.x + sprite.w)
                    max_height = max(max_height, sprite.y)

            max_width = util.min_dimension(max_width)
            max_height = util.min_dimension(max_height)

            out = Image.new("RGBA", (max_width, max_height))

            for sprite_id in self.__s_by_collection[collection_name]:
                sprite = self.__sprites[sprite_id]
                im = sprite.content
                if sprite.flipped:
                    im = im.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)

                y = out.size[1] - sprite.y - (sprite.w if sprite.flipped else sprite.h)
                out.paste(im, (sprite.x, y))

            try:
                out.save(output_path.joinpath(collection_name + ".png"))
            except OSError:
                return False
        return True

    def propagate_main_copy(self, vanilla_hash: str, main: Path) -> None:
        if not main.is_absolute():
            main = self.sprite_path.joinpath(main)
        sprite = self.__sprites[main]
        main_im = sprite.content

        for path in self.duplicates[vanilla_hash]:
            if path == main or path not in self.__sprites:
                continue
            dupe_sprite = self.__sprites[path]
            dupe_im = Image.open(path)
            dupe_im.paste(
                main_im,
                (dupe_sprite.xr, dupe_im.size[1] - dupe_sprite.yr - dupe_sprite.h),
            )
            dupe_im.save(path)

    def sorted_duplicates(self, vanilla_hash: str) -> list[Path]:
        def order_by_modification(file: Path) -> int:
            if file not in self.__sprites:
                return 2
            sprite = self.__sprites[file]
            image_hash = str(self.__sprites[file].image_hash)
            return 1 if image_hash == vanilla_hash else 0

        return sorted(
            filter(lambda p: p in self.__sprites, self.duplicates[vanilla_hash]),
            key=order_by_modification,
        )

    def check_completion(self, duplicates: list[Path], vanilla_hash: str) -> bool:
        prev_hash = ""
        for path in map(self.sprite_path.joinpath, duplicates):
            if path not in self.__sprites:
                continue
            sprite = self.__sprites[path]
            curr_hash = str(sprite.image_hash)
            if not prev_hash:
                prev_hash = curr_hash
            elif curr_hash != prev_hash:
                return False
        return True

    def search_sprites(self, sprite_name: str) -> Iterable[Path]:
        for path, sprite in self.__sprites.items():
            if sprite_name in str(path):
                yield path

    def loaded_animations(self, collections: dict[str, bool]) -> Iterable[str]:
        return (
            anim
            for anim, paths in self.__s_by_animation.items()
            if any(
                collections.get(self.__sprites[path].collection, False)
                for path in paths
            )
        )
