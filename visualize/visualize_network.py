import matplotlib.pyplot as plt

def visualize_network(
    network,
    show_router_id=True,
    show_core_id=False,
    show_bandwidth=True,
    title="Network Topology"
):
    fig, ax = plt.subplots(figsize=(10, 5))

    # 畫 link
    for link in network.links:
        x1, y1 = link.node_u.x, link.node_u.y
        x2, y2 = link.node_v.x, link.node_v.y

        ax.plot(
            [x1, x2],
            [y1, y2],
            linestyle='-',
            linewidth=2,
            color='grey',
            zorder=1
        )

        # 標示 bandwidth
        if show_bandwidth:
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2

            # 水平線與垂直線給不同偏移，避免壓在線上
            if y1 == y2:
                text_x = mid_x
                text_y = mid_y + 0.08
            else:
                text_x = mid_x + 0.08
                text_y = mid_y

            ax.text(
                text_x,
                text_y,
                f"{link.bandwidth:g}",
                color="blue",
                fontsize=9,
                ha="center",
                va="center",
                bbox=dict(
                    facecolor="white",
                    edgecolor="none",
                    alpha=0.8,
                    pad=1
                ),
                zorder=3
            )

    # 畫 node
    for node in network.nodes:
        ax.scatter(
            node.x,
            node.y,
            color="#dbeafe",
            edgecolors="black",
            linewidths=0.8,
            s=90,
            zorder=4
        )

        labels = []
        if show_router_id:
            labels.append(f"R{node.router_id}")
        if show_core_id:
            labels.append(f"C{node.core_id}")

        label = "\n".join(labels)

        ax.text(
            node.x + 0.08,
            node.y + 0.08,
            label,
            fontsize=9,
            ha="left",
            va="bottom",
            color="black",
            zorder=5
        )

    # 座標與格線設定
    ax.set_xlim(-0.3, network.width - 0.7)
    ax.set_ylim(-0.3, network.height - 0.7)
    ax.set_aspect("equal")

    ax.set_xticks(range(network.width))
    ax.set_yticks(range(network.height))

    ax.grid(True, linewidth=0.6, alpha=0.5)

    ax.set_title(title, pad=15)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")

    # 移除外框
    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()
    plt.savefig("topology_clean.png", dpi=300, bbox_inches="tight")
    plt.show()