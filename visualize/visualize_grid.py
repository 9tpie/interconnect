# visualize_grid.py
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data_structure import Grid


def node_layer(node_id: int) -> int:
    """計算節點所在的層級"""
    if node_id < 1:
        return 0
    return int(math.floor(math.log2(node_id))) + 1


def parent_id(node_id: int) -> int:
    """取得父節點 ID"""
    return node_id // 2


def visualize_grid(grid: Grid, show_values: bool = True, save_path: str = "grid.png"):
    """
    彩色視覺化 Grid 狀態
    
    - 根據節點層級分配顏色
    - 顯示節點 ID
    - 繪製 parent-child 連線
    """
    fig, ax = plt.subplots(figsize=(max(10, grid.width), max(8, grid.height)))
    
    # 背景網格線
    for x in range(grid.width + 1):
        ax.axvline(x, color='lightgray', linewidth=0.5)
    for y in range(grid.height + 1):
        ax.axhline(y, color='lightgray', linewidth=0.5)
    
    # 根據層級分配顏色
    colors = plt.cm.Set3(range(12))
    
    # 收集所有節點位置 (用於繪製連線)
    node_positions = {}  # node_id -> (x, y)
    
    # 畫每一個格子
    for x in range(grid.width):
        for y in range(grid.height):
            val = grid.get(x, y)
            
            if val is None:
                # 空格：淺灰色
                rect = patches.Rectangle(
                    (x, y), 1, 1,
                    facecolor='#f0f0f0',
                    edgecolor='lightgray',
                    linewidth=0.5
                )
                ax.add_patch(rect)
            else:
                # 有節點：根據層級著色
                node_id = int(val)
                layer = node_layer(node_id)
                color = colors[layer % len(colors)]
                
                node_positions[node_id] = (x, y)
                
                rect = patches.Rectangle(
                    (x, y), 1, 1,
                    linewidth=2,
                    edgecolor='black',
                    facecolor=color,
                    alpha=0.7
                )
                ax.add_patch(rect)
                
                # 印 node_id 在中間
                if show_values:
                    fontsize = 8 if grid.width > 8 else 10
                    ax.text(
                        x + 0.5, y + 0.5,
                        str(node_id),
                        ha='center', va='center',
                        fontsize=fontsize,
                        fontweight='bold',
                        color='black'
                    )
    
    # 使用不同調色盤讓連線顏色更鮮明
    line_colors = plt.cm.tab10(range(10))
    
    # 繪製 parent-child 連線 (使用子節點的層級顏色)
    for node_id, (x, y) in node_positions.items():
        if node_id == 1:
            continue
        pid = parent_id(node_id)
        if pid in node_positions:
            px, py = node_positions[pid]
            layer = node_layer(node_id)
            line_color = line_colors[layer % len(line_colors)]
            ax.plot(
                [x + 0.5, px + 0.5],
                [y + 0.5, py + 0.5],
                color=line_color, linewidth=2, alpha=0.8
            )
    
    # 設定座標系
    ax.set_xlim(-0.5, grid.width + 0.5)
    ax.set_ylim(-0.5, grid.height + 0.5)
    ax.set_aspect("equal")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    
    # 加入圖例
    num_nodes = len(node_positions)
    max_layer = max(node_layer(nid) for nid in node_positions.keys()) if node_positions else 1
    legend_elements = []
    for layer in range(2, max_layer + 1):  # Layer 2 開始才有連線
        line_color = line_colors[layer % len(line_colors)]
        from matplotlib.lines import Line2D
        legend_elements.append(Line2D([0], [0], color=line_color, linewidth=2, label=f'Layer {layer}'))
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', fontsize=8, title='Connections')
    
    plt.title(f"Grid Visualization ({grid.width}x{grid.height}, {num_nodes} nodes)")
    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight')
    plt.close()

