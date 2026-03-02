from algorithms import solve, solve_interconnect, print_result, path_root_to_chiplet, dataflow_to_router_path
from algorithms import node_layer
from algorithms import assign_router
from visualize import visualize_grid, visualize_network, visualize_router_placement

def main():
    num = 16

    # assign router
    router_map = assign_router(num)

    # placement
    placed, grid = solve(num)
    core_to_router = {core: rid for rid, core in router_map.items()}

    # interconnect
    routes, edge_routes, node_layer, network = solve_interconnect(num, placed)

    # result
    print_result(placed, routes, edge_routes, node_layer)

    # dataflow
    full_paths = {}
    for c_id in range(num):
        test_tree_path = path_root_to_chiplet(num, c_id)
        full_router_path = dataflow_to_router_path(
            num=num,
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

    # visualize_network(network)
    visualize_grid(grid)
    # visualize_router_placement(grid, placed)

if __name__ == "__main__":
    main()