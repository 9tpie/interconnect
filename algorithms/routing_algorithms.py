import math
from collections import defaultdict
from typing import List, Tuple


def xy_route_by_coord(
    src: Tuple[int, int],
    dst: Tuple[int, int],
) -> List[Tuple[int, int]]:
    sx, sy = src
    dx, dy = dst

    path: List[Tuple[int, int]] = [(sx, sy)]
    x, y = sx, sy

    # 先走 X
    while x != dx:
        x += 1 if dx > x else -1
        path.append((x, y))

    # 再走 Y
    while y != dy:
        y += 1 if dy > y else -1
        path.append((x, y))

    return path

def yx_route_by_coord(
    src: Tuple[int, int],
    dst: Tuple[int, int],
) -> List[Tuple[int, int]]:
    sx, sy = src
    dx, dy = dst

    path: List[Tuple[int, int]] = [(sx, sy)]
    x, y = sx, sy

    # 先走 Y
    while y != dy:
        y += 1 if dy > y else -1
        path.append((x, y))

    # 再走 X
    while x != dx:
        x += 1 if dx > x else -1
        path.append((x, y))

    return path