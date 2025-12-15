from dataclasses import dataclass
from math import log2
from typing import Dict, Tuple, Optional

from data_structure.grid import Grid


@dataclass(frozen=True)
class Block:
    """一個矩形區塊（含邊界）"""
    x0: int
    x1: int
    y0: int
    y1: int

    @property
    def w(self) -> int:
        return self.x1 - self.x0 + 1

    @property
    def h(self) -> int:
        return self.y1 - self.y0 + 1

    @property
    def area(self) -> int:
        return self.w * self.h


def _is_pow2(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def grid_shape(num: int) -> Tuple[int, int]:
    """
    依照你圖的模式把 num 排成 W x H（都為 2 的次方，且 W>=H）
    16 -> 4x4
    32 -> 8x4
    """
    if not _is_pow2(num):
        raise ValueError("num 必須是 2 的次方，例如 16, 32, 64 ...")

    k = int(log2(num))  # num=2^k
    W = 2 ** ((k + 1) // 2)  # ceil(k/2)
    H = 2 ** (k // 2)        # floor(k/2)
    return W, H


def split_block(b: Block, axis: str) -> Tuple[Block, Block]:
    """
    切割規則要對齊你的筆記：
    - axis='x'：切左右 (x0..mid) 與 (mid+1..x1)
    - axis='y'：切上下，且把「上半部(y大)」當作左子(2i)，下半部當右子(2i+1)
    """
    if axis == "x":
        mid = (b.x0 + b.x1) // 2
        left = Block(b.x0, mid, b.y0, b.y1)         # 2i
        right = Block(mid + 1, b.x1, b.y0, b.y1)    # 2i+1
        return left, right

    if axis == "y":
        mid = (b.y0 + b.y1) // 2
        top = Block(b.x0, b.x1, mid + 1, b.y1)      # 2i：上半部（y較大）
        bottom = Block(b.x0, b.x1, b.y0, mid)       # 2i+1：下半部
        return top, bottom

    raise ValueError("axis 必須是 'x' 或 'y'")


def node_level(node_id: int) -> int:
    return int(log2(node_id)) + 1


def build_area_partition(
    num: int,
    leaf_area: int = 4,
) -> Tuple[Grid, Dict[int, Block]]:
    """
    回傳:
      - grid: 依照 num 建好的 Grid
      - blocks: node_id -> Block(x0,x1,y0,y1)

    leaf_area=4 表示切到 2x2 就停止（符合你圖上的停止探索）
    """
    W, H = grid_shape(num)
    grid = Grid(W, H)

    start_axis = "x" if W > H else "y"  # 32: 先切x, 16: 先切y

    blocks: Dict[int, Block] = {}
    root = Block(0, W - 1, 0, H - 1)

    q = [(1, root)]  # (node_id, block)

    while q:
        nid, b = q.pop(0)
        blocks[nid] = b

        if b.area <= leaf_area:
            continue

        lvl = node_level(nid)
        axis = start_axis if (lvl % 2 == 1) else ("y" if start_axis == "x" else "x")

        c1, c2 = split_block(b, axis)
        q.append((nid * 2, c1))
        q.append((nid * 2 + 1, c2))

    return grid, blocks


def block_of_node(num: int, node_id: int, leaf_area: int = 4) -> Block:
    """如果你只想查單一 node_id 的區塊"""
    _, blocks = build_area_partition(num, leaf_area=leaf_area)
    if node_id not in blocks:
        raise ValueError(f"node_id={node_id} 不存在（可能超過停止探索的深度）")
    return blocks[node_id]


if __name__ == "__main__":
    num = int(input("輸入 num (2 的次方，例如 16/32): "))
    grid, blocks = build_area_partition(num, leaf_area=4)

    for nid in sorted(blocks.keys()):
        b = blocks[nid]
        print(f"{nid}: x={b.x0}~{b.x1}, y={b.y0}~{b.y1}, area={b.area}")
