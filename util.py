from math import ceil, log2
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")
U = TypeVar("U")


def lunique(seq: Iterable[T]) -> list[T]:
    return list(dict.fromkeys(seq))


def lmap(func: Callable[[T], U], seq: Iterable[T]) -> list[U]:
    return list(map(func, seq))


def first(seq: Iterable[T], condition: Callable[[T], bool] = lambda x: True) -> T:
    return next(x for x in seq if condition(x))


def min_dimension(l: int) -> int:
    return 2 ** ceil(log2(l - 1))
