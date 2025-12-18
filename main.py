from algorithms import solve
from algorithms import node_layer
from visualize import visualize_grid

def main():
    num = 32

    placed, grid = solve(num)

    print("=== Placement Result (1 ~ n layers, leaf included) ===")
    for nid in sorted(placed.keys()):
        n = placed[nid]
        print(f"node{nid:>3}  layer={node_layer(nid)}  at ({n.x},{n.y})  router_id={n.router_id}")

    print("\nGrid used map (1=used, 0=empty):")

    print("placed nodes =", len(placed))
    print("leaf nodes =", [nid for nid in placed if node_layer(nid) == max(node_layer(i) for i in placed)])
    print(grid)
    visualize_grid(grid)

if __name__ == "__main__":
    main()