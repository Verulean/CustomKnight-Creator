"""
This module provides miscellaneous utility functions for CustomKnight Creator.
"""
from math import ceil, log2
from typing import Callable, Hashable, Iterable, TypeVar, cast

T = TypeVar("T")
U = TypeVar("U")


def lunique(seq: Iterable[Hashable]) -> list[Hashable]:
    """
    Returns a list of unique elements of an iterable, respecting the original
    element order.

    Parameters
    ----------
    seq : Iterable[Hashable]
        The sequence to trim duplicate elements from.

    Returns
    -------
    list[Hashable]
        A stably-ordered list of unique elements of `seq`.

    """
    return list(dict.fromkeys(seq))


def lmap(func: Callable[[T], U], seq: Iterable[T]) -> list[U]:
    """
    Returns a list with the results of a function map.

    Parameters
    ----------
    func : Callable[[T], U]
        The function to map.
    seq : Iterable[T]
        The sequence of arguments to pass to `func`.

    Returns
    -------
    list[U]
        A list containing the result of `func` called on each successive
        element in `seq`.

    """
    return list(map(func, seq))


def first(seq: Iterable[T], condition: Callable[[T], bool] = lambda x: True) -> T:
    """
    Returns the first element of an iterable satisfying an optional condition
    function.

    Parameters
    ----------
    seq : Iterable[T]
        A sequence of objects.
    condition : Callable[[T], bool], optional
        A function that returns whether an element is valid to be chosen. The
        default is lambda x: True.

    Returns
    -------
    T
        The first element in `seq` for which `condition` returns True.

    """
    return next(x for x in seq if condition(x))


def min_dimension(l: int) -> int:
    """
    Returns the spritesheet dimension needed to accommodate a given length.

    Parameters
    ----------
    l : int
        The length, along a given dimension, of the packed sprites.

    Returns
    -------
    int
        The appropriate spritesheet dimension to fit the sprites.

    """
    return cast(int, 2 ** ceil(log2(l - 1)))
