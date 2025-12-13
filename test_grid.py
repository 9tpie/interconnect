from data_structure import Grid
from visualize import visualize_grid

def main():
    g = Grid(4, 4)

    # 放幾個 router
    g.place(0, 0, 0)
    g.place(1, 1, 1)
    g.place(2, 2, 2)

    visualize_grid(g)

if __name__ == "__main__":
    main()
