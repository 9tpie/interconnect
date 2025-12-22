#!/usr/bin/env python3
"""迭代式 DFS 測試腳本 - 含可視化"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

# ============= 基本資料結構 =============

@dataclass
class Node:
    x: int
    y: int
    router_id: int
    core_id: int

@dataclass(frozen=True)
class Block:
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


class Grid:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.cells = [[None for _ in range(height)] for _ in range(width)]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_used(self, x: int, y: int) -> bool:
        return self.cells[x][y] is not None

    def place(self, x: int, y: int, value):
        self.cells[x][y] = value

    def remove(self, x: int, y: int):
        self.cells[x][y] = None


# ============= 輔助函數 =============

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

def grid_shape(num: int) -> Tuple[int, int]:
    k = int(math.log2(num))
    W = 2 ** ((k + 1) // 2)
    H = 2 ** (k // 2)
    return W, H

def split_block(b: Block, axis: str) -> Tuple[Block, Block]:
    if axis == "x":
        mid = (b.x0 + b.x1) // 2
        left = Block(b.x0, mid, b.y0, b.y1)
        right = Block(mid + 1, b.x1, b.y0, b.y1)
        return left, right
    if axis == "y":
        mid = (b.y0 + b.y1) // 2
        top = Block(b.x0, b.x1, mid + 1, b.y1)
        bottom = Block(b.x0, b.x1, b.y0, mid)
        return top, bottom
    raise ValueError("axis must be 'x' or 'y'")

def node_level(node_id: int) -> int:
    return int(math.log2(node_id)) + 1

def build_area_partition(num: int, leaf_area: int = 4) -> Tuple[Grid, Dict[int, Block]]:
    W, H = grid_shape(num)
    grid = Grid(W, H)
    start_axis = "x" if W > H else "y"
    blocks: Dict[int, Block] = {}
    root = Block(0, W - 1, 0, H - 1)
    q = [(1, root)]
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

def inter_layer_distances(num_of_core: int) -> Tuple[int, List[int]]:
    n = int(math.log2(num_of_core))
    distances: List[int] = []
    for i in range(1, n):
        t = n - i + 1
        exp = (t - 1) // 2
        d = 2 ** exp
        distances.append(d)
    return n, distances

def place_node_at(grid, node_id: int, router_id: int, core_id: int, xy: Tuple[int, int]) -> Node:
    x, y = xy
    grid.place(x, y, router_id)
    return Node(x=x, y=y, router_id=router_id, core_id=core_id)

def remove_node_at(grid, xy: Tuple[int, int]) -> None:
    x, y = xy
    grid.remove(x, y)

def candidates_for_node(grid, blocks, node_id, parent_xy, target_dist):
    b = blocks[node_id]
    cands = []
    for x in range(b.x0, b.x1 + 1):
        for y in range(b.y0, b.y1 + 1):
            if grid.is_used(x, y):
                continue
            if parent_child_dist(parent_xy, (x, y)) == target_dist:
                cands.append((x, y))
    return cands


# ============= 迭代式 solve =============

def solve_iterative(num: int):
    """使用迭代式 DFS 的 solve 函數"""
    grid, blocks = build_area_partition(num, leaf_area=4)
    n_layers, dists = inter_layer_distances(num)
    d_last = dists[-1]

    placed: Dict[int, Node] = {}

    # 固定 root
    root_block = blocks[1]
    fixed_x = 1
    top_y = grid.height - 1
    root_xy = (fixed_x, top_y)
    if not in_block(root_block, fixed_x, top_y):
        raise RuntimeError("node1 固定點不在 block1 內")
    placed[1] = place_node_at(grid, 1, router_id=1, core_id=-1, xy=root_xy)

    block_node_ids = sorted(blocks.keys())
    orderA = [nid for nid in block_node_ids if nid != 1]

    def dfs_blocks_iter() -> bool:
        stack = [(0, None, None, False)]
        while stack:
            idx, cands_iter, placed_xy, need_backtrack = stack[-1]
            if idx == len(orderA):
                return True
            nid = orderA[idx]
            pid = parent_id(nid)
            if pid not in placed:
                stack.pop()
                continue
            if need_backtrack and placed_xy is not None:
                remove_node_at(grid, placed_xy)
                del placed[nid]
                placed_xy = None
            if cands_iter is None:
                parent_xy = (placed[pid].x, placed[pid].y)
                lyr = node_layer(nid)
                target_dist = dists[lyr - 2]
                cands = candidates_for_node(grid, blocks, nid, parent_xy, target_dist)
                cands_iter = iter(cands)
                stack[-1] = (idx, cands_iter, None, False)
            try:
                xy = next(cands_iter)
                placed[nid] = place_node_at(grid, nid, router_id=nid, core_id=-1, xy=xy)
                stack[-1] = (idx, cands_iter, xy, True)
                stack.append((idx + 1, None, None, False))
            except StopIteration:
                stack.pop()
        return False

    if not dfs_blocks_iter():
        raise RuntimeError("blocks 節點放置失敗")

    leaf_parents = [nid for nid, b in blocks.items() if b.area <= 4]
    leaf_parents = sorted(leaf_parents)

    def leaf_candidates_in_parent_block(parent_id_: int):
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

    def dfs_leaf_iter() -> bool:
        stack = [(0, None, None, None, None, False)]
        while stack:
            parent_idx, cands1_iter, xy1, cands2_iter, xy2, need_backtrack = stack[-1]
            if parent_idx == len(leaf_parents):
                return True
            pid = leaf_parents[parent_idx]
            c1, c2 = pid * 2, pid * 2 + 1
            if need_backtrack and xy2 is not None:
                remove_node_at(grid, xy2)
                del placed[c2]
                xy2 = None
            if cands1_iter is None:
                cands = leaf_candidates_in_parent_block(pid)
                cands1_iter = iter(cands)
                stack[-1] = (parent_idx, cands1_iter, None, None, None, False)
            if xy1 is None:
                try:
                    xy1 = next(cands1_iter)
                    placed[c1] = place_node_at(grid, c1, router_id=c1, core_id=-1, xy=xy1)
                    cands2 = leaf_candidates_in_parent_block(pid)
                    cands2_iter = iter(cands2)
                    stack[-1] = (parent_idx, cands1_iter, xy1, cands2_iter, None, False)
                except StopIteration:
                    stack.pop()
                    continue
            try:
                xy2 = next(cands2_iter)
                if xy2 == xy1:
                    continue
                placed[c2] = place_node_at(grid, c2, router_id=c2, core_id=-1, xy=xy2)
                stack[-1] = (parent_idx, cands1_iter, xy1, cands2_iter, xy2, True)
                stack.append((parent_idx + 1, None, None, None, None, False))
            except StopIteration:
                remove_node_at(grid, xy1)
                del placed[c1]
                stack[-1] = (parent_idx, cands1_iter, None, None, None, False)
        return False

    if not dfs_leaf_iter():
        raise RuntimeError("leaf 放置失敗")

    return placed, grid


# ============= 可視化 =============

def visualize_placement(placed: Dict[int, Node], grid, num: int, save_path: str = None):
    """使用 matplotlib 可視化放置結果"""
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # 繪製 grid
    for x in range(grid.width + 1):
        ax.axvline(x, color='lightgray', linewidth=0.5)
    for y in range(grid.height + 1):
        ax.axhline(y, color='lightgray', linewidth=0.5)
    
    # 根據層級分配顏色
    colors = plt.cm.Set3(range(12))
    
    # 繪製節點
    for nid, node in placed.items():
        layer = node_layer(nid)
        color = colors[layer % len(colors)]
        
        # 繪製方塊
        rect = patches.Rectangle(
            (node.x, node.y), 1, 1,
            linewidth=2,
            edgecolor='black',
            facecolor=color,
            alpha=0.7
        )
        ax.add_patch(rect)
        
        # 標註節點 ID
        ax.text(
            node.x + 0.5, node.y + 0.5,
            str(nid),
            ha='center', va='center',
            fontsize=8 if num > 32 else 10,
            fontweight='bold'
        )
    
    # 繪製 parent-child 連線
    for nid, node in placed.items():
        if nid == 1:
            continue
        pid = parent_id(nid)
        if pid in placed:
            parent_node = placed[pid]
            ax.plot(
                [node.x + 0.5, parent_node.x + 0.5],
                [node.y + 0.5, parent_node.y + 0.5],
                color='red', linewidth=1.5, alpha=0.6
            )
    
    ax.set_xlim(-0.5, grid.width + 0.5)
    ax.set_ylim(-0.5, grid.height + 0.5)
    ax.set_aspect('equal')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_title(f'Placement Result (num={num}, nodes={len(placed)})')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"圖片已儲存至: {save_path}")
    else:
        plt.show()
    
    plt.close()


# ============= 主程式 =============

def main():
    import sys
    
    # 預設測試 num=16
    num = 16
    if len(sys.argv) > 1:
        num = int(sys.argv[1])
    
    print(f"測試 num={num}")
    print("-" * 40)
    
    try:
        placed, grid = solve_iterative(num)
        print(f"✓ 成功放置 {len(placed)} 個節點")
        print(f"  Grid 大小: {grid.width}x{grid.height}")
        
        # 顯示放置結果
        print("\n放置結果:")
        for nid in sorted(placed.keys()):
            node = placed[nid]
            layer = node_layer(nid)
            print(f"  Node {nid:3d} (Layer {layer}): ({node.x}, {node.y})")
        
        # 可視化
        save_path = f"placement_num{num}.png"
        visualize_placement(placed, grid, num, save_path)
        
    except Exception as e:
        print(f"✗ 失敗: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
