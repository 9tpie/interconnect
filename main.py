from algorithms.area_partition import build_area_partition


if __name__ == "__main__":
    num = int(input("輸入 num (2 的次方，例如 16/32): "))
    grid, blocks = build_area_partition(num, leaf_area=4)

    for nid in sorted(blocks.keys()):
        b = blocks[nid]
        print(f"{nid}: x={b.x0}~{b.x1}, y={b.y0}~{b.y1}, area={b.area}")