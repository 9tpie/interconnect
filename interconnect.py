"""
找到所有配對的路徑(XY, YX)
"""
import math
from collections import defaultdict
from typing import List, Tuple, Dict

from algorithms import solve
from algorithms import node_layer
from algorithms import xy_route_by_coord
from algorithms import yx_route_by_coord
from algorithms import assign_router
from data_structure import Node
from data_structure import Network
from visualize import visualize_network

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

def build_router_id_map(placed: Dict[int, "Node"]) -> Dict[int, "Node"]:
    """router_id -> Node（同一個 router_id 應該只對到一個 Node）"""
    m = {}
    for _, n in placed.items():
        if n.router_id is None:
            continue
        m[n.router_id] = n
    return m


def add_last_level_routes_to_network(
    network: Network,
    routes: Dict[int, Dict[Tuple[int, int], dict]],
    placed: Dict[int, Node],
    bandwidth: float = 1.0,
    use: str = "XY",
    undirected: bool = True,
):
    if not routes:
        return

    last_level = max(routes.keys())
    rid_to_node = build_router_id_map(placed)

    added = set()  # 去重用

    for (p, c), info in routes[last_level].items():
        router_path = info.get(use, [])
        if len(router_path) < 2:
            continue

        for a, b in zip(router_path[:-1], router_path[1:]):
            u = rid_to_node.get(a)
            v = rid_to_node.get(b)
            if u is None or v is None:
                continue

            key = (min(a, b), max(a, b)) if undirected else (a, b)
            if key in added:
                continue

            # ★ 重點：最後一層一律灰色
            network.add_link(u, v, bandwidth, color="gray")

            added.add(key)


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
        use="XY"
    )

    print("\n\n")
    print("=== Placement Result (1 ~ n layers, leaf included) ===\n")
    for nid in sorted(placed.keys()):
        n = placed[nid]
        print(f"node{nid:>3}  layer={node_layer(nid)}  at ({n.x},{n.y})  router_id={n.router_id}")

    
    print("\n\n")
    print("=== Router Path Result (1 ~ n layers, leaf included) ===")
    # 示範印出
    for level in sorted(routes.keys()):
        print(f"\nlevel {level} -> {level+1}")
        for (p, c), rec in routes[level].items():
            print(f"({p},{c})  XY={rec['XY']}  YX={rec['YX']}")


    visualize_network(network)

    
    

if __name__ == "__main__":
    main()
