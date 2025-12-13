# grid.py
from typing import Any, Optional, Tuple

class Grid:
    """
    X x Y 的方格，用來做 router / core 位置擺放。
    每一格可以放一個任意物件（例如 router_id、Node 物件等）。
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

        # cells[x][y] = None 表示沒有人用；否則存放占用這格的物件
        self.cells = [[None for _ in range(height)] for _ in range(width)]

    # ----- 基本操作 -----

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def _check_bounds(self, x: int, y: int):
        if not self.in_bounds(x, y):
            raise ValueError(f"({x}, {y}) 超出範圍 0..{self.width-1}, 0..{self.height-1}")

    def is_used(self, x: int, y: int) -> bool:
        """這格有沒有被占用"""
        self._check_bounds(x, y)
        return self.cells[x][y] is not None

    def get(self, x: int, y: int) -> Any:
        """取得這格目前的內容 (None / router_id / 物件）"""
        self._check_bounds(x, y)
        return self.cells[x][y]

    def place(self, x: int, y: int, value: Any):
        """在 (x,y) 放一個東西（例如 router_id) """
        self._check_bounds(x, y)
        if self.is_used(x, y):
            raise ValueError(f"格子 ({x}, {y}) 已被使用，不能再放")
        self.cells[x][y] = value

    def remove(self, x: int, y: int):
        """把 (x,y) 清空"""
        self._check_bounds(x, y)
        self.cells[x][y] = None

    # ----- 找空位 -----

    def find_empty(self) -> Optional[Tuple[int, int]]:
        """從 (0,0) 開始掃描，找到第一個空格"""
        for x in range(self.width):
            for y in range(self.height):
                if not self.is_used(x, y):
                    return x, y
        return None

    def find_empty_from(self, start_x: int, start_y: int) -> Optional[Tuple[int, int]]:
        """
        從 (start_x, start_y) 開始往右、往上掃描 grid
        找到下一個空格。
        """
        self._check_bounds(start_x, start_y)

        # 先掃 start_x 那一欄從 start_y 開始
        for y in range(start_y, self.height):
            if not self.is_used(start_x, y):
                return start_x, y

        # 再掃後面的欄位
        for x in range(start_x + 1, self.width):
            for y in range(self.height):
                if not self.is_used(x, y):
                    return x, y

        return None

    # ----- 方便 debug 的文字輸出 -----

    def __str__(self) -> str:
        """
        用 0 / 1 顯示整個 grid(1=占用, 0=空）
        Y 軸由上到下顯示，跟平面圖比較像。
        """
        lines = []
        for y in reversed(range(self.height)):
            row = []
            for x in range(self.width):
                row.append("1" if self.is_used(x, y) else "0")
            lines.append(" ".join(row))
        return "\n".join(lines)
