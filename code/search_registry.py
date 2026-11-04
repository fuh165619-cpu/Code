# ==================== 搜索算法注册表 ====================
# 接入新算法的步骤：
#   1. 新建一个模块（如 A_star_search.py）
#   2. 模块里提供 search_single(initial, upper) 和 search_double(initial, upper)
#      返回值统一为 (是否有解, 路径, 步数)
#   3. 在下面 import 并加进 ALGORITHMS，main / test 就会自动看到它
import BFS_search

ALGORITHMS = {
    'BFS': BFS_search,
}


def get(name):
    # 按名字取算法模块
    return ALGORITHMS[name]


def names():
    # 所有已注册算法的名字
    return list(ALGORITHMS.keys())
