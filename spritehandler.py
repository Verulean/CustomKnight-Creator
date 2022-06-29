"""
This module implements the sprite management backend for CustomKnight Creator.
"""
from collections import defaultdict
from itertools import starmap
from pathlib import Path
from PIL import Image
from Sprite import Sprite
from typing import Iterable, Optional
import json
import util


class SpriteHandler:
    """
    The SpriteHandler class implements the main management functionality for
    CustomKnight respriting. A SpriteHandler allows for searching, organizing,
    duplicate management, and packing into sheets of a SpritePacker-style sprite
    directory.
    """

    def __init__(
        self, *, base_path: Optional[Path] = None, sprite_path: Optional[Path] = None
    ) -> None:
        """
        Constructor for SpriteHandler.

        Parameters
        ----------
        base_path : Optional[Path], optional
            The base path to the CustomKnight Creator directory. If `base_path`
            is None, defaults to this module's directory. The default is None.
        sprite_path : Optional[Path], optional
            The path to the sprite directory. If `sprite_path` is None, defaults
            to an empty Path. The default is None.

        Returns
        -------
        None.

        """
        self.base_path: Path = Path(__file__).parent if base_path is None else base_path
        self.sprite_path: Path = Path("") if sprite_path is None else sprite_path

        # all sprites, by sprite path
        self.__sprites: dict[Path, Sprite] = {}
        # all sprites, by collection name
        self.__s_by_collection: dict[str, list[Path]] = defaultdict(list)
        # all sprites, by animation name
        self.__s_by_animation: dict[str, list[Path]] = defaultdict(list)

        # paths to duplicate sprites, by vanilla sprite hash
        self.duplicates: dict[str, set[Path]] = {}

    def __rectify_sprite_path(self, path: Path) -> Path:
        if path.is_absolute():
            return path
        return self.sprite_path.joinpath(path)

    def __getitem__(self, index: Path) -> Sprite:
        """
        Returns the sprite at a given path.

        Parameters
        ----------
        index : Path
            The sprite path to find the sprite for.

        Returns
        -------
        Sprite
            An object representing the sprite at the specified path.

        """
        index = self.__rectify_sprite_path(index)
        return self.__sprites[index]

    def load_sprite_info(self, paths: Iterable[Path]) -> list[str]:
        """
        Loads sprite information from a list of provided SpriteInfo.json files.
        Populates the master sprite dictionaries from the loaded data.

        Parameters
        ----------
        paths : Iterable[Path]
            A sequence of paths to SpriteInfo.json files, each of which give
            information about sprite size, orientation, and sheet location for
            a sprite sheet.

        Returns
        -------
        list[str]
            A list of names for the collections present in the given sprite
            information.

        """
        raw_data: list[dict[str, list[str]]] = []
        collections = set()
        for path in paths:
            path = self.__rectify_sprite_path(path)
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
        """
        Loads and processes information about all possible sets of duplicate
        sprites.

        Returns
        -------
        None.

        """
        info_path = self.base_path.joinpath("resources", "duplicatedata.json")
        self.duplicates = {
            image_hash: set(map(self.__rectify_sprite_path, dups))
            for image_hash, dups in json.load(open(info_path, encoding="utf-8")).items()
        }

    def get_duplicates(self, animation_name: str) -> dict[str, list[Path]]:
        """
        Returns the duplicate sprites that appear in a given animation.

        Parameters
        ----------
        animation_name : str
            The name of the animation to return duplicate sets for. If
            `animation_name` is an empty string, returns duplicate sets for
            all loaded animations.

        Returns
        -------
        dict[str, list[Path]]
            A mapping from vanilla image hashes to a collection of paths to
            duplicate sprites that have the hash.

        """
        if not animation_name:
            return {
                image_hash: loaded_sprites
                for image_hash in self.duplicates
                if len(loaded_sprites := self.sorted_duplicates(image_hash)) > 1
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
                    if len(loaded_sprites) > 1:
                        d[image_hash] = loaded_sprites
                except StopIteration:
                    continue
            return d

    def __populate_sprites(self) -> None:
        """
        Update sprite dictionaries for searching by collection / by animation
        using master sprite dictionary.

        Returns
        -------
        None.

        """
        self.__s_by_animation.clear()
        self.__s_by_collection.clear()

        for path, sprite in self.__sprites.items():
            self.__s_by_collection[sprite.collection].append(path)
            self.__s_by_animation[sprite.animation].append(path)

    def get_animation_sprites(self, animation: str) -> list[str]:
        """
        Returns all frames of an animation.

        Parameters
        ----------
        animation : str
            The name of the animation.

        Returns
        -------
        list[str]
            A sequence of file names for the sprites that make up the given
            animation. The list contains file names in chronological order of
            the animation itself.

        """
        return [self.__sprites[i].path.name for i in self.__s_by_animation[animation]]

    def pack_sheets(
        self, collections: dict[str, bool], output_path: Optional[Path] = None
    ) -> bool:
        """
        Packs sprites from enabled collections and saves the resulting sheets.

        Parameters
        ----------
        collections : dict[str, bool]
            A mapping from collection names to the enabled/disabled state.
        output_path : Optional[Path], optional
            The output directory to save to. If `output_path` is None, saves
            to `base_path`. The default is None.

        Returns
        -------
        bool
            A flag that indicates whether the packing process succeeded.

        """
        if output_path is None:
            output_path = self.base_path

        for collection_name, enabled in collections.items():
            if not enabled:
                continue

            # calculate maximum dimensions of the group of packed sprites
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

            # create sheet image with correct dimensions to fit all sprites
            max_width = util.min_dimension(max_width)
            max_height = util.min_dimension(max_height)
            out = Image.new("RGBA", (max_width, max_height))

            # paste all sprites into sheet
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
        """
        Overwrites duplicate sprites with a given main image.

        Parameters
        ----------
        vanilla_hash : str
            The vanilla image hash of the duplicate sprites.
        main : Path
            A path to the main sprite to replace all other duplicates with.

        Returns
        -------
        None.

        """
        main = self.__rectify_sprite_path(main)
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
        """
        Returns a sorted list of a given set of duplicate sprites based on the
        state of modification of each sprite.

        Parameters
        ----------
        vanilla_hash : str
            The vanilla image hash of the duplicate sprites.

        Returns
        -------
        list[Path]
            A list sorted based on the actual image hash of each duplicate
            sprite. Sprites that are modified from vanilla appear first,
            followed by vanilla sprites, then finally sprites that are unloaded.

        """

        def order_by_modification(file: Path) -> int:
            if file not in self.__sprites:
                return 2
            image_hash = str(self.__sprites[file].image_hash)
            return 1 if image_hash == vanilla_hash else 0

        return sorted(
            filter(lambda p: p in self.__sprites, self.duplicates[vanilla_hash]),
            key=order_by_modification,
        )

    def check_completion(self, duplicates: Iterable[Path], vanilla_hash: str) -> bool:
        """
        Determines whether a set of duplicate sprites is complete.

        Parameters
        ----------
        duplicates : Iterable[Path]
            A sequence of paths to duplicate sprites to include in the check.
        vanilla_hash : str
            The vanilla image hash of the duplicate sprites.

        Returns
        -------
        bool
            True if all sprites have the same image hash, and that hash is not
            identical to the vanilla value. False otherwise.

        """
        prev_hash = ""
        for path in map(self.sprite_path.joinpath, duplicates):
            if path not in self.__sprites:
                continue
            sprite = self.__sprites[path]
            curr_hash = str(sprite.image_hash)
            if not prev_hash:
                prev_hash = curr_hash
            elif curr_hash != prev_hash or curr_hash == vanilla_hash:
                return False
        return True

    def search_sprites(self, animation_name: str, sprite_name: str) -> Iterable[Path]:
        """
        Yields paths to sprites from a given animation with a given name.

        Parameters
        ----------
        animation_name : str
            The animation to search in.
        sprite_name : str
            The name of the sprite.

        Yields
        ------
        Iterable[Path]
            A sequence of paths to sprites that satisfy the search query.

        """

        for path in self.__s_by_animation[animation_name]:
            if sprite_name in str(path):
                yield path

    def loaded_animations(self, collections: dict[str, bool]) -> Iterable[str]:
        """
        Returns all animations that are loaded and in an enabled collection.

        Parameters
        ----------
        collections : dict[str, bool]
            A mapping from collection names to the enabled/disabled state.

        Returns
        -------
        Iterable[str]
            A sequence of names of the loaded and enabled animations.

        """
        return (
            anim
            for anim, paths in self.__s_by_animation.items()
            if all(
                collections.get(self.__sprites[path].collection, False)
                for path in paths
            )
        )
