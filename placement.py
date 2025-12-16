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


def solve(num: int) -> Tuple[Dict[int, Node], object]:
    # 1) area partition
    grid, blocks = build_area_partition(num, leaf_area=4)

    # 2) layer distances
    n_layers, dists = inter_layer_distances(num)  # length = n_layers-1（但最後一步我們改用 1）

    # ✅ 現在要放到 leaf：探索 1 ~ n_layers
    max_layer_to_place = n_layers

    # 3) 決定要放哪些節點（存在於 blocks 且 layer <= n_layers）
    node_ids = sorted([nid for nid in blocks.keys() if node_layer(nid) <= max_layer_to_place])
    if 1 not in node_ids:
        raise RuntimeError("blocks does not contain node1")

    # 4) 固定 node1 在 x=1, y=最上方
    root_block = blocks[1]
    fixed_x = 1
    top_y = grid.height - 1
    root_xy = (fixed_x, top_y)

    if not in_block(root_block, fixed_x, top_y):
        raise RuntimeError(
            f"node1 fixed ({fixed_x},{top_y}) not in its block "
            f"x={root_block.x0}~{root_block.x1}, y={root_block.y0}~{root_block.y1}"
        )
    if grid.is_used(*root_xy):
        raise RuntimeError(f"node1 fixed ({fixed_x},{top_y}) already used")

    placed: Dict[int, Node] = {1: place_node_at(grid, 1, router_id=1, core_id=-1, xy=root_xy)}

    # 5) 放置順序：id 遞增（排除 node1）
    order = [nid for nid in node_ids if nid != 1]

    # 6) 回朔 DFS
    def dfs(idx: int) -> bool:
        if idx == len(order):
            return True

        nid = order[idx]
        lyr = node_layer(nid)

        pid = parent_id(nid)
        if pid not in placed:
            return False  # 理論上不會發生（因為上層 id 較小會先放）

        pxy = (placed[pid].x, placed[pid].y)

        # ✅ 距離規則：
        # - 若 nid 在 leaf 層 (layer == n_layers)，則父子距離固定為 1
        # - 否則用 level_dist 的相鄰層距離：Layer(lyr-1)->Layer(lyr) = dists[lyr-2]
        if lyr == n_layers:
            target_dist = 1
        else:
            target_dist = dists[lyr - 2]

        cands = candidates_for_node(grid, blocks, nid, pxy, target_dist)
        if not cands:
            return False

        for xy in cands:
            placed[nid] = place_node_at(grid, nid, router_id=nid, core_id=-1, xy=xy)
            if dfs(idx + 1):
                return True
            remove_node_at(grid, xy)
            del placed[nid]

        return False

    if not dfs(0):
        raise RuntimeError("找不到能讓 1~n 層（含 leaf）全部放置完成的解（已完整回朔）")

    return placed, grid


def main():
    num = int(input("輸入 num (2 的次方，例如 16/32): ").strip())

    placed, grid = solve(num)

    print("=== Placement Result (1 ~ n layers, leaf included) ===")
    for nid in sorted(placed.keys()):
        n = placed[nid]
        print(f"node{nid:>3}  layer={node_layer(nid)}  at ({n.x},{n.y})  router_id={n.router_id}")

    print("\nGrid used map (1=used, 0=empty):")
    print(grid)
    visualize_grid(grid)

if __name__ == "__main__":
    main()