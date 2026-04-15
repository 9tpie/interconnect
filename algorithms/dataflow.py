from __future__ import annotations
import math
from typing import List, Tuple, Dict
from visualize import visualize_grid, visualize_network
from collections import Counter
from data_structure import Network
from algorithms import solve, solve_interconnect, print_result, assign_router
from visualize import visualize_grid

STATUS_XY_CONNECTED = 2
STATUS_YX_CONNECTED = 3

def build_router_to_node(placed: Dict[int, "Node"]) -> Dict[int, "Node"]:
    router_to_node: Dict[int, "Node"] = {}
    for n in placed.values():
        rid = getattr(n, "router_id", None)
        if rid is not None and rid >= 0:
            router_to_node[rid] = n
    return router_to_node

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


def dataflow_to_router_path(num, path_nodes, routes, chiplet_id=0, verbose=False):
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
    router_map = assign_router(num)
    core_to_router = {core: rid for rid, core in router_map.items()}
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
    回傳dict
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

def stage1_opt(full_paths):
    new_paths = {}

    for c_id, path in full_paths.items():
        p = list(path)  # copy，不改到原本 full_paths 裡的 list

        if not p:
            new_paths[c_id] = p
            continue

        target = p[-1]
        for i in range(len(p) - 1):
            if p[i] == target:
                p = p[: i + 1]   # 或 del p[i+1:] 也行（但這行更直觀）
                break

        new_paths[c_id] = p

    return new_paths

def stage2_opt(full_paths):
    new_paths = {}

    for c_id, path in full_paths.items():
        stack = []
        pos = {}  # node -> index in stack

        for v in path:
            if v not in pos:
                pos[v] = len(stack)
                stack.append(v)
            else:
                idx = pos[v]
                while len(stack) > idx + 1:
                    removed = stack.pop()
                    pos.pop(removed, None)

        new_paths[c_id] = stack

    return new_paths

def calculate_interconnect(num_of_core, paths):
    """
        full_paths: {chiplet_id: [r0, r1, r2, ...]}
        1.輸出每個 cycle 的 (u->v) 次數統計
        2.計算所有cycle的每條連線的頻寬
    """

    total_cycle = 1
    n = int(math.log2(num_of_core))

    for i in range(1, n):
        t = n - i + 1
        exp = (t - 1) // 2  # 次方部分取整數
        d = 2 ** exp

        total_cycle += d

    # step i 代表 idx i -> idx i+1，所以最多到 max_len-2
    step_counters: List[Counter[Tuple[int, int]]] = [Counter() for _ in range(total_cycle)]

    total_counter = Counter()
    for cid, path in paths.items():
        if not path or len(path) < 2:
            continue
        for i in range(len(path) - 1):
            # u, v = path[i], path[i + 1]
            u = min(path[i], path[i + 1])
            v = max(path[i], path[i + 1])
            step_counters[i][(u, v)] += 1

    pair_max_counter = Counter()
    for counter in step_counters:
        for pair, cnt in counter.items():
            pair_max_counter[pair] = max(pair_max_counter[pair], cnt)

    # 印出結果
    """
    for i, counter in enumerate(step_counters):
        if not counter:
            continue
        print(f"cycle{i}")
        # 依次數由大到小，次數相同則依 u,v 排序（讓輸出穩定）
        items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))
        for (u, v), cnt in items:
            print(f"  {u} --> {v}  {cnt}個")
        print()
    """


    items = sorted(pair_max_counter.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))

    result = {}
    for (u, v), cnt in pair_max_counter.items():
        result[(u, v)] = cnt

    return result



def create_opt_network(opt_result, opt_net, router_to_node):
    for (u, v), cnt in opt_result.items():
        node_u = router_to_node.get(u)
        node_v = router_to_node.get(v)
        opt_net.add_link(node_u, node_v, cnt, color='black')



if __name__ == "__main__":
    num = 16

    k = int(math.log2(num))
    W = 2 ** ((k + 1) // 2)
    H = 2 ** (k // 2)
    stage1_opt_network = Network(W, H)

    # assign router
    # router_map = assign_router(num)

    # placement
    placed, grid = solve(num)

    router_to_node = build_router_to_node(placed)

    for node in placed.values():
        stage1_opt_network.add_existing_node(node)

    # interconnect
    routes, edge_routes, node_layer, network, connected = solve_interconnect(num, placed)

    print_result(placed=placed, routes=routes, edge_routes=None, node_layer_func=node_layer)

    # dataflow
    full_paths = {}
    for c_id in range(num):
        test_tree_path = path_root_to_chiplet(num, c_id)
        full_router_path = dataflow_to_router_path(
            num = num,
            path_nodes=test_tree_path,
            routes=routes,  # 你的 Router Path Result dict
            chiplet_id=c_id,
            verbose=False
        )
        full_paths[c_id] = full_router_path
    print("=== Dataflow in binary tree (the last one is chiplet node) ===")
    for c_id in range(num):
        test_tree_path = path_root_to_chiplet(num, c_id)
        print(f"path list: {test_tree_path}")

    print("\n")

    print("=== Transform to router path (based on topology) ===")

    for c_id, path in full_paths.items():
        print(f"chiplet node {c_id}: {path}")

    print("\n")

    print("=== Stage 1 OPTIMIZATION ===")

    stage1_result = stage1_opt(full_paths)
    for c_id, path in stage1_result.items():
        print(f"chiplet node {c_id}: {path}")

    print("\n")
    print("=== Stage 2 OPTIMIZATION ===")

    stage2_result = stage2_opt(stage1_result)
    for c_id, path in stage2_result.items():
        print(f"chiplet node {c_id}: {path}")

    stage1_opt_result = calculate_interconnect(num, stage1_result)
    # calculate_interconnect(num, stage2_result)
    for (u, v), cnt in stage1_opt_result.items():
        print(f"node {u} --- node {v}:  {stage1_opt_result[(u, v)]} bandwidth")

    create_opt_network(stage1_opt_result, stage1_opt_network, router_to_node)

    """
    # check direction
    print("\n")
    print("\n=== Check all chiplet_id ===")
    direction = check_nearby(placed, full_paths)
    for c_id, direction in direction.items():
        print(f"chiplet node {c_id}: {direction}")
    """

    visualize_network(network)
    visualize_network(stage1_opt_network)


