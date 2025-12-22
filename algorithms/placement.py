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

    def dfs_blocks_iter() -> bool:
        """
        迭代式 DFS 放置 blocks 節點。
        使用顯式 stack 避免遞迴深度限制。
        stack 元素: (idx, cands_iter, placed_xy, need_backtrack)
          - idx: 目前處理 orderA 的索引
          - cands_iter: 候選座標的迭代器 (或 None 表示尚未初始化)
          - placed_xy: 此層已放置的座標 (用於回溯時移除)
          - need_backtrack: 是否需要先清除再嘗試下一個
        """
        stack = [(0, None, None, False)]

        while stack:
            idx, cands_iter, placed_xy, need_backtrack = stack[-1]

            # 成功條件：所有節點都已放置
            if idx == len(orderA):
                return True

            nid = orderA[idx]
            pid = parent_id(nid)

            # 父節點必須已放置
            if pid not in placed:
                stack.pop()
                continue

            # 如果需要回溯（從子節點返回），先清除當前放置
            if need_backtrack and placed_xy is not None:
                remove_node_at(grid, placed_xy)
                del placed[nid]
                placed_xy = None

            # 初始化此層的候選列表
            if cands_iter is None:
                parent_xy = (placed[pid].x, placed[pid].y)
                lyr = node_layer(nid)
                target_dist = dists[lyr - 2]
                cands = candidates_for_node(grid, blocks, nid, parent_xy, target_dist)
                cands_iter = iter(cands)
                stack[-1] = (idx, cands_iter, None, False)

            # 嘗試下一個候選位置
            try:
                xy = next(cands_iter)
                # 放置此節點
                placed[nid] = place_node_at(grid, nid, router_id=nid, core_id=-1, xy=xy)
                stack[-1] = (idx, cands_iter, xy, True)  # 標記需要回溯
                # 推進到下一個節點
                stack.append((idx + 1, None, None, False))
            except StopIteration:
                # 無更多候選，回溯到上一層
                stack.pop()

        return False

    if not dfs_blocks_iter():
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

    def dfs_leaf_iter() -> bool:
        """
        迭代式 DFS 放置 leaf 節點。
        每個 parent 需放兩個 leaf (c1, c2)，使用雙層迭代。
        stack 元素: (parent_idx, cands1_iter, xy1, cands2_iter, xy2, need_backtrack)
          - parent_idx: 目前處理的 leaf_parents 索引
          - cands1_iter: c1 的候選迭代器
          - xy1: c1 放置的座標 (或 None)
          - cands2_iter: c2 的候選迭代器
          - xy2: c2 放置的座標 (或 None)
          - need_backtrack: 是否需要先清除 c2 再嘗試下一個
        """
        stack = [(0, None, None, None, None, False)]

        while stack:
            parent_idx, cands1_iter, xy1, cands2_iter, xy2, need_backtrack = stack[-1]

            # 成功條件
            if parent_idx == len(leaf_parents):
                return True

            pid = leaf_parents[parent_idx]
            c1, c2 = pid * 2, pid * 2 + 1

            # 如果需要回溯（從子節點返回），先清除 c2
            if need_backtrack and xy2 is not None:
                remove_node_at(grid, xy2)
                del placed[c2]
                xy2 = None

            # 階段 1: 初始化 c1 的候選
            if cands1_iter is None:
                cands = leaf_candidates_in_parent_block(pid)
                cands1_iter = iter(cands)
                stack[-1] = (parent_idx, cands1_iter, None, None, None, False)

            # 階段 2: 如果 c1 尚未放置，嘗試放置
            if xy1 is None:
                try:
                    xy1 = next(cands1_iter)
                    placed[c1] = place_node_at(grid, c1, router_id=c1, core_id=-1, xy=xy1)
                    # 初始化 c2 的候選
                    cands2 = leaf_candidates_in_parent_block(pid)
                    cands2_iter = iter(cands2)
                    stack[-1] = (parent_idx, cands1_iter, xy1, cands2_iter, None, False)
                except StopIteration:
                    # c1 無更多候選，回溯到上一個 parent
                    stack.pop()
                    continue

            # 階段 3: 嘗試放置 c2
            try:
                xy2 = next(cands2_iter)
                # 跳過與 xy1 相同的位置
                if xy2 == xy1:
                    continue
                placed[c2] = place_node_at(grid, c2, router_id=c2, core_id=-1, xy=xy2)
                stack[-1] = (parent_idx, cands1_iter, xy1, cands2_iter, xy2, True)  # 標記需要回溯
                # 推進到下一個 parent
                stack.append((parent_idx + 1, None, None, None, None, False))
            except StopIteration:
                # c2 無更多候選，回溯 c1 並嘗試下一個 c1 位置
                remove_node_at(grid, xy1)
                del placed[c1]
                stack[-1] = (parent_idx, cands1_iter, None, None, None, False)

        return False

    if not dfs_leaf_iter():
        raise RuntimeError("leaf 放置失敗（在 2×2 block 內找 dist[-1] 位置）")

    return placed, grid


def solve_optimized(num: int):
    """
    優化版放置演算法：使用 MRV + Forward Checking
    - MRV: 優先處理剩餘候選最少的節點
    - Forward Checking: 放置後立即檢查是否導致其他節點無解
    """
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

    # -------------------------
    # Part A: 放 blocks 節點 (使用 MRV + Forward Checking)
    # -------------------------
    block_node_ids = sorted(blocks.keys())
    unplaced_blocks = set(nid for nid in block_node_ids if nid != 1)

    def get_block_candidates(nid: int) -> List[Tuple[int, int]]:
        """取得節點的有效候選位置"""
        pid = parent_id(nid)
        if pid not in placed:
            return []
        parent_xy = (placed[pid].x, placed[pid].y)
        lyr = node_layer(nid)
        target_dist = dists[lyr - 2]
        return candidates_for_node(grid, blocks, nid, parent_xy, target_dist)

    def forward_check_blocks() -> bool:
        """檢查所有未放置節點是否還有候選"""
        for nid in unplaced_blocks:
            pid = parent_id(nid)
            if pid in placed and len(get_block_candidates(nid)) == 0:
                return False
        return True

    def select_mrv_block() -> Optional[int]:
        """選擇剩餘候選最少的節點 (MRV)"""
        eligible = [nid for nid in unplaced_blocks if parent_id(nid) in placed]
        if not eligible:
            return None
        return min(eligible, key=lambda nid: len(get_block_candidates(nid)))

    def dfs_blocks_mrv() -> bool:
        if not unplaced_blocks:
            return True

        nid = select_mrv_block()
        if nid is None:
            return False

        cands = get_block_candidates(nid)
        if not cands:
            return False

        for xy in cands:
            placed[nid] = place_node_at(grid, nid, router_id=nid, core_id=-1, xy=xy)
            unplaced_blocks.remove(nid)

            if forward_check_blocks() and dfs_blocks_mrv():
                return True

            remove_node_at(grid, xy)
            del placed[nid]
            unplaced_blocks.add(nid)

        return False

    if not dfs_blocks_mrv():
        raise RuntimeError("blocks 節點放置失敗")

    # -------------------------
    # Part B: 放 leaf (使用 MRV + Forward Checking)
    # -------------------------
    leaf_parents = sorted([nid for nid, b in blocks.items() if b.area <= 4])
    unplaced_leaves: Dict[int, List[int]] = {}
    for pid in leaf_parents:
        unplaced_leaves[pid] = [pid * 2, pid * 2 + 1]

    def get_leaf_candidates(pid: int) -> List[Tuple[int, int]]:
        """取得 leaf 的候選位置"""
        b = blocks[pid]
        pxy = (placed[pid].x, placed[pid].y)
        cands = []
        for x in range(b.x0, b.x1 + 1):
            for y in range(b.y0, b.y1 + 1):
                if grid.is_used(x, y):
                    continue
                if parent_child_dist(pxy, (x, y)) == d_last:
                    cands.append((x, y))
        return cands

    def count_available_pairs(pid: int) -> int:
        """計算一個 parent 可用的 (c1, c2) 組合數"""
        n = len(get_leaf_candidates(pid))
        return n * (n - 1) if n >= 2 else 0

    def forward_check_leaves() -> bool:
        """檢查所有還需要放 leaf 的 parent 是否還有可行組合"""
        for pid, leaves in unplaced_leaves.items():
            if len(leaves) == 2 and count_available_pairs(pid) == 0:
                return False
            elif len(leaves) == 1 and len(get_leaf_candidates(pid)) == 0:
                return False
        return True

    def select_mrv_leaf_parent() -> Optional[int]:
        """選擇剩餘組合最少的 parent"""
        eligible = [pid for pid in leaf_parents if unplaced_leaves.get(pid)]
        if not eligible:
            return None
        return min(eligible, key=lambda pid: (
            0 if len(unplaced_leaves[pid]) == 1 else 1,
            count_available_pairs(pid) if len(unplaced_leaves[pid]) == 2 else len(get_leaf_candidates(pid))
        ))

    def dfs_leaves_mrv() -> bool:
        if all(len(leaves) == 0 for leaves in unplaced_leaves.values()):
            return True

        pid = select_mrv_leaf_parent()
        if pid is None:
            return False

        leaves = unplaced_leaves[pid]
        
        if len(leaves) == 2:
            c1, c2 = leaves
            cands = get_leaf_candidates(pid)
            
            for xy1 in cands:
                placed[c1] = place_node_at(grid, c1, router_id=c1, core_id=-1, xy=xy1)
                unplaced_leaves[pid] = [c2]
                
                for xy2 in get_leaf_candidates(pid):
                    placed[c2] = place_node_at(grid, c2, router_id=c2, core_id=-1, xy=xy2)
                    unplaced_leaves[pid] = []
                    
                    if forward_check_leaves() and dfs_leaves_mrv():
                        return True
                    
                    remove_node_at(grid, xy2)
                    del placed[c2]
                    unplaced_leaves[pid] = [c2]
                
                remove_node_at(grid, xy1)
                del placed[c1]
                unplaced_leaves[pid] = [c1, c2]
            
            return False
        
        elif len(leaves) == 1:
            c = leaves[0]
            for xy in get_leaf_candidates(pid):
                placed[c] = place_node_at(grid, c, router_id=c, core_id=-1, xy=xy)
                unplaced_leaves[pid] = []
                
                if forward_check_leaves() and dfs_leaves_mrv():
                    return True
                
                remove_node_at(grid, xy)
                del placed[c]
                unplaced_leaves[pid] = [c]
            
            return False

        return True

    if not dfs_leaves_mrv():
        raise RuntimeError("leaf 放置失敗")

    return placed, grid
