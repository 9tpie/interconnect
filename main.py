from algorithms import solve
from algorithms import node_layer
from algorithms import assign_router
from visualize import visualize_grid


def main():
    num = 8

    placed, grid = solve(num)

    #placed 資料結構
    print("=== Placement Result (1 ~ n layers, leaf included) ===")
    for nid in sorted(placed.keys()):
        n = placed[nid]
        print(f"node{nid:>3}  layer={node_layer(nid)}  at ({n.x},{n.y})  router_id={n.router_id}")

    print("\nGrid used map (1=used, 0=empty):")
    print("placed nodes =", len(placed))

    # 可視化
    visualize_grid(grid)

    #grid 資料結構
    print("\n=== Raw grid.cells (cells[x][y]) ===")
    for y in reversed(range(grid.height)):   # 讓 y=0 在最下面
        row = []
        for x in range(grid.width):
            v = grid.cells[x][y]
            row.append("." if v is None else f"{v:2d}")
        print(" ".join(row))

    print("DFS後的結果")
    for nid, n in placed.items():
        print(n)

    #建立router core配對結果
    router_map = assign_router(num)
    core_to_router = {}
    for rid, core in router_map.items():
        core_to_router[core] = rid

    router_to_core = {rid: core for rid, core in router_map.items()}

    #配對結果寫回placed中的Node
    for rid, core in router_to_core.items():
        if rid in placed:
            placed[rid].core_id = core

    print("DFS後存取配對結果")
    for nid, n in placed.items():
        print(n)

    

if __name__ == "__main__":
    main()