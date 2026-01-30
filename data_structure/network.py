from .node_link import Node
from .node_link import Link
from typing import List

class Network:
    def __init__(self, width, height):
        self.nodes: List[Node] = []
        self.links: List[Link] = []
        self.width = width
        self.height = height

    def add_node(self, x: int, y: int, router_id: int, core_id: int) -> Node:
        node = Node(x, y, router_id, core_id)
        self.nodes.append(node)
        return node
    
    def add_existing_node(self, node: Node):
        self.nodes.append(node)

    def add_link(self, node_u: Node, node_v: Node, bandwidth: float, color="black") -> Link:
        # 1. 遍歷現有的連結，檢查是否已經存在 (雙向檢查)
        for link in self.links:
            # 注意：這裡假設 Link 物件將傳入的節點儲存為 node_u 和 node_v
            # 如果您的 Link 類別屬性名稱不同 (例如 link.u, link.src 等)，請在此修改

            # 檢查方向 U -> V
            match_forward = (link.node_u == node_u and link.node_v == node_v)
            # 檢查方向 V -> U (因為是無向連結)
            match_backward = (link.node_u == node_v and link.node_v == node_u)

            if match_forward or match_backward:
                # === 找到既有的邊：執行更新 ===
                link.bandwidth = bandwidth
                link.color = color
                return link  # 回傳更新後的舊 link，不執行 append

        # 2. 如果迴圈跑完都沒找到：建立新連結並加入
        new_link = Link(node_u, node_v, bandwidth, color)
        self.links.append(new_link)
        return new_link