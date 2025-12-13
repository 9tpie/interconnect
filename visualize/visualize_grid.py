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
            color = "#cccccc" if val is None else "#ff7777"

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

    plt.title("Grid Visualization")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.gca().invert_yaxis()  # 如果你想要 y=0 在上方，可以取消這行
    plt.show()
