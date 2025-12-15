import math
from typing import List, Tuple

def inter_layer_distances(num_of_core: int) -> Tuple[int, List[int]]:
    """
    依照你圖上的定義：
      n = log2(num_of_core)   # 層數(最上層=layer1)
      t = n - i + 1
      dist(i->i+1) = 2 ^ floor((t-1)/2),  i = 1..n-1
    回傳：(n, distances)
      distances[k-1] = Layer k -> Layer k+1 的距離
    """

    if num_of_core <= 0:
        raise ValueError("num_of_core must be positive")
    if (num_of_core & (num_of_core - 1)) != 0:
        raise ValueError("num_of_core must be a power of 2 (e.g., 2,4,8,16,...)")

    n = int(math.log2(num_of_core))  # 照你的圖：16 -> n=4

    distances: List[int] = []
    for i in range(1, n):  # i = 1..n-1
        t = n - i + 1
        exp = (t - 1) // 2          # 次方部分取整數
        d = 2 ** exp
        distances.append(d)

    return n, distances


if __name__ == "__main__":
    num_of_core = 32
    n, dists = inter_layer_distances(num_of_core)

    print(f"num_of_core={num_of_core}, n_layers={n}")
    for i, d in enumerate(dists, start=1):
        print(f"Layer {i} -> Layer {i+1}: dist = {d}")
