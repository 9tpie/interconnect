import math

def router_in_tree(nums_of_cores):
    """
    depth = 樹的深度（例如你畫的 3 層：1 → 2,3 → 4,5,6,7）
    """
    depth = int(math.log2(nums_of_cores))
    node = 1
    for level in range(1, depth + 1):
        count = 2 ** (level - 1)   # 該層節點數量
        layer_nodes = list(range(node, node + count))
        
        print(f"第 {level} 層：{layer_nodes}")
        
        node += count  # 移動到下一層的開始節點

def core_address(core_id, num_cores):
    bits = int(math.log2(num_cores))
    return format(core_id, f"0{bits}b")

def assign_router(num_cores):
    """
    依照位元翻轉規則分配 router：
    從最高位元 (MSB) 開始掃描，
    只要 core i 和 core i+1 在該 bit 不同，就在中間放一個 router，
    並把這個 router 分配給 core i。
    """
    bits = int(math.log2(num_cores))
    router_id = 1
    router_map = {}  # key: router 編號 (int), value: core 編號 (int)
    used_cores = set()   # 已經分配過 router 的 core


    # 從 MSB 到 LSB
    for bit_idx in range(bits - 1, -1, -1):
        # 掃所有 core 對 (core, core+1)
        for core in range(num_cores - 1):
            b_cur = (core >> bit_idx) & 1
            b_nxt = ((core + 1) >> bit_idx) & 1

            # 這個 bit 有 0/1 翻轉，而且這個 core 還沒被用過
            if b_cur != b_nxt and core not in used_cores:
                router_map[router_id] = core
                used_cores.add(core)
                router_id += 1

                # 16 cores → 只需要 15 個 router
                if router_id > num_cores - 1:
                    return router_map

                

    return router_map

