import sys
from algorithms import solve, solve_optimized
from algorithms import node_layer
from algorithms import assign_router
from visualize import visualize_grid


def main():
    # 從命令列參數讀取 num，預設 16
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 512
    
    # num >= 64 使用優化版，否則使用原版
    if num >= 64:
        print(f"使用優化版演算法 (num={num})")
        placed, grid = solve_optimized(num)
    else:
        print(f"使用原版演算法 (num={num})")
        placed, grid = solve(num)

    # 放置結果
    print(f"\n=== Placement Result (num={num}, {len(placed)} nodes) ===")
    for nid in sorted(placed.keys()):
        n = placed[nid]
        print(f"node{nid:>3}  layer={node_layer(nid)}  at ({n.x},{n.y})  router_id={n.router_id}")

    # 可視化並儲存
    visualize_grid(grid)
    print(f"\n可視化圖片已儲存至 grid.png")

    # Grid 文字顯示
    print(f"\n=== Raw grid.cells ({grid.width}x{grid.height}) ===")
    for y in reversed(range(grid.height)):
        row = []
        for x in range(grid.width):
            v = grid.cells[x][y]
            row.append("." if v is None else f"{v:2d}")
        print(" ".join(row))

    # Router-Core 配對
    router_map = assign_router(num)
    router_to_core = {rid: core for rid, core in router_map.items()}

    for rid, core in router_to_core.items():
        if rid in placed:
            placed[rid].core_id = core

    print("\n=== Router-Core 配對結果 ===")
    for nid, n in sorted(placed.items()):
        print(f"node{nid:>3}: router={n.router_id}, core={n.core_id}")


if __name__ == "__main__":
    main()