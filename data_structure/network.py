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

    def add_link(self, node_u: Node, node_v: Node, bandwidth: float, color = "black") -> Link:
        link = Link(node_u, node_v, bandwidth, color)
        self.links.append(link)
        return link