from helper_interconnect import *

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
    for level in range(len(routes)-1, 0, -1):
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
    for level in range(len(routes)-1, 0, -1):
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
    print_result(placed, routes, edge_routes, node_layer)

    # print(f"seen_undirected: {seen_undirected}")
    visualize_network(network)

if __name__ == "__main__":
    main()