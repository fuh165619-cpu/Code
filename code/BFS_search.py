# ==================== 搜索算法：广度优先（BFS） ====================
# 保证找到的路径步数最短
# 带步数上界剪枝：depth 超过 upper 直接失败返回。
# 注意：因为有上界的存在，search_single / search_double 单独调用可能会返回假阴性，
# 主流程里用"当前已知最优步数"作为上界迭代调用，最后得到的就是真正的最优解。
# 接口约定：所有搜索模块都提供 search_single / search_double 两个名字，
# 返回值统一为 (是否有解, 路径, 步数)，由 search_registry 注册后接入 main / test。
import collections
import constants
from simulation import visible_mask_at, check, next_step_generator

# 六种动作：上、下、左、右、逆时针转 delta、顺时针转 delta
ACTIONS = ['up', 'down', 'left', 'right', 'anticlock', 'clock']


def _build_path(state, parent, action):
    # 从终点状态沿 parent 回溯，重建动作序列
    path = []
    cur = state
    while parent[cur] is not None:
        path.append(action[cur])
        cur = parent[cur]
    path.reverse()
    return path


def search1(initial, upper):
    # 单人搜索。initial 是三元组：守卫位置、面向、已清除集合（位掩码）
    queue = collections.deque([initial])
    seen = {initial}
    parent = {initial: None}
    action = {initial: None}
    depth = {initial: 0}
    # 初始状态的合法性检验
    if not check(initial[0], initial[1], cleared_mask=initial[2]):
        return False, None, -1
    while queue:
        state = queue.popleft()
        # 终止条件：所有空地都被看过了
        if state[2] == constants.all_empty_mask:
            return True, _build_path(state, parent, action), depth[state]
        if depth[state] >= upper:
            return False, None, -1
        # 单人共 6 种后继：上、下、左、右、逆时针转 delta、顺时针转 delta
        guard, face = state[0], state[1]
        nxt = [
            ((guard[0], guard[1] + 1), face, state[2], 'up'),
            ((guard[0], guard[1] - 1), face, state[2], 'down'),
            ((guard[0] - 1, guard[1]), face, state[2], 'left'),
            ((guard[0] + 1, guard[1]), face, state[2], 'right'),
            (guard, (face + constants.delta) % 12, state[2], 'anticlock'),
            (guard, (face - constants.delta) % 12, state[2], 'clock'),
        ]
        for g, f, m, act in nxt:
            if constants.in_bounds(g[0], g[1]) and constants.is_open(g[0], g[1]):
                # 先过一遍 check：这一步走完不能有"漏看且看不到"的格子
                if check(g, f, cleared_mask=m):
                    new_m = m | visible_mask_at(g, f)
                    ns = (g, f, new_m)
                    if ns not in seen:
                        seen.add(ns)
                        queue.append(ns)
                        parent[ns] = state
                        action[ns] = act
                        depth[ns] = depth[state] + 1
    return False, None, -1


def search2(initial, upper):
    # 双人搜索。initial 是五元组：守卫1位置、面向、守卫2位置、面向、已清除集合
    # 每次生成后继有 6*6=36 种组合
    queue = collections.deque([initial])
    seen = {initial}
    parent = {initial: None}
    action = {initial: None}
    depth = {initial: 0}
    if not check(initial[0], initial[1], initial[2], initial[3], initial[4]):
        return False, None, -1
    while queue:
        state = queue.popleft()
        if state[4] == constants.all_empty_mask:
            return True, _build_path(state, parent, action), depth[state]
        if depth[state] >= upper:
            return False, None, -1
        for a1 in ACTIONS:
            for a2 in ACTIONS:
                ns, act1, act2 = next_step_generator(state, a1, a2)
                g1, f1, g2, f2, m = ns
                if (constants.in_bounds(g1[0], g1[1]) and constants.in_bounds(g2[0], g2[1]) and
                        constants.is_open(g1[0], g1[1]) and constants.is_open(g2[0], g2[1])):
                    if check(g1, f1, g2, f2, m):
                        new_m = (m | visible_mask_at(g1, f1)) | visible_mask_at(g2, f2)
                        ns2 = (g1, f1, g2, f2, new_m)
                        if ns2 not in seen:
                            seen.add(ns2)
                            queue.append(ns2)
                            parent[ns2] = state
                            action[ns2] = (act1, act2)
                            depth[ns2] = depth[state] + 1
    return False, None, -1


# 统一接口别名：main / test 通过 search_registry 按这两个名字调用
search_single = search1
search_double = search2
