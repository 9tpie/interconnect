from dataclasses import dataclass
from typing import List

@dataclass
class Node:
    x: int
    y: int
    router_id: int
    core_id: int

@dataclass
class Link:
    node_u: Node
    node_v: Node
    bandwidth: float

class Network:
    def __init__(self):
        self.nodes: List[Node] = []
        self.links: List[Link] = []

    def add_node(self, x: int, y: int, router_id: int, core_id: int) -> Node:
        node = Node(x, y, router_id, core_id)
        self.nodes.append(node)
        return node

    def add_link(self, node_u: Node, node_v: Node, bandwidth: float) -> Link:
        link = Link(node_u, node_v, bandwidth)
        self.links.append(link)
        return link