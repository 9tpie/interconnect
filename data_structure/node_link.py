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

