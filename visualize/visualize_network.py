import matplotlib.pyplot as plt

def visualize_network(network):
    plt.figure(figsize=(6, 6))

    # 畫所有 link
    for link in network.links:
        x_values = [link.node_u.x, link.node_v.x]
        y_values = [link.node_u.y, link.node_v.y]
        plt.plot(x_values, y_values, linestyle='-', linewidth=2)

        # 標示 bandwidth
        mid_x = (link.node_u.x + link.node_v.x) / 2
        mid_y = (link.node_u.y + link.node_v.y) / 2
        plt.text(mid_x, mid_y, f"{link.bandwidth}", color="blue", fontsize=10)

    # 畫所有 node
    for node in network.nodes:
        plt.scatter(node.x, node.y, color='red', s=200)

        # 顯示 node 資訊
        label = f"R{node.router_id}\nC{node.core_id}"
        plt.text(node.x + 0.05, node.y + 0.05, label, fontsize=10)

    ax = plt.gca()
    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.title("Network Topology Visualization", pad = 30)
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.xticks(range(network.width + 1))
    plt.yticks(range(network.height + 1))
    plt.grid(True)
    plt.axis("equal")
    plt.savefig("topology.png")
    plt.show()