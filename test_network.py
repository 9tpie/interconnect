from data_structure import Network
from data_structure import Node
from data_structure import Link
from visualize.visualize_network import visualize_network

def build_simple_mesh():
    net = Network()

    # 建 2x2 的例子
    n00 = net.add_node(0, 0, router_id=0, core_id=0)
    n10 = net.add_node(1, 0, router_id=1, core_id=1)
    n01 = net.add_node(0, 1, router_id=2, core_id=2)
    n11 = net.add_node(1, 1, router_id=3, core_id=3)

    # 垂直 link
    net.add_link(n01, n11, bandwidth=32.0)

    return net

if __name__ == "__main__":
    net = build_simple_mesh()
    print("nodes:", net.nodes)
    print("links:", net.links)
    visualize_network(net)
    print("拓樸圖已產生:topology.png")