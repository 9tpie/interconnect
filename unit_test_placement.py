# main.py

"""
測試第一層到第二層探索
"""

from __future__ import annotations

import math
from typing import Dict, Tuple, Optional

from algorithms.area_partition import build_area_partition, Block
from algorithms.level_dist import inter_layer_distances
from data_structure import Node
from visualize import visualize_grid

def node_layer(node_id: int) -> int:
    """Heap 編號 (1-based) 對應 layer：layer = floor(log2(id)) + 1"""
    if node_id < 1:
        raise ValueError("node_id 必須 >= 1")
    return int(math.floor(math.log2(node_id))) + 1


def parent_child_dist(parent_xy: Tuple[int, int], child_xy: Tuple[int, int]) -> int:
    """父子距離：x方向差 + y方向差"""
    px, py = parent_xy
    cx, cy = child_xy
    return abs(px - cx) + abs(py - cy)


def place_node_at(grid, node_id: int, router_id: int, core_id: int, xy: Tuple[int, int]) -> Node:
    """在 grid 放一個 node（grid cell 只存 router_id）"""
    x, y = xy
    if grid.is_used(x, y):
        raise RuntimeError(f"座標 ({x},{y}) 已被使用，無法放置 node{node_id}")
    grid.place(x, y, router_id)
    return Node(x=x, y=y, router_id=router_id, core_id=core_id)


def find_empty_in_block_with_exact_parent_dist(
    grid,
    b: Block,
    parent_xy: Tuple[int, int],
    target_dist: int,
) -> Optional[Tuple[int, int]]:
    """在 block 內找空位，使得 dist(parent, child) == target_dist；找不到回 None"""
    for x in range(b.x0, b.x1 + 1):
        for y in range(b.y0, b.y1 + 1):
            if grid.is_used(x, y):
                continue
            if parent_child_dist(parent_xy, (x, y)) == target_dist:
                return (x, y)
    return None


def main():
    num = int(input("輸入 num (2 的次方，例如 16/32): ").strip())

    # (1) area partition：產生 grid + node_id -> 候選 block
    grid, blocks = build_area_partition(num, leaf_area=4)

    # 印出候選區域
    for nid in sorted(blocks.keys()):
        b = blocks[nid]
        print(f"{nid}: x={b.x0}~{b.x1}, y={b.y0}~{b.y1}, area={b.area}")
    print()

    # (2) level dist：相鄰 layer 距離
    n_layers, dists = inter_layer_distances(num)
    for i, d in enumerate(dists, start=1):
        print(f"Layer {i} -> Layer {i+1}: dist = {d}")
    print()

    # (3) node2、node3 必須在 layer2
    if 2 not in blocks or 3 not in blocks:
        raise RuntimeError("此 num 的 area_partition 結果沒有 node2 或 node3")
    if node_layer(2) != 2 or node_layer(3) != 2:
        raise RuntimeError("node2 / node3 不在 layer2，請確認節點編號與 layer 定義")

    # (4) node1 固定位置：x=2, y=最上方
    if 1 not in blocks:
        raise RuntimeError("area_partition 輸出沒有 node1")

    root_block = blocks[1]
    fixed_x = 1
    top_y = grid.height - 1
    root_xy = (fixed_x, top_y)

    # 必須在 node1 的候選區域內
    if not (root_block.x0 <= fixed_x <= root_block.x1 and root_block.y0 <= top_y <= root_block.y1):
        raise RuntimeError(
            f"node1 固定座標 ({fixed_x},{top_y}) 不在 node1 候選區域內："
            f"x={root_block.x0}~{root_block.x1}, y={root_block.y0}~{root_block.y1}"
        )

    node1 = place_node_at(grid, node_id=1, router_id=1, core_id=-1, xy=root_xy)
    parent_xy = (node1.x, node1.y)

    # (5) Layer1->Layer2 距離，要求 node2/node3 與 node1 的父子距離都等於 dist12
    dist12 = dists[0]

    placed: Dict[int, Node] = {1: node1}
    for nid in (2, 3):
        b = blocks[nid]
        xy = find_empty_in_block_with_exact_parent_dist(grid, b, parent_xy, dist12)
        if xy is None:
            raise RuntimeError(
                f"node{nid} 在候選區域 x={b.x0}~{b.x1}, y={b.y0}~{b.y1} 內找不到空位，"
                f"使得 dist(node1,node{nid}) == {dist12}"
            )
        placed[nid] = place_node_at(grid, node_id=nid, router_id=nid, core_id=-1, xy=xy)

    # (6) 印結果
    print(f"node1 (layer{node_layer(1)}) fixed at {parent_xy}")
    for nid in (2, 3):
        n = placed[nid]
        d = parent_child_dist(parent_xy, (n.x, n.y))
        b = blocks[nid]
        print(
            f"node{nid} (layer{node_layer(nid)}) at ({n.x},{n.y}), "
            f"dist(node1,node{nid})={d}, "
            f"block: x={b.x0}~{b.x1}, y={b.y0}~{b.y1}"
        )

    print("\nGrid used map (1=used, 0=empty):")
    print(grid)
    visualize_grid(grid)

if __name__ == "__main__":
    main()
