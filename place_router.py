import math

def area_partition(num_of_cores):
    """
    把面積分割成 1:1 or 1:2
    nums_of_cores: 現在的core數量
    目標是把現在的core數量減半 並切割原本的面積為對半
    """
    divide_cores = int(num_of_cores/2)
    divide_level = int(math.log2(divide_cores))
    if divide_level % 2 ==0:
        return (1, 1) # 原面積垂直切割成一半
    else:
        return (1, 2) # 原面積水平切割成一半
    

def find_distance():
    """
    找出每一層的距離為多少
    """
    pass

def place_the_router():
    """
    利用find_distance & area_partition 找到每個router的擺放位置
    """
    pass

def main():
    print(area_partition(16))

if __name__ == '__main__':
    main()