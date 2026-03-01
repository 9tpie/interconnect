from __future__ import annotations
import math
from typing import List, Tuple
from visualize import visualize_grid, visualize_network

from algorithms import solve, solve_interconnect, print_result, assign_router
from visualize import visualize_grid

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
        """
        if verbose:
            if rec is None:
                print(f"[warn] missing route record for ({p},{c}); skip")
            else:
                print(f"level {lvl} || node {p} -> node {c} || choose {mode} || path={seg}")

        """

        if seg:
            segments.append(seg)
    # step 1: 完成path(based on topology)
    full_router_path = concat_paths(segments)

    # step 2: 根據chiplet_id傳轉換成chiplet_router，並把chiplet_router concat到full_router_path
    chiplet_router = core_to_router.get(chiplet_id, None)
    full_router_path.append(chiplet_router)

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


def path_root_to_chiplet(num: int, chiplet_id: int) -> List[int]:
    """回傳你圖上的形式：root -> ... -> leaf -> chiplet"""
    leaf = leaf_of_chiplet(num, chiplet_id)
    return root_to_node_path(leaf) + [chiplet_id]


def check_nearby(placed_dict, full_paths):

    """
    傳入兩個dict，分別是位置以及路徑

    """
    def find_node_by_router_id(placed_dict, rid: int):
        for n in placed_dict.values():
            if getattr(n, "router_id", None) == rid:
                return n
        return None

    directions = {}
    for c_id, path in full_paths.items():
        if path[-1] == path[-2]:
            directions[c_id]="pass"

        else:
            leaf_node = find_node_by_router_id(placed_dict, path[-2])
            chiplet_node = find_node_by_router_id(placed_dict, path[-1])

            if leaf_node is None:
                return "LEAF_ROUTER_NOT_IN_PLACED"
            if chiplet_node is None:
                return "CHIPLET_ROUTER_NOT_IN_PLACED"

            dx = chiplet_node.x - leaf_node.x
            dy = chiplet_node.y - leaf_node.y
            manhattan = abs(dx) + abs(dy)

            if manhattan == 1:
                if dx == 1 and dy == 0:
                    directions[c_id] = "(E)"
                elif dx == -1 and dy == 0:
                    directions[c_id] = "(W)"
                elif dx == 0 and dy == 1:
                    directions[c_id] = "(N)"
                elif dx == 0 and dy == -1:
                    directions[c_id] = "(S)"
                else:
                    directions[c_id] = "（相鄰但方向判定異常）"
                #print(f"[OK] leaf_router 與 chiplet_router 東西南北相鄰：距離=1，方向={direction}")
            else:
                #print(f"[NO] leaf_router 與 chiplet_router 非東西南北相鄰：Manhattan distance = {manhattan}")
                directions[c_id] = "Not nearby"

    return directions

if __name__ == "__main__":
    num = 8

    # assign router
    router_map = assign_router(num)
    core_to_router = {core: rid for rid, core in router_map.items()}

    # placement
    placed, grid = solve(num)

    # interconnect
    routes, edge_routes, node_layer, network = solve_interconnect(num, placed)

    print_result(placed=placed, routes=routes, edge_routes=None, node_layer_func=node_layer)

    # dataflow
    print("=== Dataflow in binary tree (the last one is chiplet node) ===")
    for c_id in range(num):
        test_tree_path = path_root_to_chiplet(num,c_id)
        print(f"path list: {test_tree_path}")

    print("\n")

    print("=== Transform to router path (based on topology) ===")
    full_paths = {}
    for c_id in range(num):
        test_tree_path = path_root_to_chiplet(num, c_id)
        full_router_path = dataflow_to_router_path(
            path_nodes=test_tree_path,
            routes=routes,  # 你的 Router Path Result dict
            chiplet_id=c_id,
            verbose=False
        )
        full_paths[c_id] = full_router_path
    for c_id, path in full_paths.items():
        print(f"chiplet node {c_id}: {path}")

    # check direction
    print("\n")
    print("\n=== Check all chiplet_id ===")
    direction = check_nearby(placed, full_paths)
    for c_id, direction in direction.items():
        print(f"chiplet node {c_id}: {direction}")



    visualize_network(network)


