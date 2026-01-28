"""
找到所有配對的路徑(XY, YX)
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
    """
    回傳格式：
    routes[level][(p, c)] = {
        "parent": p,
        "child": c,
        "src_router": placed[p].router_id,
        "dst_router": placed[c].router_id,
        "XY": [router_id...],
        "YX": [router_id...],
    }
    """
    pair_list = parent_child_pairs_by_level(num_nodes)

    routes = defaultdict(dict)

    for level in sorted(pair_list.keys()):
        for p, c in pair_list[level]:
            # 直接用 placed 取 node（不需要 find_node_by_router_id）
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
            xy_path = info["XY"]  # List[int]
            yx_path = info["YX"]  # List[int]

            edge_routes[level][pair] = {
                **info,  # 保留原本欄位，完全對齊
                "XY_edges": path_to_edges(xy_path, undirected=undirected),
                "YX_edges": path_to_edges(yx_path, undirected=undirected),
            }

    return edge_routes

def build_router_id_map(placed: Dict[int, "Node"]) -> Dict[int, "Node"]:
    """router_id -> Node（同一個 router_id 應該只對到一個 Node）"""
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
    color: Optional[str] = None,
    add_to_seen: bool = True,
) -> List[Edge]:
    """
    把 edges 加入 net：
      - router_id -> Node 查表
      - seen 去重（預設無向正規化）
      - 可指定 color（若 Network.add_link 支援 color 參數）
    回傳：實際新增的 edges（以輸入的正規化形式）
    """
    if seen is None:
        seen = set()

    added: List[Edge] = []

    for (a, b) in edges:
        key = undirected_edge(a, b) if undirected else (a, b)
        if key in seen:
            continue

        node_a = router_to_node.get(a)
        node_b = router_to_node.get(b)
        if node_a is None or node_b is None:
            continue

        if color is None:
            net.add_link(node_a, node_b, bandwidth)
        else:
            net.add_link(node_a, node_b, bandwidth, color=color)

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
    """
    處理單一層級的路由：
    檢查每對 (pair)，只有當 XY 與 YX 其中一條路徑接觸到 seen，而另一條沒有時，
    才將剩下的邊補齊 (XOR 邏輯)。
    """
    if seen is None:
        seen = set()

    added_all: List[Edge] = []

    for pair, info in routes_at_level.items():
        # 1. 取得路徑的邊 (轉成 set)
        xy_edges = set(info.get("XY_edges", []))
        yx_edges = set(info.get("YX_edges", []))
        
        # 2. 判斷個別路徑是否「接觸」到 seen
        has_xy_contact = bool(xy_edges & seen)
        has_yx_contact = bool(yx_edges & seen)

        # 3. 核心邏輯修改：使用 XOR (^) 運算子
        # 只有當 (有XY沒YX) 或 (有YX沒XY) 時為 True
        is_triggered = has_xy_contact ^ has_yx_contact

        if is_triggered:
            # 4. 【邏輯修正】不再取聯集，而是誰觸發就補誰
            edges_to_add = set()

            if has_xy_contact:
                # 若是 XY 觸發，只補齊 XY 剩下的邊
                edges_to_add.update(xy_edges - seen)
            else:
                # 若是 YX 觸發 (由於 XOR 成立，這裡必定是 YX 為 True)
                # 只補齊 YX 剩下的邊
                edges_to_add.update(yx_edges - seen)

            if edges_to_add:
                newly_added = add_edges(
                    net,
                    list(edges_to_add), # 轉回 list 傳入
                    router_to_node,
                    bandwidth=bandwidth,
                    seen=seen,
                    undirected=True
                )
                added_all.extend(newly_added)
            info["status"] = STATUS_CONNECTED

    return added_all

def add_last_level_routes_to_network(
    network: "Network",
    routes: Dict[int, Dict[Tuple[int, int], dict]],
    placed: Dict[int, "Node"],
    bandwidth: float = 1.0,
    use: str = "XY",
    undirected: bool = True,
) -> List[Edge]: # 加上回傳型別提示

    if not routes:
        return []

    last_level = max(routes.keys())
    router_to_node = build_router_to_node(placed)
    
    # 使用區域變數 seen 來避免重複添加 (如果你希望這個函式獨立運作)
    local_seen: Set[Edge] = set() 
    all_added_edges: List[Edge] = [] # 用來累積所有被加入的邊

    for (_p, _c), info in routes[last_level].items():
        path = info.get(use, [])
        edges = path_to_edges(path, undirected=undirected)
        
        # 呼叫 add_edges 並接收回傳值
        added = add_edges(
            network,
            edges,
            router_to_node,
            bandwidth=bandwidth,
            seen=local_seen,
            undirected=undirected,
            color="black",
        )
        if added:
            all_added_edges.extend(added) # 累積結果
            info["status"] = STATUS_CONNECTED

    return all_added_edges # 回傳完整的清單


def least_congestion_per_level(
        routes: Dict[int, Dict[Tuple[int, int], dict]],
        level: int,
        net: "Network",
        router_to_node: Dict[int, Node],
        bandwidth: float = 10.0,
        seen_undirected: Optional[Set[Edge]] = None,
) -> List[Edge]:
    """
    針對同一層級 (Layer) 的所有連線配對，計算 XY 與 YX 路徑與「目前已選路徑」的重疊程度。
    選擇重疊數較少的路徑，並將結果標記在 info['status']。
    此函式會直接修改傳入的 routes 字典。
    """
    if seen_undirected is None:
        seen_undirected = set()

    # 紀錄這一層目前為止被佔用的邊 (用 set 存無向邊 tuple 以加速比對)
    occupied_edges: Set[Edge] = set()
    added_all: List[Edge] = []

    if level not in routes:
        print(f"[DEBUG] 錯誤: routes 中找不到 level={level} 的資料")
        return []

    # Helper: 確保 edge 是 tuple 格式
    def to_edge_set(edge_list, tag=""):
        try:
            if not edge_list: return set()
            return set(tuple(e) for e in edge_list)
        except Exception as e:
            return set()

    # Helper: 節點轉排序後的邊集合
    def nodes_to_edges_set(node_list):
        s = set()
        if node_list and isinstance(node_list[0], int):
            for i in range(len(node_list) - 1):
                s.add(tuple(sorted((node_list[i], node_list[i + 1]))))
        return s

    # ==========================================
    # === Step 1: 優先處理無衝突路徑 (XY == YX) ===
    # ==========================================
    print(f"--- Step 1: 優先處理無衝突路徑 (XY == YX) ---")

    for (_p, _c), info in routes[level].items():
        path_xy_nodes = info.get("XY", [])
        path_yx_nodes = info.get("YX", [])

        # 簡單檢查是否完全相同
        if path_xy_nodes != path_yx_nodes:
            continue

        # print(f"  [Match] 處理配對 Router {_p} -> {_c} (路徑相同)")

        edges = nodes_to_edges_set(path_xy_nodes)

        if not edges:
            continue

        added = add_edges(
            net,
            list(edges),  # add_edges 需要 list
            router_to_node,
            bandwidth=bandwidth,
            seen=seen_undirected,
            undirected=True,
        )

        if added:
            seen_undirected.update(added)
            added_all.extend(added)

        # 即使邊已經存在(added為空)，只要路徑確認選定，就該更新狀態與佔用表
        occupied_edges.update(edges)

        # --- 更新 Status ---
        info["status"] = STATUS_CONNECTED
        # ------------------

    # =======================================================
    # === Step 2: 同 Parent 局部擁塞檢查 (僅處理單邊衝突) ===
    # === 注意：這部分已經移出 Step 1 的迴圈外               ===
    # =======================================================
    print(f"--- Step 2: 同 Parent 局部擁塞檢查 (僅處理單邊衝突) ---")

    # 1. 依照 Parent 分組
    from collections import defaultdict
    parent_groups = defaultdict(list)
    for (p, c), info in routes[level].items():
        parent_groups[p].append(c)

    # 2. 針對每一組 Parent 進行處理
    for p, children in parent_groups.items():

        # 只處理還沒連線的 (Status == 0)
        targets = [c for c in children if routes[level][(p, c)].get("status") == STATUS_UNCONNECTED]
        if not targets:
            continue

        print(f"\n[Group] Parent {p}，待處理子節點: {targets}")

        # === 建立「目前已佔用」的集合 (含 Pre-fill: Step 1 已連線的兄弟) ===
        local_occupied: Set[Edge] = set()

        # [動作 A] Pre-fill: 載入已連線兄弟 (包含 Step 1 剛連上的)
        for c in children:
            info = routes[level][(p, c)]
            status = info.get("status")
            if status == STATUS_CONNECTED:
                # 這裡原本邏輯較複雜，但因為 Step 1 只有唯一解，
                # 而且如果 status 是 1，代表路徑已定，直接抓 XY 即可 (因為 XY==YX)
                # 為了保險，我們還是照舊抓取
                path_nodes = info.get("XY", [])  # 預設抓 XY
                current_edges = nodes_to_edges_set(path_nodes)
                local_occupied.update(current_edges)

        # [動作 B] 逐一檢查並決策
        for c in targets:
            info = routes[level][(p, c)]

            # 準備路徑
            path_xy_nodes = info.get("XY", [])
            path_yx_nodes = info.get("YX", [])

            edges_xy = nodes_to_edges_set(path_xy_nodes)
            edges_yx = nodes_to_edges_set(path_yx_nodes)

            # 計算交集 (Cost)
            cost_xy = len(edges_xy.intersection(local_occupied))
            cost_yx = len(edges_yx.intersection(local_occupied))

            print(f"  [Check] 子節點 {c} (Parent {p}) -> Cost XY: {cost_xy} | Cost YX: {cost_yx}")

            selected_edges = set()
            selected_path_nodes = []

            # === 決策邏輯 ===
            # 情況 3: 只有一條路暢通 -> 連線那一條
            if cost_xy == 0 and cost_yx > 0:
                print(f"    -> [DECISION] 選 XY")
                selected_edges = edges_xy
                selected_path_nodes = path_xy_nodes
            elif cost_yx == 0 and cost_xy > 0:
                print(f"    -> [DECISION] 選 YX")
                selected_edges = edges_yx
                selected_path_nodes = path_yx_nodes
            else:
                # cost_xy == 0 and cost_yx == 0 (都暢通 -> 暫不處理，或可預設 XY)
                # cost_xy > 0 and cost_yx > 0 (都塞車 -> 放棄)
                print(f"    -> [SKIP] 無法單純決策 (XY={cost_xy}, YX={cost_yx})")
                continue

            # 執行加入
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

            # --- 更新狀態與佔用表 ---
            info["status"] = STATUS_CONNECTED

            # 因為 XY 和 YX 不同，這裡理論上應該要標記選了哪條
            # 但你的資料結構只存 status=1，所以這裡僅更新狀態
            # 如果之後需要知道選了哪條，可能需要 info['selected'] = 'XY' 之類的欄位

            local_occupied.update(selected_edges)
            occupied_edges.update(selected_edges)
            # -----------------------

    return added_all


def solve_multiple_solution(
        routes_at_level: Dict[Tuple[int, int], dict],
        router_to_node: Dict[int, "Node"],
        net: "Network",
        bandwidth: float = 10.0,
        seen_undirected: Optional[Set[Tuple[int, int]]] = None,  # 修正型別提示
) -> List[Tuple[int, int]]:
    """
    若有多組解，則選擇XY(default)來連接
    """
    added_all: List[Tuple[int, int]] = []

    if seen_undirected is None:
        seen_undirected = set()

    # --- 修正後的輔助函式 (針對 Tuple) ---
    def is_edge_in_seen(u, v, seen_set):
        """
        直接檢查 tuple 是否存在於 set 中。
        因為是 Tuple，必須手動檢查兩個方向來模擬無向邊。
        """
        return (u, v) in seen_set or (v, u) in seen_set

    def is_path_connected(edges_list, seen_set):
        if not edges_list:
            return False
        for (u, v) in edges_list:
            if not is_edge_in_seen(u, v, seen_set):
                return False
        return True

    # ==========================================
    # Step 1: 檢查既有連通性
    # ==========================================
    print("--- Step 1: Checking Existing Connectivity ---")

    for (_p, _c), info in routes_at_level.items():
        if info.get("status") == 0:
            xy_edges = info.get('XY_edges', [])
            yx_edges = info.get('YX_edges', [])

            # 優先檢查 XY
            if xy_edges and is_path_connected(xy_edges, seen_undirected):
                print(f"Route {_p}->{_c} is already connected via XY.")
                info['status'] = 1
                continue

                # 其次檢查 YX
            if yx_edges and is_path_connected(yx_edges, seen_undirected):
                print(f"Route {_p}->{_c} is already connected via YX.")
                info['status'] = 1
                continue

            print(f"Route {_p}->{_c} remains Unconnected.")

    # ==========================================
    # Step 2: 執行 XY Routing 並補齊缺少的邊
    # ==========================================
    print("--- Step 2: Using default (XY) to connect ---")

    for (_p, _c), info in routes_at_level.items():
        if info.get("status") == 0:
            xy_edges = info.get('XY_edges', [])

            if not xy_edges:
                continue

            print(f"Routing {_p} -> {_c} via XY...")

            for u, v in xy_edges:

                # 1. 檢查是否已存在 (使用 Helper)
                if is_edge_in_seen(u, v, seen_undirected):
                    continue

                # 2. 不存在則建立 (修正：直接建立 Tuple，不要呼叫 Edge())
                try:
                    new_edge = (u, v)  # <--- 這裡直接用 Tuple
                    added = add_edges(
                        net,
                        [new_edge],
                        router_to_node,
                        bandwidth=bandwidth,
                        seen=seen_undirected,
                        undirected=True,
                    )
                    # 加入 seen (這裡我們統一存入 (u, v)，helper 會幫忙查反向)
                    seen_undirected.add(new_edge)
                    added_all.append(new_edge)

                    print(f"  [+] Created missing link: {u} <-> {v}")

                except Exception as e:
                    print(f"  [!] Error creating edge {u}-{v}: {e}")

            info['status'] = 1

    return added_all
def print_result(placed, routes, edge_routes, node_layer_func):
    """
    列印 Placement, Router Path 以及 Router Edge 的結果。

    Args:
        placed (dict): 包含節點位置資訊的字典 (需包含 .x, .y, .router_id)
        routes (dict): 包含路徑資訊的字典
        edge_routes (dict): 包含邊緣路徑資訊的字典
        node_layer_func (function): 輸入 nid 回傳 layer 的函式
    """

    # --- 1. Placement Result ---
    print("\n\n")
    print("=== Placement Result (1 ~ n layers, leaf included) ===\n")
    for nid in sorted(placed.keys()):
        n = placed[nid]
        # 使用傳入的 node_layer_func 取得層級
        layer = node_layer_func(nid)
        print(f"node{nid:>3}  layer={layer}  at ({n.x},{n.y})  router_id={n.router_id}")

    # --- 2. Router Path Result ---
    print("\n\n")
    print("=== Router Path Result (1 ~ n layers, leaf included) ===")

    for level in sorted(routes.keys()):
        print(f"\nlevel {level} -> {level + 1}")
        for (p, c), rec in routes[level].items():
            print(f"({p},{c})  XY={rec['XY']}  YX={rec['YX']}  status={rec['status']}")

    # --- 3. Router Edge Result ---
    print("\n\n")  # 補上換行讓格式與上面一致
    print("=== Router Edge Result (1 ~ n layers, leaf included) ===")

    for level in sorted(edge_routes.keys()):
        print(f"\nlevel {level} -> {level + 1}")
        for (p, c), info in edge_routes[level].items():
            # 注意: 這裡原程式碼為 rec['status']，已修正為 info['status']
            status = info.get('status', 'N/A')
            print(f"({p},{c})  XY edges: {info['XY_edges']}  YX edges: {info['YX_edges']}  status={status}")

def solve_interconnect(num, placed):

    # router-core 配對
    router_map = assign_router(num)
    router_to_core = {rid: core for rid, core in router_map.items()}
    router_to_node = build_router_to_node(placed)

    # 寫回 placed
    for rid, core in router_to_core.items():
        if rid in placed:
            placed[rid].core_id = core

    # build routes（寫回後再建）
    routes = build_routes_dict_by_level(num - 1, placed)
    print(f"The number of core(node): {num}\nThe number of level in tree: {len(routes)}")

    # 建立路徑轉為無向邊的dict
    edge_routes = build_edge_dict_by_level(routes)

    # 建 network
    k = int(math.log2(num))
    W = 2 ** ((k + 1) // 2)
    H = 2 ** (k // 2)
    network = Network(W, H)

    for node in placed.values():
        network.add_existing_node(node)

    # edge usage
    seen_undirected = set()  # 避免重複呼叫 之後可能要改掉
    unique_edges_by_level = {}
    connected: Set[Edge] = set()

    # step 1: 加入最後一層
    print("step 1: 加入最後一層")
    last_edges = add_last_level_routes_to_network(
        network=network,
        routes=routes,
        placed=placed,
        bandwidth=1,
        use="XY",
        undirected=True,
    )
    connected.update(last_edges)
    seen_undirected.update(last_edges)

    last_level = max(routes.keys())
    for pair, info in routes[last_level].items():
        if info["status"] == STATUS_CONNECTED:
            edge_routes[last_level][pair]["status"] = STATUS_CONNECTED

    # step 2: 解決每一層中的唯一路徑以及交集為0的唯一路徑
    print("step 2: 解決每一層中的唯一路徑以及交集為0的唯一路徑")
    for level in range(len(routes) - 1, 0, -1):
        least_congestion_edges = least_congestion_per_level(
            routes=routes,
            level=level,
            net=network,
            router_to_node=router_to_node,
            seen_undirected=seen_undirected
        )
        connected.update(least_congestion_edges)
        seen_undirected.update(least_congestion_edges)

        for pair, info in routes[level].items():
            # 如果 routes 裡的狀態變成了 CONNECTED (1)
            if info.get("status") == STATUS_CONNECTED:
                # 就更新 edge_routes 對應的項目
                edge_routes[level][pair]["status"] = STATUS_CONNECTED

    # step 3: 解決最後沒被連上的邊
    for level in range(len(routes) - 1, 0, -1):
        added_edges = add_missing_edge(
            net=network,
            routes_at_level=edge_routes[level],
            router_to_node=router_to_node,
            bandwidth=10.0,
            seen=connected
        )
        connected.update(added_edges)
        seen_undirected.update(added_edges)

        for pair, info in routes[last_level].items():
            if info["status"] == STATUS_CONNECTED:
                edge_routes[last_level][pair]["status"] = STATUS_CONNECTED

    # step 4: 解決多組解的情況
    print("\nstep 4 message")
    for level in range(len(routes) - 1, 0, -1):
        solve_multiple_solution(
            net=network,
            routes_at_level=edge_routes[level],
            router_to_node=router_to_node,
            bandwidth=20.0,
            seen_undirected=connected
        )

    return routes, edge_routes, node_layer, network

def main():

    num = 16
    placed, grid = solve(num)
    routes, edge_routes, node_layer, network = solve_interconnect(num, placed)
    print_result(placed, routes, edge_routes, node_layer)
    visualize_network(network)

if __name__ == "__main__":
    main()

# 短短加(短*2)短短