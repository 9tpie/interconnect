"""
測試任兩點間 計算路徑
"""

import math
from collections import defaultdict
from typing import List, Tuple

from algorithms import solve
from algorithms import node_layer
from algorithms import assign_router
from algorithms import xy_route_by_coord
from algorithms import yx_route_by_coord
from data_structure import Node

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

def find_node_by_router_id(placed, target_router_id):
    for node in placed.values():
        if node.router_id == target_router_id:
            return node
    return None



def coord_to_router_id(xy: Tuple[int, int], placed: List[Node]) -> int:
    x, y = xy
    for n in placed.values():
        if n.x == x and n.y == y:
            return n.router_id
    raise ValueError(f"座標 {xy} 找不到對應的 router")



def main():
    num = 8

    placed, grid = solve(num)
    print(type(placed))
    #placed 資料結構
    print("=== Placement Result (1 ~ n layers, leaf included) ===")
    for nid in sorted(placed.keys()):
        n = placed[nid]
        print(f"node{nid:>3}  layer={node_layer(nid)}  at ({n.x},{n.y})  router_id={n.router_id}")


    source_router = 1
    destination_router = 2

    source_node = find_node_by_router_id(placed, source_router)
    destination_node = find_node_by_router_id(placed, destination_router)
    print(f"source router is {source_router}: ({source_node.x}, {source_node.y})")
    print(f"destination router is {destination_router}: ({destination_node.x}, {destination_node.y})")

    src_xy = (source_node.x, source_node.y)
    dst_xy = (destination_node.x, destination_node.y)

    path_xy = xy_route_by_coord(src_xy, dst_xy)
    
    path_yx = yx_route_by_coord(src_xy, dst_xy)

    
    router_xy_path = []
    for xy in path_xy:
        router_xy_path.append(coord_to_router_id(xy, placed))

    router_yx_path = []
    for xy in path_yx:
        router_yx_path.append(coord_to_router_id(xy, placed))

    print("XY path :", router_xy_path)
    print("YX path :", router_yx_path)
    

if __name__ == "__main__":
    main()
