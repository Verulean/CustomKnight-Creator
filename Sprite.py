from dataclasses import dataclass
from pathlib import Path
from PIL import Image
from typing import Optional


@dataclass
class Sprite:
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
        self.__update_file()
        return self.__hash

    @property
    def content(self) -> Image.Image:
        self.__update_file()
        return self.__content

    @property
    def animation(self) -> str:
        return self.path.parent.name
