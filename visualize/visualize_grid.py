# visualize_grid.py
import matplotlib.pyplot as plt
from data_structure import Grid

def visualize_grid(grid: Grid, show_values: bool = True):
    """
    視覺化 Grid 狀態

    - 空格畫淺灰色
    - 已使用的格子畫紅色
    - 顯示格子內的 value (例如 router_id)
    """
    fig, ax = plt.subplots(figsize=(grid.width, grid.height))

    # 畫每一個格子
    for x in range(grid.width):
        for y in range(grid.height):
            val = grid.get(x, y)

            # 顏色：None = 空格 / 有值 = 占用
            color = "#cccccc" if val is None else "#dbeafe"

            # rectangle = (x, y, width, height)
            rect = plt.Rectangle((x, y), 1, 1, facecolor=color, edgecolor='black')
            ax.add_patch(rect)

            # 印 value 在中間
            if show_values and val is not None:
                ax.text(
                    x + 0.5,
                    y + 0.5,
                    str(val),
                    ha='center',
                    va='center',
                    fontsize=12,
                    color='black'
                )

    # 設定座標系
    ax.set_xlim(0, grid.width)
    ax.set_ylim(0, grid.height)
    ax.set_aspect("equal")
    ax.set_xticks(range(grid.width + 1))
    ax.set_yticks(range(grid.height + 1))
    ax.grid(True)

    plt.title("Router placement")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.show()

    save_path = "C:\\Users\\yctea\\Desktop\\interconnect_topology"
    plt.savefig(save_path, dpi=300, bbox_inches="tight")

def visualize_router_placement(
    grid: Grid,
    placed: dict[int, "Node"],
    *,
    show_router_id: bool = False,
    show_core_id: bool = True,
    title: str = "Core Placement"
):
    """
    額外的圖：看 router 擺放結果（用 placed 決定 router 類型）
    - tree router: core_id == -1
    - chiplet router: core_id >= 0
    """
    # 先做 router_id -> Node 的索引，才能用 cell 裡的 router_id 找到 Node
    rid2node = {n.router_id: n for n in placed.values() if getattr(n, "router_id", None) is not None}

    fig, ax = plt.subplots(figsize=(grid.width, grid.height))

    for x in range(grid.width):
        for y in range(grid.height):
            rid = grid.get(x, y)

            # 空格
            if rid is None:
                face = "#eeeeee"
            else:
                n = rid2node.get(rid, None)
                # 找不到 node（理論上不該發生），用保底色
                if n is None:
                    face = "#f5d0fe"
                else:
                    core_id = getattr(n, "core_id", -1)
                    # tree router / chiplet router 分色
                    face = "#bfdbfe" if core_id == -1 else "#bbf7d0"

            rect = plt.Rectangle((x, y), 1, 1, facecolor=face, edgecolor="black")
            ax.add_patch(rect)

            # 文字標示
            if rid is not None:
                n = rid2node.get(rid, None)
                lines = []
                if show_router_id:
                    lines.append(f"{rid}")
                if show_core_id and n is not None:
                    core_id = getattr(n, "core_id", -1)
                    if core_id >= 0:
                        lines.append(f"{core_id}")
                ax.text(
                    x + 0.5, y + 0.5,
                    "\n".join(lines),
                    ha="center", va="center",
                    fontsize=12, color="black"
                )

    ax.set_xlim(0, grid.width)
    ax.set_ylim(0, grid.height)
    ax.set_aspect("equal")
    ax.set_xticks(range(grid.width + 1))
    ax.set_yticks(range(grid.height + 1))
    ax.grid(True)


    plt.title(title)
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.show()
