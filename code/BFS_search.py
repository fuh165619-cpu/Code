# ==================== 搜索算法：广度优先（BFS） ====================
# 保证找到的路径步数最短
# 带步数上界剪枝：depth 超过 upper 直接失败返回。
# 注意：因为有上界的存在，search_single / search_double 单独调用可能会返回假阴性，
# 主流程里用"当前已知最优步数"作为上界迭代调用，最后得到的就是真正的最优解。
# 接口约定：所有搜索模块都提供 search_single / search_double 两个名字，
# 返回值统一为 (是否有解, 路径, 步数)，由 search_registry 注册后接入 main / test。
import collections
import constants
from simulation import visible_mask_at, check

# 六种动作：上、下、左、右、逆时针转 delta、顺时针转 delta
ACTIONS = ['up', 'down', 'left', 'right', 'anticlock', 'clock']

# 与 simulation.apply_one 完全一致的位移量，用于内联展开后继
_STEPS = (((0, 1), 'up'), ((0, -1), 'down'), ((-1, 0), 'left'), ((1, 0), 'right'))


def _build_path(state, parent):
    # 从终点状态沿 parent 回溯，重建动作序列
    # parent[state] = (上一步状态, 动作)
    path = []
    while state in parent:
        state, act = parent[state]
        path.append(act)
    path.reverse()
    return path


def _successors(pos, face):
    # 该守卫一步能到达的合法 (位置, 面向, 动作)：四个方向 + 逆/顺时针转
    # 相当于提前做掉原实现里每个后继都要做的"越界 / 撞墙"过滤
    x, y = pos
    map1 = constants.map1
    width, height = constants.width, constants.height
    out = []
    for (dx, dy), act in _STEPS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height and map1[nx][ny] == 0:
            out.append(((nx, ny), face, act))
    delta = constants.delta
    out.append((pos, (face + delta) % 12, 'anticlock'))
    out.append((pos, (face - delta) % 12, 'clock'))
    return out


def search1(initial, upper):
    # 单人搜索。initial 是三元组：守卫位置、面向、已清除集合（位掩码）
    if not check(initial[0], initial[1], cleared_mask=initial[2]):
        return False, None, -1
    all_empty = constants.all_empty_mask
    queue = collections.deque([(initial, 0)])
    seen = {initial}
    parent = {}
    while queue:
        state, depth = queue.popleft()
        guard, face, cleared = state
        # 终止条件：所有空地都被看过了
        if cleared == all_empty:
            return True, _build_path(state, parent), depth
        if depth >= upper:
            return False, None, -1
        next_depth = depth + 1
        for g, f, act in _successors(guard, face):
            # 先过一遍 check：这一步走完不能有"漏看且看不到"的格子
            if not check(g, f, cleared_mask=cleared):
                continue
            new_state = (g, f, cleared | visible_mask_at(g, f))
            if new_state not in seen:
                seen.add(new_state)
                parent[new_state] = (state, act)
                queue.append((new_state, next_depth))
    return False, None, -1


def search2(initial, upper):
    # 双人搜索。initial 是五元组：守卫1位置、面向、守卫2位置、面向、已清除集合
    # 每次生成后继有 6*6=36 种组合
    if not check(initial[0], initial[1], initial[2], initial[3], initial[4]):
        return False, None, -1
    all_empty = constants.all_empty_mask
    queue = collections.deque([(initial, 0)])
    seen = {initial}
    parent = {}
    while queue:
        state, depth = queue.popleft()
        g1, f1, g2, f2, cleared = state
        if cleared == all_empty:
            return True, _build_path(state, parent), depth
        if depth >= upper:
            return False, None, -1
        next_depth = depth + 1
        # 先分别算好两个守卫各自的合法动作，36 种组合里不再重复过滤
        opts1 = _successors(g1, f1)
        opts2 = _successors(g2, f2)
        for ng1, nf1, a1 in opts1:
            for ng2, nf2, a2 in opts2:
                if not check(ng1, nf1, ng2, nf2, cleared):
                    continue
                new_state = (ng1, nf1, ng2, nf2,
                             cleared | visible_mask_at(ng1, nf1)
                             | visible_mask_at(ng2, nf2))
                if new_state not in seen:
                    seen.add(new_state)
                    parent[new_state] = (state, (a1, a2))
                    queue.append((new_state, next_depth))
    return False, None, -1


# 统一接口别名：main / test 通过 search_registry 按这两个名字调用
search_single = search1
search_double = search2
