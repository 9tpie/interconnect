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
STATUS_USE_XY = 1
STATUS_USE_YX = 2

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
            color="gray",
        )
        all_added_edges.extend(added) # 累積結果

    return all_added_edges # 回傳完整的清單

def add_unique_route_links_for_level(
    net: "Network",
    level: int,
    routes: Dict[int, Dict[Tuple[int, int], dict]],
    placed: Dict[int, "Node"],
    bandwidth: float = 1.0,
    seen_undirected: Optional[Set[Edge]] = None,
) -> List[Edge]:

    if level not in routes:
        return []

    router_to_node = build_router_to_node(placed)
    if seen_undirected is None:
        seen_undirected = set()

    added_all: List[Edge] = []

    for (_p, _c), info in routes[level].items():
        path_xy = info.get("XY", [])
        path_yx = info.get("YX", [])
        if path_xy != path_yx:
            continue

        edges = path_to_edges(path_xy, undirected=True)
        added = add_edges(
            net,
            edges,
            router_to_node,
            bandwidth=bandwidth,
            seen=seen_undirected,
            undirected=True,
        )
        added_all.extend(added)

    return added_all

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
    選擇重疊數較少的路徑，並將結果標記在 info['selected_type'] 與 info['selected_path']。
    此函式會直接修改傳入的 routes_in_level 字典。
    """
    # 紀錄這一層目前為止被佔用的邊 (用 set 存無向邊 tuple 以加速比對)
    occupied_edges: Set[Edge] = set()

    added_all: List[Edge] = []

    if level not in routes:
        print(f"[DEBUG] 錯誤: routes 中找不到 level={level} 的資料")
        return []

    # Helper: 確保 edge 是 tuple 格式 (避免 list of lists 造成 set 失敗)
    def to_edge_set(edge_list, tag=""):
        try:
            # 如果 edge_list 是空的
            if not edge_list:
                return set()
            # 強制轉換每個元素為 tuple
            s = set(tuple(e) for e in edge_list)
            return s
        except Exception as e:
            print(f"[DEBUG] {tag} 資料格式轉換失敗: {e}, Data: {edge_list}")
            return set()

    # === Step 1: 優先處理無衝突路徑 (XY == YX) ===
    print(f"--- Step 1: 優先處理無衝突路徑 (XY == YX) ---")

    for (_p, _c), info in routes[level].items():
        # [修正 1] Key 名稱改為 'XY' 和 'YX'
        path_xy_nodes = info.get("XY", [])
        path_yx_nodes = info.get("YX", [])

        # 簡單檢查是否完全相同 (節點路徑相同，邊自然也相同)
        if path_xy_nodes != path_yx_nodes:
            continue

        print(f"  [Match] 處理配對 Router {_p} -> {_c} (路徑相同)")

        # [修正 2] 將「節點路徑」轉換為「邊的集合」
        # 例如: [1, 9, 3] -> {(1, 9), (9, 3)}
        edges = set()
        if len(path_xy_nodes) > 1:
            for i in range(len(path_xy_nodes) - 1):
                u = path_xy_nodes[i]
                v = path_xy_nodes[i + 1]
                # 確保無向邊的一致性 (小 ID 在前，或者依靠 add_edges 處理)
                # 這裡直接存 tuple 即可
                edges.add((u, v))

        print(f"    -> 節點路徑: {path_xy_nodes}")
        print(f"    -> 轉換後候選邊: {edges}")

        if not edges:
            print(f"    -> [WARNING] 邊集合為空，跳過。")
            continue

        added = add_edges(
            net,
            edges,
            router_to_node,
            bandwidth=bandwidth,
            seen=seen_undirected,
            undirected=True,
        )

        if added:
            print(f"    -> [SUCCESS] 成功加入新邊: {added}")
            seen_undirected.update(added)
        else:
            print(f"    -> [INFO] 未加入任何邊 (可能已存在)")

        occupied_edges.update(edges)
        info["status"] = STATUS_USE_XY
        added_all.extend(added)

        # === Step 2: 同 Parent 局部擁塞檢查 (嚴格篩選版) ===
        print(f"--- Step 2: 同 Parent 局部擁塞檢查 (僅處理單邊衝突) ---")

        # 1. 依照 Parent 分組
        from collections import defaultdict
        parent_groups = defaultdict(list)
        for (p, c), info in routes[level].items():
            parent_groups[p].append(c)

        # Helper: 節點轉排序後的邊集合
        def nodes_to_edges_set(node_list):
            s = set()
            if node_list and isinstance(node_list[0], int):
                for i in range(len(node_list) - 1):
                    s.add(tuple(sorted((node_list[i], node_list[i + 1]))))
            return s

        # 2. 針對每一組 Parent 進行處理
        for p, children in parent_groups.items():

            targets = [c for c in children if routes[level][(p, c)].get("status") == STATUS_UNCONNECTED]
            if not targets:
                continue

            print(f"\n[Group] Parent {p}，待處理子節點: {targets}")

            # === 建立「目前已佔用」的集合 (含 Pre-fill) ===
            local_occupied: Set[Edge] = set()

            # [動作 A] Pre-fill: 載入已連線兄弟
            for c in children:
                info = routes[level][(p, c)]
                status = info.get("status")
                if status in [STATUS_USE_XY, STATUS_USE_YX]:
                    path_key = "XY" if status == STATUS_USE_XY else "YX"
                    path_data = info.get(path_key, [])

                    # 處理資料格式 (相容 nodes list 或 edges list)
                    current_edges = set()
                    if path_data:
                        if isinstance(path_data[0], int):  # nodes list
                            current_edges = nodes_to_edges_set(path_data)
                        else:  # edges list
                            for u, v in path_data:
                                current_edges.add(tuple(sorted((u, v))))

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

                # === 決策邏輯 ===

                # 情況 1: 兩條路都沒有交集 -> 略過
                if cost_xy == 0 and cost_yx == 0:
                    print(f"    -> [SKIP] 兩條路都暢通 (Both Cost=0)，暫不處理")
                    continue

                # 情況 2: 兩條路都有交集 -> 不連線 (太擠了，無法決定)
                if cost_xy > 0 and cost_yx > 0:
                    print(f"    -> [SKIP] 兩條路都擁塞 (XY={cost_xy}, YX={cost_yx})，放棄連線")
                    continue

                # 情況 3: 只有一條路暢通 -> 連線那一條
                selected_edges = set()
                selected_status = ""

                if cost_xy == 0:
                    print(f"    -> [DECISION] 只有 XY 暢通 (XY=0, YX={cost_yx}) -> 選 XY")
                    selected_edges = edges_xy
                    selected_status = STATUS_USE_XY
                else:  # cost_yx == 0
                    print(f"    -> [DECISION] 只有 YX 暢通 (XY={cost_xy}, YX=0) -> 選 YX")
                    selected_edges = edges_yx
                    selected_status = STATUS_USE_YX

                # 執行加入
                added = add_edges(
                    net,
                    selected_edges,
                    router_to_node,
                    bandwidth=bandwidth,
                    seen=seen_undirected,
                    undirected=True,
                )

                if added:
                    print(f"    -> [SUCCESS] 成功加入邊: {added}")
                    seen_undirected.update(added)
                    added_all.extend(added)

                    # 更新狀態
                    info["status"] = selected_status

                    # 更新 local_occupied (讓後面的兄弟知道這條路被選走了)
                    local_occupied.update(selected_edges)
                    occupied_edges.update(selected_edges)
                else:
                    print(f"    -> [INFO] 邊已存在，無法加入")

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




def main():
    num = 16
    placed, grid = solve(num)

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

    # 加最後一層（灰色由 add_last_level_routes_to_network 內部決定/傳入）

    """
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
    print(f"加入leaf層: {seen_undirected}")
    """


    # 加入唯一路徑
    """
    for level in sorted(routes.keys()):
        edges = add_unique_route_links_for_level(
            net=network,
            level=level,
            routes=routes,
            placed=placed,
            bandwidth=2,
            seen_undirected=seen_undirected,
        )
    unique_edges_by_level[level] = edges
    connected.update(edges)

    """
    
    # 加入缺失的邊(迴圈)
    """
    for level, routes_in_level in edge_routes.items():
        print(f"Processing Level {level}...")
        
        # 呼叫函式處理該層
        added_edges = add_missing_edge(
            net=network,
            routes_at_level=routes_in_level,
            router_to_node=router_to_node,
            bandwidth=10.0,
            seen=connected  # 這就是你的 connected set
        )
        
        print(f"  -> Level {level} 新增了 {len(added_edges)} 條邊")
    """
    # 加入缺失的邊(單層測試)
    """
    test_level = 2
    added_edges = add_missing_edge(
            net=network,
            routes_at_level=edge_routes[test_level],
            router_to_node=router_to_node,
            bandwidth=10.0,
            seen=connected  # 這就是你的 connected set
        )
    connected.update(added_edges)
    seen_undirected.update(added_edges)
    print(f"加入缺失的邊: {seen_undirected}")
    """

    # 列印結果
    print_result(placed, routes, edge_routes, node_layer)

    """
    test_level = 2
    print(routes[test_level])
    # 測試單層避免擁塞
    result_edges = least_congestion_per_level(
            routes=routes,
            level=test_level,
            net=network,
            router_to_node=router_to_node,
            seen_undirected=seen_undirected
        )
    connected.update(result_edges)
    seen_undirected.update(result_edges)
    print(f"加入邊: {seen_undirected}")
    """

    # visualize_network(network)

    

if __name__ == "__main__":
    main()

# 短短加(短*2)短短