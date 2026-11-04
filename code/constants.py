# ==================== 常数与共享状态 ====================
import os

# eps 很多地方都要用，直接当全局常数
eps = 0.0001

# 运行生成的文件（动画 gif、对比图、解路径等）统一放在项目根目录
# （代码文件夹的上一级）的 output 文件夹里。
# 用代码文件的位置推算绝对路径，跟从哪个目录启动 python 无关，
# 避免在不同目录运行时生成多个 output。
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(_PROJECT_ROOT, 'output')


def output_path(filename):
    # 返回输出文件夹内的完整路径，文件夹不存在时自动创建
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return os.path.join(OUTPUT_DIR, filename)

# 下面这些原来散落各处的全局变量，拆分模块后统一放在这里。
# 其他模块一律用 constants.xxx 的方式读写，保证状态同步。
# width / height / map1 / delta 由 main 启动时通过 user_input 模块填充。
width = 0
height = 0
map1 = []       # map1[x][y]，左上角是(0,0)，x轴水平向右，y轴水平向下；0=空地，1=墙
delta = 0       # 每次转头的角度，用整数标记：1=30度，2=60度
all_empty_mask = 0  # 所有空格子的位掩码，由 search.find_all_empty_mask 填充


def idx(x, y):
    # 输入 x, y 得到位掩码的下标
    return x * height + y


def in_bounds(x, y):
    # 坐标是否在地图内
    return 0 <= x < width and 0 <= y < height


def is_open(x, y):
    # 是否为空地（非墙）
    return map1[x][y] == 0
