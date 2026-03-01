# main.py
from __future__ import annotations

import math
from typing import Dict, List, Tuple, Optional

from algorithms.area_partition import build_area_partition, Block
from algorithms.level_dist import inter_layer_distances
from data_structure import Node
from visualize import visualize_grid


# -----------------------------
# 基本工具
# -----------------------------
def node_layer(node_id: int) -> int:
    if node_id < 1:
        raise ValueError("node_id must be >= 1")
    return int(math.floor(math.log2(node_id))) + 1


def parent_id(node_id: int) -> int:
    return node_id // 2


def parent_child_dist(parent_xy: Tuple[int, int], child_xy: Tuple[int, int]) -> int:
    px, py = parent_xy
    cx, cy = child_xy
    return abs(px - cx) + abs(py - cy)


def in_block(b: Block, x: int, y: int) -> bool:
    return (b.x0 <= x <= b.x1) and (b.y0 <= y <= b.y1)


def place_node_at(grid, node_id: int, router_id: int, core_id: int, xy: Tuple[int, int]) -> Node:
    x, y = xy
    if grid.is_used(x, y):
        raise RuntimeError(f"({x},{y}) already used")
    grid.place(x, y, router_id)  # cell 存 router_id
    return Node(x=x, y=y, router_id=router_id, core_id=core_id)


def remove_node_at(grid, xy: Tuple[int, int]) -> None:
    x, y = xy
    grid.remove(x, y)


def candidates_for_node(
    grid,
    blocks: Dict[int, Block],
    node_id: int,
    parent_xy: Tuple[int, int],
    target_dist: int,
) -> List[Tuple[int, int]]:
    b = blocks[node_id]
    cands: List[Tuple[int, int]] = []
    for x in range(b.x0, b.x1 + 1):
        for y in range(b.y0, b.y1 + 1):
            if grid.is_used(x, y):
                continue
            if parent_child_dist(parent_xy, (x, y)) == target_dist:
                cands.append((x, y))
    return cands


def solve(num: int):
    # ------------------------------------------------------------
    # 動態 blocks：子節點的 block 由「父節點座標」決定哪一半給 2i
    # ------------------------------------------------------------
    # 只在 solve 內做 local import，避免你要改動檔案其他地方的 import
    from algorithms.area_partition import Grid, grid_shape, split_block

    if num < 4 or (num & (num - 1)) != 0:
        raise ValueError("num must be power of two and >= 4 (e.g., 16, 32, ...)")

    # 建 grid
    W, H = grid_shape(num)
    grid = Grid(W, H)

    # 距離規則
    n_layers, dists = inter_layer_distances(num)
    d_last = dists[-1]

    placed: Dict[int, Node] = {}
    blocks: Dict[int, Block] = {}

    # start_axis：沿用你原本 area_partition 的慣例（W>H 先切 x，否則先切 y）
    start_axis = "x" if W > H else "y"

    def other_axis(axis: str) -> str:
        return "y" if axis == "x" else "x"

    def axis_for_node(nid: int) -> str:
        """nid 這一層用哪個 axis 來切它的 block（交錯 x/y）"""
        lyr = node_layer(nid)  # root=1
        return start_axis if (lyr % 2 == 1) else other_axis(start_axis)

    def split_block_follow_parent(b: Block, axis: str, parent_xy: Tuple[int, int]) -> Tuple[Block, Block]:
        """
        回傳 (block_for_small_child, block_for_big_child)
        規則：小的子節點(2i) 一定拿「包含 parent_xy」的那一半。
        """
        px, py = parent_xy
        c1, c2 = split_block(b, axis)  # 原本規則：c1=左/上, c2=右/下（依 split_block 實作）

        def inside(bb: Block) -> bool:
            return (bb.x0 <= px <= bb.x1) and (bb.y0 <= py <= bb.y1)

        # 若 parent 在 c2，就交換，讓小孩拿到包含 parent 的那半
        if inside(c2) and not inside(c1):
            return c2, c1
        return c1, c2

    # ------------------------------------------------------------
    # 1) 初始化 root block + 固定 root 位置
    # ------------------------------------------------------------
    blocks[1] = Block(0, W - 1, 0, H - 1)

    fixed_x = 1
    top_y = grid.height - 1
    root_xy = (fixed_x, top_y)
    if not in_block(blocks[1], fixed_x, top_y):
        raise RuntimeError("node1 固定點不在 block1 內")
    placed[1] = place_node_at(grid, 1, router_id=1, core_id=-1, xy=root_xy)

    # root 放好 → 立刻切出 blocks[2], blocks[3]（依 root 座標決定 2i 在哪半）
    b2, b3 = split_block_follow_parent(blocks[1], axis_for_node(1), (placed[1].x, placed[1].y))
    blocks[2] = b2
    blocks[3] = b3

    # ------------------------------------------------------------
    # 2) Part 1：放 internal nodes（2 .. num//2 - 1）
    #    並在放好每個 nid 後，動態切出它的 children blocks
    # ------------------------------------------------------------
    internal_end = (num // 2) - 1
    orderA = list(range(2, internal_end + 1))

    # leaf parents 範圍：num//4 .. num//2 - 1（例如 num=16 -> 4..7）
    leaf_parent_start = num // 4

    def dfs_blocks(idx: int) -> bool:
        if idx == len(orderA):
            return True

        nid = orderA[idx]
        pid = parent_id(nid)
        if pid not in placed:
            return False
        if nid not in blocks:
            # 正常不應該發生：pid 放好時就會把孩子 blocks 切出來
            return False

        parent_xy = (placed[pid].x, placed[pid].y)

        lyr = node_layer(nid)
        target_dist = dists[lyr - 2]  # layer2 用 dists[0] ...

        cands = candidates_for_node(grid, blocks, nid, parent_xy, target_dist)
        for xy in cands:
            placed[nid] = place_node_at(grid, nid, router_id=nid, core_id=-1, xy=xy)

            # 若 nid 還沒到 leaf_parent（代表還需要切出下一層的 blocks）
            created_children = False
            if nid < leaf_parent_start:
                axis = axis_for_node(nid)
                small_b, big_b = split_block_follow_parent(blocks[nid], axis, (placed[nid].x, placed[nid].y))
                blocks[nid * 2] = small_b
                blocks[nid * 2 + 1] = big_b
                created_children = True

            if dfs_blocks(idx + 1):
                return True

            # 回朔
            remove_node_at(grid, xy)
            del placed[nid]
            if created_children:
                blocks.pop(nid * 2, None)
                blocks.pop(nid * 2 + 1, None)

        return False

    if not dfs_blocks(0):
        raise RuntimeError("blocks 節點放置失敗（internal nodes）")

    # ------------------------------------------------------------
    # 3) Part 2：放 leaf（沿用你原本作法）
    #    leaf parents 就是 num//4 .. num//2 - 1
    # ------------------------------------------------------------
    leaf_parents = list(range(num // 4, num // 2))

    def leaf_candidates_in_parent_block(parent_id_: int) -> List[Tuple[int, int]]:
        """在 parent 的 2×2 block 中找距離 parent 座標 = d_last 的空格"""
        b = blocks[parent_id_]
        pxy = (placed[parent_id_].x, placed[parent_id_].y)

        cands = []
        for x in range(b.x0, b.x1 + 1):
            for y in range(b.y0, b.y1 + 1):
                if grid.is_used(x, y):
                    continue
                if parent_child_dist(pxy, (x, y)) == d_last:
                    cands.append((x, y))
        return cands

    def dfs_leaf(parent_idx: int) -> bool:
        if parent_idx == len(leaf_parents):
            return True

        pid = leaf_parents[parent_idx]
        c1, c2 = pid * 2, pid * 2 + 1

        cands = leaf_candidates_in_parent_block(pid)
        for i in range(len(cands)):
            xy1 = cands[i]
            placed[c1] = place_node_at(grid, c1, router_id=c1, core_id=-1, xy=xy1)

            cands2 = leaf_candidates_in_parent_block(pid)
            for xy2 in cands2:
                if xy2 == xy1:
                    continue
                placed[c2] = place_node_at(grid, c2, router_id=c2, core_id=-1, xy=xy2)

                if dfs_leaf(parent_idx + 1):
                    return True

                remove_node_at(grid, xy2)
                del placed[c2]

            remove_node_at(grid, xy1)
            del placed[c1]

        return False

    if not dfs_leaf(0):
        raise RuntimeError("leaf 放置失敗（在 2×2 block 內找 dist[-1] 位置）")

    # -------------------------
    # Part 3: 放最後一個router
    #
    # -------------------------
    empty_cells = []
    for x in range(grid.width):
        for y in range(grid.height):
            if not grid.is_used(x, y):
                empty_cells.append((x, y))

    if len(empty_cells) != 1:
        raise RuntimeError(f"預期只剩 1 個空位，但找到 {len(empty_cells)} 個：{empty_cells}")

    last_xy = empty_cells[0]
    last_router_id = num  # num=16 -> router16
    placed[last_router_id] = place_node_at(
        grid,
        node_id=last_router_id,  # 這裡用 16 當 key，剛好也對齊 router_id
        router_id=last_router_id,
        core_id=-1,  # 之後 solve_interconnect 會用 assign_router 把 core_id 補上
        xy=last_xy
    )

    return placed, grid

def main():
    num = 16
    placed, grid = solve(num)
    print(placed)
    visualize_grid(grid)

if __name__ == '__main__':
    main()