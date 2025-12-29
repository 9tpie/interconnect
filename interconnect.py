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
    routes[level][(p,c)] = {
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

def add_missing_edges_if_any_connected(
    path: List[int],
    connected: Set[Edge],
    *,
    undirected: bool = True,
) -> List[Edge]:
    """
    若 path 的邊中「至少一條」已存在 connected，回傳所有缺的邊；否則回空。
    """
    edges = path_to_edges(path, undirected=undirected)
    if not edges:
        return []
    if not any(e in connected for e in edges):
        return []
    return [e for e in edges if e not in connected]

def add_last_level_routes_to_network(
    network: "Network",
    routes: Dict[int, Dict[Tuple[int, int], dict]],
    placed: Dict[int, "Node"],
    bandwidth: float = 1.0,
    use: str = "XY",
    undirected: bool = True,
):
    if not routes:
        return

    last_level = max(routes.keys())
    router_to_node = build_router_to_node(placed)
    seen: Set[Edge] = set()

    for (_p, _c), info in routes[last_level].items():
        path = info.get(use, [])
        edges = path_to_edges(path, undirected=undirected)
        add_edges(
            network,
            edges,
            router_to_node,
            bandwidth=bandwidth,
            seen=seen,
            undirected=undirected,
            color="gray",
        )

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



def main():
    num = 16
    placed, grid = solve(num)

    # router-core 配對
    router_map = assign_router(num)
    router_to_core = {rid: core for rid, core in router_map.items()}

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


    # 加最後一層（灰色由 add_last_level_routes_to_network 內部決定/傳入）
    add_last_level_routes_to_network(
        network=network,
        routes=routes,
        placed=placed,
        bandwidth=1,
        use="XY",
        undirected=True,
    )
    

    # 加入唯一路徑

    seen_undirected = set()
    unique_edges_by_level = {}

    for level in sorted(routes.keys()):
        edges = add_unique_route_links_for_level(
            net=network,
            level=level,
            routes=routes,
            placed=placed,
            bandwidth=2,
            seen_undirected=seen_undirected,  # ★ 跨 level 去重
        )
        unique_edges_by_level[level] = edges

    
    

    # 列印結果
    print("\n\n")
    print("=== Placement Result (1 ~ n layers, leaf included) ===\n")
    for nid in sorted(placed.keys()):
        n = placed[nid]
        print(f"node{nid:>3}  layer={node_layer(nid)}  at ({n.x},{n.y})  router_id={n.router_id}")

    
    print("\n\n")
    print("=== Router Path Result (1 ~ n layers, leaf included) ===")

    for level in sorted(routes.keys()):
        print(f"\nlevel {level} -> {level+1}")
        for (p, c), rec in routes[level].items():
            print(f"({p},{c})  XY={rec['XY']}  YX={rec['YX']}")

    print("=== Router Edge Result (1 ~ n layers, leaf included) ===")

    for level in sorted(edge_routes.keys()):
        print(f"\nlevel {level} -> {level+1}")
        for (p, c), info in edge_routes[level].items():
            print(f"({p},{c})  XY edges: {info['XY_edges']}  YX edges: {info['YX_edges']}")
            
            

    # visualize_network(network)

    print(seen_undirected)
    

if __name__ == "__main__":
    main()
