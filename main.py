from algorithms import solve, solve_interconnect, print_result
from algorithms import node_layer
from algorithms import assign_router
from visualize import visualize_grid, visualize_network

def main():
    num = 8

    # placement
    placed, grid = solve(num)

    # interconnect
    routes, edge_routes, node_layer, network = solve_interconnect(num, placed)

    # result
    print_result(placed, routes, edge_routes, node_layer)
    visualize_network(network)
    visualize_grid(grid)
    

if __name__ == "__main__":
    main()