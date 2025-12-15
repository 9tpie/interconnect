from dataclasses import dataclass
from math import log2
import math

@dataclass(frozen=True)
class Rect:
    x0: int
    x1: int
    y0: int
    y1: int

    @property
    def w(self) -> int:
        return self.x1 - self.x0 + 1

    @property
    def h(self) -> int:
        return self.y1 - self.y0 + 1

    @property
    def area(self) -> int:
        return self.w * self.h


def calculate_x_y(num):
    """ 由初始core數量 得知最上層的區塊 """
    root = math.sqrt(num)
    
    y = int(root)
    
    if root.is_integer():
        x = y
    else:
        x = y * 2
        
    return x, y


def split_rect(rect: Rect, axis: str) -> tuple[Rect, Rect]:
    """把 rect 沿 axis ('x' or 'y') 對半切成兩塊：回傳(左子/2i, 右子/2i+1)。"""
    if axis == "x":
        mid = (rect.x0 + rect.x1) // 2
        left  = Rect(rect.x0, mid,       rect.y0, rect.y1)      # 2i：較小 x
        right = Rect(mid + 1, rect.x1,   rect.y0, rect.y1)      # 2i+1：較大 x
        return left, right

    if axis == "y":
        mid = (rect.y0 + rect.y1) // 2
        top    = Rect(rect.x0, rect.x1,  mid + 1, rect.y1)      # 2i：較大 y（上半部，符合你圖）
        bottom = Rect(rect.x0, rect.x1,  rect.y0, mid)          # 2i+1：較小 y
        return top, bottom

    raise ValueError("axis 必須是 'x' 或 'y'")


def node_level(node_id: int) -> int:
    """完全二元樹 heap index 的 level：1-based"""
    return int(log2(node_id)) + 1


def build_blocks(num: int, leaf_area: int = 4) -> dict[int, Rect]:
    """
    回傳：node_id -> Rect(x0,x1,y0,y1)
    leaf_area=4 表示切到 2x2 就停止（符合你圖 num=16/32 的停止探索）
    """
    W, H = calculate_x_y(num)
    start_axis = "x" if W > H else "y"   # num=32 先切 x；num=16 先切 y

    blocks: dict[int, Rect] = {}
    root = Rect(0, W - 1, 0, H - 1)

    # BFS/queue：存 (node_id, rect)
    q = [(1, root)]

    while q:
        nid, rect = q.pop(0)
        blocks[nid] = rect

        # 到葉子就不再切
        if rect.area <= leaf_area:
            continue

        lvl = node_level(nid)
        axis = start_axis if (lvl % 2 == 1) else ("y" if start_axis == "x" else "x")

        c1, c2 = split_rect(rect, axis)
        q.append((nid * 2, c1))
        q.append((nid * 2 + 1, c2))

    return blocks


def print_blocks(num: int, leaf_area: int = 4) -> None:
    blocks = build_blocks(num, leaf_area=leaf_area)
    for nid in sorted(blocks.keys()):
        r = blocks[nid]
        print(f"{nid}: x={r.x0}~{r.x1}, y={r.y0}~{r.y1} (level {node_level(nid)})")


# --- 範例 ---
if __name__ == "__main__":
    num = int(input("輸入 num (2 的次方，例如 16/32): "))
    print_blocks(num, leaf_area=4)
