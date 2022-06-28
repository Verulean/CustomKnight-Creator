"""
This module implements a Sprite object for storing position data for, and the
content-based hash of, a single image/sprite.
"""
from dataclasses import dataclass
from pathlib import Path
from PIL import Image
from typing import Optional


@dataclass
class Sprite:
    """
    The Sprite class stores details of the position and orientation of a sprite
    within a CustomKnight spritesheet. Sprite objects also track the state of
    the underlying sprite image file, updating the sprite content and hash
    when the file has been modified.
    """

    identifier: int
    x: int
    y: int
    xr: int
    yr: int
    w: int
    h: int
    flipped: bool
    path: Path
    collection: str
    mtime: Optional[float] = None

    def __update_file(self) -> None:
        """
        Checks if the source image has been modified, and recomputes the
        cropped sprite content and resulting image hash if so.

        Returns
        -------
        None.

        """
        mtime: float = self.path.stat().st_mtime
        if mtime == self.mtime:
            return
        self.mtime = mtime

        im = Image.open(self.path)
        w = im.size[1]
        self.__content = im.crop(
            (self.xr, w - self.yr - self.h, self.xr + self.w, w - self.yr)
        )
        self.__hash = hash(tuple(map(tuple, self.__content.getdata())))

    @property
    def image_hash(self) -> int:
        """
        Getter for the image hash of the sprite content in the image file.

        Returns
        -------
        int
            The current hash.

        """
        self.__update_file()
        return self.__hash

    @property
    def content(self) -> Image.Image:
        """
        Getter for the sprite content of the image file.

        Returns
        -------
        Image
            A PIL image with the underlying image file, cropped to the sprite
            borders.

        """
        self.__update_file()
        return self.__content

    @property
    def animation(self) -> str:
        """
        Returns the name of the animation the sprite is in.

        Returns
        -------
        str
            The animation name.

        """
        return self.path.parent.name
