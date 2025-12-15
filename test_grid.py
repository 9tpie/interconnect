from data_structure import Grid
from visualize import visualize_grid
import math 

def calculate_x_y(num):
    
    root = math.sqrt(num)
    
    y = int(root)
    
    if root.is_integer():
        x = y
    else:
        x = y * 2
        
    return x, y

def get_children(parent):
    left = parent * 2
    right = parent * 2 + 1
    return left, right

def get_level(node):
    if node < 1:
        raise ValueError("節點編號必須 >= 1")
    return int(math.log2(node)) + 1


def main():

    num_of_core = 16
    x, y = calculate_x_y(num_of_core)
    g = Grid(x, y)

    # 放幾個 router
    # g.place(0, 0, 0)
    # g.place(1, 1, 1)
    # g.place(2, 2, 2)

    # visualize_grid(g)

    for i in range(1, num_of_core):
        print(f"節點 {i} 在第 {get_level(i)} 層")

if __name__ == "__main__":
    main()
 