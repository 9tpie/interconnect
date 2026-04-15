"""
找到所有配對的路徑(XY, YX)
修改說明：已加入頻寬顏色映射 (Bandwidth Color Map) 機制
"""
import math
from collections import defaultdict
from typing import List, Tuple, Dict, DefaultDict, Set, Optional, Iterable

from algorithms import solve
from algorithms import node_layer
from algorithms import xy_route_by_coord
from algorithms import yx_route_by_coord
from algorithms import assign_router
from data_structure import Node
from data_structure import Network
from visualize import visualize_network

Edge = Tuple[int, int]

STATUS_UNCONNECTED = 0
STATUS_CONNECTED = 1
STATUS_XY_CONNECTED = 2
STATUS_YX_CONNECTED = 3


def status_from_path_type(path_type: str) -> int:
    """把路徑類型轉成 status。
    - 'XY' -> STATUS_XY_CONNECTED
    - 'YX' -> STATUS_YX_CONNECTED
    - 其他 -> STATUS_CONNECTED (保底)
    """
    t = (path_type or "").upper()
    if t == "XY":
        return STATUS_XY_CONNECTED
    if t == "YX":
        return STATUS_YX_CONNECTED
    return STATUS_CONNECTED


# ==========================================
# [New] Bandwidth to Color Mapping
# 定義頻寬對應的顏色 (可依需求修改顏色代碼)
# ==========================================
BANDWIDTH_COLORS = {
    2.0:  'black',       # Leaf level
    4.0:  'tab:blue',    # Level 1 aggregation
    8.0:  'tab:red',     # Level 2
    16.0: 'tab:green',   # Level 3
    32.0: 'tab:purple',  # Level 4
    64.0: 'tab:orange',
    128.0: 'tab:brown',
    256.0: 'magenta',
}

def get_color_by_bw(bandwidth: float) -> str:
    """根據頻寬回傳對應顏色，若無對應則回傳預設灰色"""
    # 轉成 float 統一查詢鍵值
    bw_key = float(bandwidth)
    return BANDWIDTH_COLORS.get(bw_key, 'gray')

# ==========================================

def parent_child_pairs_by_level(num_nodes: int):
    """
    回傳格式：
    level 1 2: (1,2) (1,3)
    level 2 3: (2,4) (2,5) (3,6) (3,7)
    """
    levels = defaultdict(list)

    for parent in range(1, num_nodes + 1):
        parent_level = int(math.floor(math.log2(parent))) + 1

        left = 2 * parent
        right = 2 * parent + 1

        if left <= num_nodes:
            levels[parent_level].append((parent, left))
        if right <= num_nodes:
            levels[parent_level].append((parent, right))

    return levels

def coord_to_router_id(xy: Tuple[int, int], placed: Dict[int, Node]) -> int:
    x, y = xy
    for n in placed.values():  # placed 是 dict -> values() 才是 Node
        if n.x == x and n.y == y:
            return n.router_id
    raise ValueError(f"座標 {xy} 找不到對應的 router")

def find_node_by_router_id(placed, target_router_id):
    for node in placed.values():
        if node.router_id == target_router_id:
            return node
    return None

def build_routes_dict_by_level(
    num_nodes: int,
    placed: Dict[int, Node],
) -> Dict[int, Dict[Tuple[int, int], dict]]:
    pair_list = parent_child_pairs_by_level(num_nodes)
    routes = defaultdict(dict)

    for level in sorted(pair_list.keys()):
        for p, c in pair_list[level]:
            p_node = placed[p]
            c_node = placed[c]

            src_xy = (p_node.x, p_node.y)
            dst_xy = (c_node.x, c_node.y)

            path_xy = xy_route_by_coord(src_xy, dst_xy)
            path_yx = yx_route_by_coord(src_xy, dst_xy)

            xy_router_path = [coord_to_router_id(xy, placed) for xy in path_xy]
            yx_router_path = [coord_to_router_id(xy, placed) for xy in path_yx]

            routes[level][(p, c)] = {
                "parent": p,
                "child": c,
                "src_router": p_node.router_id,
                "dst_router": c_node.router_id,
                "XY": xy_router_path,
                "YX": yx_router_path,
                "status": STATUS_UNCONNECTED
            }

    return routes

def build_edge_dict_by_level(
    routes: Dict[int, Dict[Tuple[int, int], dict]],
    *,
    undirected: bool = True,
) -> Dict[int, Dict[Tuple[int, int], dict]]:
    edge_routes = defaultdict(dict)

    for level, pair_dict in routes.items():
        for pair, info in pair_dict.items():
            xy_path = info["XY"]
            yx_path = info["YX"]

            edge_routes[level][pair] = {
                **info,
                "XY_edges": path_to_edges(xy_path, undirected=undirected),
                "YX_edges": path_to_edges(yx_path, undirected=undirected),
            }

    return edge_routes

def build_router_id_map(placed: Dict[int, "Node"]) -> Dict[int, "Node"]:
    m = {}
    for _, n in placed.items():
        if n.router_id is None:
            continue
        m[n.router_id] = n
    return m

def undirected_edge(u: int, v: int) -> Edge:
    return (u, v) if u < v else (v, u)

def path_to_edges(path: List[int], *, undirected: bool = True) -> List[Edge]:
    if len(path) < 2:
        return []
    if undirected:
        return [undirected_edge(path[i], path[i + 1]) for i in range(len(path) - 1)]
    return [(path[i], path[i + 1]) for i in range(len(path) - 1)]

def build_router_to_node(placed: Dict[int, "Node"]) -> Dict[int, "Node"]:
    router_to_node: Dict[int, "Node"] = {}
    for n in placed.values():
        rid = getattr(n, "router_id", None)
        if rid is not None and rid >= 0:
            router_to_node[rid] = n
    return router_to_node


def add_edges(
        net: "Network",
        edges: Iterable[Edge],
        router_to_node: Dict[int, "Node"],
        *,
        bandwidth: float = 1.0,
        seen: Optional[Set[Edge]] = None,
        undirected: bool = True,
        color: Optional[str] = None, # 保留參數介面，但內部邏輯會優先使用頻寬映射
        add_to_seen: bool = True,
        update_if_exists: bool = True,
) -> List[Edge]:
    if seen is None:
        seen = set()

    added: List[Edge] = []

    # [Update] 根據頻寬決定顏色
    bw_color = get_color_by_bw(bandwidth)

    for (a, b) in edges:
        key = undirected_edge(a, b) if undirected else (a, b)

        node_a = router_to_node.get(a)
        node_b = router_to_node.get(b)
        if node_a is None or node_b is None:
            continue

        if key in seen:
            if update_if_exists:
                # 若已存在，更新其頻寬與顏色
                net.add_link(node_a, node_b, bandwidth, color=bw_color)
                added.append(key)
            continue

        # 新增連線
        net.add_link(node_a, node_b, bandwidth, color=bw_color)
        added.append(key)
        if add_to_seen:
            seen.add(key)

    return added

def add_missing_edge(
    net: "Network",
    routes_at_level: Dict[Tuple[int, int], dict],
    router_to_node: Dict[int, "Node"],
    *,
    bandwidth: float = 1.0,
    seen: Optional[Set[Edge]] = None,
) -> List[Edge]:
    if seen is None:
        seen = set()

    added_all: List[Edge] = []

    for pair, info in routes_at_level.items():
        xy_edges = set(info.get("XY_edges", []))
        yx_edges = set(info.get("YX_edges", []))

        has_xy_contact = bool(xy_edges & seen)
        has_yx_contact = bool(yx_edges & seen)

        is_triggered = has_xy_contact ^ has_yx_contact

        if is_triggered:
            edges_to_add = set()

            if has_xy_contact:
                edges_to_add.update(xy_edges)
            else:
                edges_to_add.update(yx_edges)

            if edges_to_add:
                newly_added = add_edges(
                    net,
                    list(edges_to_add),
                    router_to_node,
                    bandwidth=bandwidth,
                    seen=seen,
                    undirected=True
                )
                added_all.extend(newly_added)
            info["status"] = STATUS_XY_CONNECTED if has_xy_contact else STATUS_YX_CONNECTED

    return added_all

def add_last_level_routes_to_network(
    network: "Network",
    routes: Dict[int, Dict[Tuple[int, int], dict]],
    placed: Dict[int, "Node"],
    bandwidth: float = 1.0,
    use: str = "XY",
    undirected: bool = True,
) -> List[Edge]:

    if not routes:
        return []

    last_level = max(routes.keys())
    router_to_node = build_router_to_node(placed)

    local_seen: Set[Edge] = set()
    all_added_edges: List[Edge] = []

    for (_p, _c), info in routes[last_level].items():
        path = info.get(use, [])
        edges = path_to_edges(path, undirected=undirected)

        # [Update] 移除 hardcoded color="black"，讓 add_edges 內部根據 bandwidth=2.0 去抓黑色
        added = add_edges(
            network,
            edges,
            router_to_node,
            bandwidth=bandwidth,
            seen=local_seen,
            undirected=undirected
        )
        if added:
            all_added_edges.extend(added)
            info["status"] = status_from_path_type(use)

    return all_added_edges


def least_congestion_per_level(
        routes: Dict[int, Dict[Tuple[int, int], dict]],
        level: int,
        net: "Network",
        router_to_node: Dict[int, Node],
        bandwidth: float = 10.0,
        seen_undirected: Optional[Set[Edge]] = None,
) -> List[Edge]:
    if seen_undirected is None:
        seen_undirected = set()

    occupied_edges: Set[Edge] = set()
    added_all: List[Edge] = []

    if level not in routes:
        return []

    def nodes_to_edges_set(node_list):
        s = set()
        if node_list and isinstance(node_list[0], int):
            for i in range(len(node_list) - 1):
                s.add(tuple(sorted((node_list[i], node_list[i + 1]))))
        return s

    # === Step 1: 優先處理無衝突路徑 (XY == YX) ===
    for (_p, _c), info in routes[level].items():
        path_xy_nodes = info.get("XY", [])
        path_yx_nodes = info.get("YX", [])

        if path_xy_nodes != path_yx_nodes:
            continue

        edges = nodes_to_edges_set(path_xy_nodes)
        if not edges:
            continue

        added = add_edges(
            net,
            list(edges),
            router_to_node,
            bandwidth=bandwidth,
            seen=seen_undirected,
            undirected=True,
        )
        if added:
            seen_undirected.update(added)
            added_all.extend(added)

        occupied_edges.update(edges)
        info["status"] = STATUS_XY_CONNECTED

    # === Step 2: 同 Parent 局部擁塞檢查 ===
    from collections import defaultdict
    parent_groups = defaultdict(list)
    for (p, c), info in routes[level].items():
        parent_groups[p].append(c)

    for p, children in parent_groups.items():
        targets = [c for c in children if routes[level][(p, c)].get("status") == STATUS_UNCONNECTED]
        if not targets:
            continue

        local_occupied: Set[Edge] = set()

        for c in children:
            info = routes[level][(p, c)]
            status = info.get("status")
            if status in (STATUS_CONNECTED, STATUS_XY_CONNECTED, STATUS_YX_CONNECTED):
                path_nodes = info.get("XY", [])
                current_edges = nodes_to_edges_set(path_nodes)
                local_occupied.update(current_edges)

        for c in targets:
            info = routes[level][(p, c)]
            path_xy_nodes = info.get("XY", [])
            path_yx_nodes = info.get("YX", [])

            edges_xy = nodes_to_edges_set(path_xy_nodes)
            edges_yx = nodes_to_edges_set(path_yx_nodes)

            cost_xy = len(edges_xy.intersection(local_occupied))
            cost_yx = len(edges_yx.intersection(local_occupied))

            selected_edges = set()
            selected_status = None

            if cost_xy == 0 and cost_yx > 0:
                selected_edges = edges_xy
                selected_status = STATUS_XY_CONNECTED
            elif cost_yx == 0 and cost_xy > 0:
                selected_edges = edges_yx
                selected_status = STATUS_YX_CONNECTED
            else:
                continue

            added = add_edges(
                net,
                list(selected_edges),
                router_to_node,
                bandwidth=bandwidth,
                seen=seen_undirected,
                undirected=True,
            )

            if added:
                seen_undirected.update(added)
                added_all.extend(added)

            info["status"] = selected_status if selected_status is not None else STATUS_CONNECTED
            local_occupied.update(selected_edges)
            occupied_edges.update(selected_edges)

    return added_all


def solve_multiple_solution(
        routes_at_level: Dict[Tuple[int, int], dict],
        router_to_node: Dict[int, "Node"],
        net: "Network",
        bandwidth: float = 10.0,
        seen_undirected: Optional[Set[Tuple[int, int]]] = None,
) -> List[Tuple[int, int]]:

    added_all: List[Tuple[int, int]] = []

    if seen_undirected is None:
        seen_undirected = set()

    def is_edge_in_seen(u, v, seen_set):
        return (u, v) in seen_set or (v, u) in seen_set

    def is_path_connected(edges_list, seen_set):
        if not edges_list:
            return False
        for (u, v) in edges_list:
            if not is_edge_in_seen(u, v, seen_set):
                return False
        return True

    # --- 2. 輔助函式：統一的頻寬更新邏輯 ---
    def update_link_bandwidth(u_id: int, v_id: int, req_bw: float):
        """
        [Update] 更新頻寬時，同時更新顏色
        """
        node_u = router_to_node[u_id]
        node_v = router_to_node[v_id]

        current_bw = 0.0

        for link in net.links:
            is_forward = (link.node_u == node_u and link.node_v == node_v)
            is_backward = (link.node_u == node_v and link.node_v == node_u)
            if is_forward or is_backward:
                current_bw = link.bandwidth
                break

        final_bw = max(current_bw, req_bw)
        # 根據最終頻寬取得顏色
        final_color = get_color_by_bw(final_bw)

        # 寫入 Network (帶入顏色)
        net.add_link(node_u, node_v, final_bw, color=final_color)

    # ==========================================
    # Step 1: 檢查既有連通性 (並更新頻寬)
    # ==========================================
    for (_p, _c), info in routes_at_level.items():
        if info.get("status") == 0:
            xy_edges = info.get('XY_edges', [])
            yx_edges = info.get('YX_edges', [])

            if xy_edges and is_path_connected(xy_edges, seen_undirected):
                info['status'] = STATUS_XY_CONNECTED
                for u, v in xy_edges:
                    update_link_bandwidth(u, v, bandwidth)
                continue

            if yx_edges and is_path_connected(yx_edges, seen_undirected):
                info['status'] = STATUS_YX_CONNECTED
                for u, v in yx_edges:
                    update_link_bandwidth(u, v, bandwidth)
                continue

    # ==========================================
    # Step 2: 執行 Default (XY) Routing 並補齊缺少的邊
    # ==========================================
    for (_p, _c), info in routes_at_level.items():
        if info.get("status") == 0:
            xy_edges = info.get('XY_edges', [])

            if not xy_edges:
                continue

            for u, v in xy_edges:
                is_new_edge = not is_edge_in_seen(u, v, seen_undirected)

                update_link_bandwidth(u, v, bandwidth)

                seen_undirected.add((u, v))
                seen_undirected.add((v, u))

                if is_new_edge:
                    added_all.append((u, v))

            info['status'] = STATUS_XY_CONNECTED

    return added_all

def print_result(*args, **kwargs):
    """
    容錯版列印：
    - 允許少傳/多傳參數：print_(placed) / print_(placed, routes) / print_(placed, routes, edge_routes) ...
    - routes 或 edge_routes 缺失時，仍會列印 placement；有什麼印什麼
    - node_layer_func 可省略：會嘗試用 log2 推估（假設樹狀編號：1=root，2/3...）
    - 也支援用關鍵字傳入：print_(placed=..., routes=..., edge_routes=..., node_layer_func=...)
    """

    # ----------------------------
    # 1) 先從 kwargs 拿，再用 args 補
    # ----------------------------
    placed = kwargs.get("placed", None)
    routes = kwargs.get("routes", None)
    edge_routes = kwargs.get("edge_routes", None)
    node_layer_func = kwargs.get("node_layer_func", None)

    # 依序用 args 填補缺的（多的忽略）
    # 允許傳入格式： (placed, routes, edge_routes, node_layer_func)
    arg_list = list(args)
    if placed is None and len(arg_list) >= 1:
        placed = arg_list[0]
    if routes is None and len(arg_list) >= 2:
        routes = arg_list[1]
    if edge_routes is None and len(arg_list) >= 3:
        edge_routes = arg_list[2]
    if node_layer_func is None and len(arg_list) >= 4:
        node_layer_func = arg_list[3]

    # ----------------------------
    # 2) 預設 node_layer_func：用 log2 推估層級
    # ----------------------------
    if node_layer_func is None:
        import math

        def node_layer_func(nid: int) -> int:
            # nid=1 -> layer 0, nid=2~3 -> layer 1, nid=4~7 -> layer 2 ...
            if nid <= 0:
                return 0
            return int(math.floor(math.log2(nid)))

    # ----------------------------
    # 3) 防呆：placed 不存在就直接結束
    # ----------------------------
    if not placed:
        print("\n\n[print_] placed is missing/empty; nothing to print.")
        return

    # ----------------------------
    # 4) Placement
    # ----------------------------
    print("\n\n")
    print("=== Placement Result (1 ~ n layers, leaf included) ===\n")
    for nid in sorted(placed.keys()):
        n = placed[nid]
        layer = node_layer_func(nid)
        # n 可能不是你預期的型別，保護一下
        x = getattr(n, "x", None)
        y = getattr(n, "y", None)
        rid = getattr(n, "router_id", None)
        print(f"node{nid:>3}  layer={layer}  at ({x},{y})  router_id={rid}")

    # ----------------------------
    # 5) Routes（有才印）
    # ----------------------------
    if routes:
        print("\n\n")
        print("=== Router Path Result (1 ~ n layers, leaf included) ===")
        for level in sorted(routes.keys()):
            print(f"\nlevel {level} -> {level + 1}")
            level_dict = routes[level]
            # 允許 level_dict 不是 dict 的情況
            if not isinstance(level_dict, dict):
                print(f"[warn] routes[{level}] is not a dict: {type(level_dict)}")
                continue

            for (p, c), rec in level_dict.items():
                # rec 可能缺欄位，給預設
                xy = rec.get("XY", None) if isinstance(rec, dict) else None
                yx = rec.get("YX", None) if isinstance(rec, dict) else None
                status = rec.get("status", None) if isinstance(rec, dict) else None
                print(f"({p},{c})  XY={xy}  YX={yx}  status={status}")
    else:
        print("\n\n[print_] routes is missing; skip Router Path Result.")

    # ----------------------------
    # 6) Edge routes（有才印）
    # ----------------------------
    if edge_routes:
        print("\n\n")
        print("=== Router Edge Result (1 ~ n layers, leaf included) ===")
        for level in sorted(edge_routes.keys()):
            print(f"\nlevel {level} -> {level + 1}")
            level_dict = edge_routes[level]
            if not isinstance(level_dict, dict):
                print(f"[warn] edge_routes[{level}] is not a dict: {type(level_dict)}")
                continue

            for (p, c), info in level_dict.items():
                if isinstance(info, dict):
                    status = info.get("status", "N/A")
                    xy_edges = info.get("XY_edges", None)
                    yx_edges = info.get("YX_edges", None)
                else:
                    status, xy_edges, yx_edges = "N/A", None, None
                print(f"({p},{c})  XY edges: {xy_edges}  YX edges: {yx_edges}  status={status}")
    else:
        print("\n\n[print_] edge_routes is missing; skip Router Edge Result.")

def leaf_router_to_chiplet(
        num: int,
        connected: Set[Edge],
        net: "Network",
        router_to_node:Dict[int, "Node"],
        bandwidth: float = 1.0
):

    added_leaf: List[Tuple[int, int]] = []
    temp_edge = []

    # step 1: 找出leaf router底下的兩個chiplet node
    for i, j in enumerate(range(int(num / 2), num)):
        print(f"leaf router {j}: chiplet {2*i}, {2*i+1}")
        temp_edge.append((j, 2*i))
        temp_edge.append((j, 2*i+1))

    # step 2: 把 (leaf router, chiplet node) --> (leaf router, chiplet router)
    leaf_edge = []
    router_map = assign_router(num)
    core_to_router = {core: rid for rid, core in router_map.items()}
    for pair in temp_edge:
        chiplet_id = pair[1]
        chiplet_router = core_to_router.get(chiplet_id, None)
        leaf_edge.append((pair[0], chiplet_router))

    print(leaf_edge)

    # step 3: 若leaf router != chiplet router，且不在connected內，則連線，頻寬為1
    for pair in leaf_edge:
        u, v = pair
        edge = tuple(sorted((u, v)))

        if u!=v:
            print(pair)

        if u != v and edge not in connected:
            node_u = router_to_node[u]
            node_v = router_to_node[v]
            added_leaf.append(edge)
            net.add_link(node_u, node_v, bandwidth)

    return added_leaf


def solve_interconnect(num, placed):

    router_map = assign_router(num)
    router_to_core = {rid: core for rid, core in router_map.items()}
    router_to_node = build_router_to_node(placed)

    for rid, core in router_to_core.items():
        if rid in placed:
            placed[rid].core_id = core

    routes = build_routes_dict_by_level(num - 1, placed)
    print(f"The number of core(node): {num}\nThe number of level in tree: {len(routes)}")

    edge_routes = build_edge_dict_by_level(routes)

    def sync_routes_to_edges(routes_dict, edge_routes_dict):
        """把 routes 的 status 同步到 edge_routes (保持兩邊一致)"""
        for lvl, pair_dict in routes_dict.items():
            if lvl not in edge_routes_dict:
                continue
            for pair, info in pair_dict.items():
                if pair in edge_routes_dict[lvl]:
                    edge_routes_dict[lvl][pair]["status"] = info.get("status", STATUS_UNCONNECTED)

    def sync_edges_to_routes(routes_dict, edge_routes_dict):
        """把 edge_routes 的 status 回寫到 routes (step3/4 會直接改 edge_routes)"""
        for lvl, pair_dict in edge_routes_dict.items():
            if lvl not in routes_dict:
                continue
            for pair, info in pair_dict.items():
                if pair in routes_dict[lvl]:
                    routes_dict[lvl][pair]["status"] = info.get("status", STATUS_UNCONNECTED)


    k = int(math.log2(num))
    W = 2 ** ((k + 1) // 2)
    H = 2 ** (k // 2)
    network = Network(W, H)

    for node in placed.values():
        network.add_existing_node(node)

    seen_undirected = set()
    unique_edges_by_level = {}
    connected: Set[Edge] = set()

    # step 1: 加入最後一層 (bandwidth=2)

    added_leaf = leaf_router_to_chiplet(
        num=num,
        connected=connected,
        net=network,
        router_to_node=router_to_node,
        bandwidth=1.0
    )
    connected.update(added_leaf)
    seen_undirected.update(added_leaf)

    sync_edges_to_routes(routes, edge_routes)
    sync_routes_to_edges(routes, edge_routes)

    last_edges = add_last_level_routes_to_network(
        network=network,
        routes=routes,
        placed=placed,
        bandwidth=2.0,
        use="XY",
        undirected=True,
    )
    connected.update(last_edges)
    seen_undirected.update(last_edges)

    sync_routes_to_edges(routes, edge_routes)

    # step 2

    for i, level in enumerate(range(len(routes) - 1, 0, -1)):
        # bandwidth 動態計算: 4, 8, 12...
        current_bw = float(4*(i+1))

        least_congestion_edges = least_congestion_per_level(
            routes=routes,
            level=level,
            net=network,
            router_to_node=router_to_node,
            bandwidth = current_bw,
            seen_undirected=seen_undirected
        )
        connected.update(least_congestion_edges)
        seen_undirected.update(least_congestion_edges)

    sync_routes_to_edges(routes, edge_routes)


    # step 3

    for i, level in enumerate(range(len(routes) - 1, 0, -1)):
        current_bw = float(4*(i+1))

        added_edges = add_missing_edge(
            net=network,
            routes_at_level=edge_routes[level],
            router_to_node=router_to_node,
            bandwidth=current_bw,
            seen=connected
        )
        connected.update(added_edges)
        seen_undirected.update(added_edges)

    sync_edges_to_routes(routes, edge_routes)
    sync_routes_to_edges(routes, edge_routes)


    # step 4

    for i, level in enumerate(range(len(routes) - 1, 0, -1)):
        current_bw = float(4*(i+1))

        added_remain = solve_multiple_solution(
            net=network,
            routes_at_level=edge_routes[level],
            router_to_node=router_to_node,
            bandwidth=current_bw,
            seen_undirected=connected
        )
        connected.update(added_remain)
        seen_undirected.update(added_remain)

    sync_edges_to_routes(routes, edge_routes)
    sync_routes_to_edges(routes, edge_routes)



    return routes, edge_routes, node_layer, network, connected

def main():
    num = 16
    placed, grid = solve(num)
    routes, edge_routes, node_layer, network, connected = solve_interconnect(num, placed)
    print_result(placed, routes, edge_routes, node_layer)
    print(connected)
    visualize_network(network)


if __name__ == "__main__":
    main()