from __future__ import annotations
import math
from typing import List, Tuple

def _is_power_of_two(x: int) -> bool:
    return x > 0 and (x & (x - 1)) == 0

def _tree_height_k(num: int) -> int:
    # num 必須是 2^k
    return int(math.log2(num))

def root_to_node_path(node: int) -> List[int]:
    """heap 編號的 root->node 路徑（包含 node）"""
    if node <= 0:
        raise ValueError("node 必須 >= 1")
    path = []
    while node >= 1:
        path.append(node)
        node //= 2
    return path[::-1]

def leaf_of_chiplet(num: int, chiplet_id: int) -> int:
    """
    chiplet -> 對應的 leaf node
    規則：每個 leaf 分到 2 個 chiplet，從左到右依序分配
    """
    if not _is_power_of_two(num):
        raise ValueError("num 必須是 2 的冪（例如 8,16,32...）")
    if not (0 <= chiplet_id < num):
        raise ValueError(f"chiplet_id 必須在 0..{num-1}")
    leaf_start = num // 2               # leaf 起點，例如 num=16 => 8
    return leaf_start + (chiplet_id // 2)

def chiplets_of_leaf(num: int, leaf: int) -> Tuple[int, int]:
    """leaf -> 這個 leaf 對應的兩個 chiplet"""
    if not _is_power_of_two(num):
        raise ValueError("num 必須是 2 的冪")
    leaf_start = num // 2
    leaf_end = num - 1
    if not (leaf_start <= leaf <= leaf_end):
        raise ValueError(f"leaf 必須在 {leaf_start}..{leaf_end}")
    base = 2 * (leaf - leaf_start)
    return base, base + 1

def path_root_to_chiplet(num: int, chiplet_id: int) -> List[int]:
    """回傳你圖上的形式：root -> ... -> leaf -> chiplet"""
    leaf = leaf_of_chiplet(num, chiplet_id)
    return root_to_node_path(leaf) + [chiplet_id]

def chiplets_in_subtree(num: int, tree_node: int) -> List[int]:
    """
    給任一 tree node（1..num-1），回傳它的子樹底下包含哪些 chiplet（依序）
    """
    if not _is_power_of_two(num):
        raise ValueError("num 必須是 2 的冪")
    if not (1 <= tree_node <= num - 1):
        raise ValueError(f"tree_node 必須在 1..{num-1}")

    k = _tree_height_k(num)          # num = 2^k
    leaf_level = k - 1               # leaf 在第 k-1 層（root=0 層）

    # 算 tree_node 的層級 d（root=0）
    d = int(math.floor(math.log2(tree_node)))

    # 子樹最左 leaf：一路走左子到 leaf_level
    shift = leaf_level - d           # 還要往下幾層
    left_leaf = tree_node << shift
    right_leaf = left_leaf + (1 << shift) - 1

    leaf_start = num // 2
    # leaf -> chiplet 區間
    left_chiplet = 2 * (left_leaf - leaf_start)
    right_chiplet = 2 * (right_leaf - leaf_start) + 1
    return list(range(left_chiplet, right_chiplet + 1))

if __name__ == "__main__":
    num = 16
    print("二元樹中的dataflow (最後一個為chiplet node): ")
    for cid in range(16):
        print(path_root_to_chiplet(num, cid))

