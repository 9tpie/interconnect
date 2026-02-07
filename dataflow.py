from __future__ import annotations
import math
from typing import List, Tuple

from algorithms import solve, solve_interconnect, print_result, assign_router

STATUS_XY_CONNECTED = 2
STATUS_YX_CONNECTED = 3

def find_route_record(routes, p, c):
    """
    在 routes 的所有 level 中找 (p,c) 的紀錄
    回傳 (level, rec)；找不到回 (None, None)
    """
    if not routes:
        return None, None
    for lvl in sorted(routes.keys()):
        level_dict = routes.get(lvl, {})
        if isinstance(level_dict, dict) and (p, c) in level_dict:
            return lvl, level_dict[(p, c)]
    return None, None


def pick_segment_by_status(rec):
    """
    依 status 選 XY 或 YX 的 router path（list of router_id）
    """
    if not isinstance(rec, dict):
        return None, None  # (mode, segment)

    status = rec.get("status", None)
    xy = rec.get("XY", None)
    yx = rec.get("YX", None)

    if status == STATUS_XY_CONNECTED:
        return "XY", xy
    if status == STATUS_YX_CONNECTED:
        return "YX", yx

    # 容錯：萬一 status 不是 2/3
    # - 若 XY==YX，選哪個都一樣
    if xy is not None and xy == yx:
        return "XY", xy
    # - 否則預設先用 XY（你也可以改成比較短的那條）
    return "XY", xy


def concat_paths(paths):
    """
    把多段 router path 串起來（避免段與段的接點重複）
    例：[1,10,2] + [2,9,4] -> [1,10,2,9,4]
    """
    full = []
    for seg in paths:
        if not seg:
            continue
        if not full:
            full.extend(seg)
        else:
            if full[-1] == seg[0]:
                full.extend(seg[1:])
            else:
                # 若接不起來也先硬接（方便你 debug 看哪裡不一致）
                full.extend(seg)
    return full


def dataflow_to_router_path(path_nodes, routes, chiplet_id=0, verbose=True):
    """
    path_nodes: 例如 [1,2,4,8,0]
    routes: Router Path Result 的 dict
    chiplet_id: 最後那個 chiplet node（通常你用 0）
    """
    if not path_nodes or len(path_nodes) < 2:
        return []

    segments = []

    # 如果最後一個是 chiplet node，就不要去找 (last_parent, chiplet) 的 router path
    end = len(path_nodes) - 1
    if path_nodes[-1] == chiplet_id:
        end = len(path_nodes) - 2  # 停在倒數第二個（chiplet 前一個）

    for i in range(end):
        p = path_nodes[i]
        c = path_nodes[i + 1]

        lvl, rec = find_route_record(routes, p, c)
        mode, seg = pick_segment_by_status(rec)

        if verbose:
            if rec is None:
                print(f"[warn] missing route record for ({p},{c}); skip")
            else:
                print(f"level {lvl} || node {p} -> node {c} || choose {mode} || path={seg}")

        if seg:
            segments.append(seg)

    full_router_path = concat_paths(segments)

    if verbose:
        print(f"\nFull router path: {full_router_path}")

    return full_router_path


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

def check_nearby(placed_dict, leaf_router, chiplet_router):

    def find_node_by_router_id(placed_dict, rid: int):
        for n in placed_dict.values():
            if getattr(n, "router_id", None) == rid:
                return n
        return None

    leaf_node = find_node_by_router_id(placed_dict, leaf_router)
    chiplet_node = find_node_by_router_id(placed_dict, chiplet_router)

    if leaf_node is None:
        return "LEAF_ROUTER_NOT_IN_PLACED"
    if chiplet_node is None:
        return "CHIPLET_ROUTER_NOT_IN_PLACED"

    dx = chiplet_node.x - leaf_node.x
    dy = chiplet_node.y - leaf_node.y
    manhattan = abs(dx) + abs(dy)

    if manhattan == 1:
        if dx == 1 and dy == 0:
            direction = "(E)"
        elif dx == -1 and dy == 0:
            direction = "(W)"
        elif dx == 0 and dy == 1:
            direction = "(N)"
        elif dx == 0 and dy == -1:
            direction = "(S)"
        else:
            direction = "（相鄰但方向判定異常）"
        #print(f"[OK] leaf_router 與 chiplet_router 東西南北相鄰：距離=1，方向={direction}")
    else:
        #print(f"[NO] leaf_router 與 chiplet_router 非東西南北相鄰：Manhattan distance = {manhattan}")
        direction = "Not nearby"

    return direction

if __name__ == "__main__":
    num = 16

    # assign router
    router_map = assign_router(num)
    core_to_router = {core: rid for rid, core in router_map.items()}

    # placement
    placed, grid = solve(num)

    # interconnect
    routes, edge_routes, node_layer, network = solve_interconnect(num, placed)

    print_result(placed=placed, routes=routes, edge_routes=None, node_layer_func=node_layer)
    print("\n\n")
    print("\n=== Check all chiplet_id ===")
    results = []

    for cid in range(num):
        test_tree_path = path_root_to_chiplet(num, cid)

        full_router_path = dataflow_to_router_path(
            path_nodes=test_tree_path,
            routes=routes,  # 你的 Router Path Result dict
            chiplet_id=cid,
            verbose=False
        )

        leaf_router = full_router_path[-2]
        chiplet_core = full_router_path[-1]

        chiplet_router_id = core_to_router.get(chiplet_core, None)

        if chiplet_router_id is None:
            direction = "NO_ROUTER"
        else:
            # 5) 檢查是否相鄰
            direction = check_nearby(placed, leaf_router, chiplet_router_id)

        results.append((cid, leaf_router, chiplet_router_id, direction))

    directions = [d for (_cid, _leaf_r, _chip_r, d) in results]
    print("\nAll directions:", directions)
