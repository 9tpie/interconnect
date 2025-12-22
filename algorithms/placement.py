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
    grid, blocks = build_area_partition(num, leaf_area=4)  # 2x2 停止 :contentReference[oaicite:2]{index=2}
    n_layers, dists = inter_layer_distances(num)           # 16 -> [2,2,1] :contentReference[oaicite:3]{index=3}
    d_last = dists[-1]

    placed: Dict[int, Node] = {}

    # 固定 root（你原本固定方式）
    root_block = blocks[1]
    fixed_x = 1
    top_y = grid.height - 1
    root_xy = (fixed_x, top_y)
    if not in_block(root_block, fixed_x, top_y):
        raise RuntimeError("node1 固定點不在 block1 內")
    placed[1] = place_node_at(grid, 1, router_id=1, core_id=-1, xy=root_xy)

    # -------------------------
    # Part A: 放 blocks 節點 (1..7)
    # -------------------------
    block_node_ids = sorted(blocks.keys())
    orderA = [nid for nid in block_node_ids if nid != 1]

    def dfs_blocks(idx: int) -> bool:
        if idx == len(orderA):
            return True

        nid = orderA[idx]
        pid = parent_id(nid)
        if pid not in placed:
            return False
        parent_xy = (placed[pid].x, placed[pid].y)

        lyr = node_layer(nid)
        target_dist = dists[lyr - 2]  # layer2 用 dists[0] ... :contentReference[oaicite:4]{index=4}

        cands = candidates_for_node(grid, blocks, nid, parent_xy, target_dist)
        for xy in cands:
            placed[nid] = place_node_at(grid, nid, router_id=nid, core_id=-1, xy=xy)
            if dfs_blocks(idx + 1):
                return True
            remove_node_at(grid, xy)
            del placed[nid]
        return False

    if not dfs_blocks(0):
        raise RuntimeError("blocks 節點放置失敗（1..7）")

    # -------------------------
    # Part B: 放 leaf（在每個 2×2 block 內找 cell）
    # leaf node id: 2*pid, 2*pid+1（對應 8..15）
    # -------------------------
    leaf_parents = [nid for nid, b in blocks.items() if b.area <= 4]  # 2x2 leaf blocks :contentReference[oaicite:5]{index=5}
    leaf_parents = sorted(leaf_parents)

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
        # 兩個 leaf id（例如 pid=4 -> 8,9）
        c1, c2 = pid * 2, pid * 2 + 1

        cands = leaf_candidates_in_parent_block(pid)
        # 我們需要挑兩個不同 cell
        for i in range(len(cands)):
            xy1 = cands[i]
            placed[c1] = place_node_at(grid, c1, router_id=c1, core_id=-1, xy=xy1)

            cands2 = leaf_candidates_in_parent_block(pid)  # 更新後再抓一次
            for xy2 in cands2:
                if xy2 == xy1:
                    continue
                placed[c2] = place_node_at(grid, c2, router_id=c2, core_id=-1, xy=xy2)

                if dfs_leaf(parent_idx + 1):
                    return True

                # 回朔 leaf2
                remove_node_at(grid, xy2)
                del placed[c2]

            # 回朔 leaf1
            remove_node_at(grid, xy1)
            del placed[c1]

        return False

    if not dfs_leaf(0):
        raise RuntimeError("leaf 放置失敗（在 2×2 block 內找 dist[-1] 位置）")

    return placed, grid