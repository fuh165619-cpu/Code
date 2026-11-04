# ==================== 模拟运行规则 ====================
# 视觉部分：守卫的可见性判定（120度视野锥 + 被墙遮挡则不可见）
#   block / can_see / visible_mask_at 会被搜索频繁调用，都做了记忆化
# 规则部分：
#   check：检查当前状态是否安全（每个空地要么已被清除，要么正被某个守卫看到）
#   动作系统：只有六种动作——上、下、左、右、逆时针转、顺时针转
import math
import constants

block_cache = {}


def block(position1, position2):
    # 判断两格连线之间是否被墙挡住：沿连线密集采样，踩到墙格即算挡住
    # 两个点重合视为没被挡住（调用时会避免这种情况），端点格子本身不算遮挡
    if (position1, position2) in block_cache:
        return block_cache[(position1, position2)]
    x1, y1 = position1
    x2, y2 = position2
    step = max(abs(x1 - x2), abs(y1 - y2)) * 20
    for i in range(1, step):
        t = i / step
        x = (1 - t) * x1 + t * x2
        y = (1 - t) * y1 + t * y2
        ix = int(round(x))
        iy = int(round(y))
        if not constants.is_open(ix, iy) and not (ix, iy) in [position1, position2]:
            block_cache[(position1, position2)] = True
            return True
    block_cache[(position1, position2)] = False
    return False


can_see_cache = {}


def can_see(position, guard, face):
    # position 能否被守卫看到
    # face 用整数标记，取值 0-11，实际角度 = face * 30 度
    if (position, guard, face) in can_see_cache:
        return can_see_cache[(position, guard, face)]
    if not constants.is_open(*position):
        can_see_cache[position, guard, face] = False
        return False
    if position == guard:
        can_see_cache[position, guard, face] = True
        return True
    if block(position, guard):
        can_see_cache[position, guard, face] = False
        return False
    # 视野锥为面朝方向左右各60度，共120度
    if (math.atan2(position[1] - guard[1], position[0] - guard[0]) - face * math.pi / 6) % (2 * math.pi) <= 2 * math.pi / 3 + constants.eps:
        can_see_cache[position, guard, face] = True
        return True
    can_see_cache[position, guard, face] = False
    return False


visible_mask_at_cache = {}


def visible_mask_at(position, face):
    # 该状态下守卫能看到的全部格子，压成一个位掩码
    if (position, face) in visible_mask_at_cache:
        return visible_mask_at_cache[(position, face)]
    result = 0
    for i in range(constants.width):
        for j in range(constants.height):
            if can_see((i, j), position, face):
                result |= 1 << constants.idx(i, j)
    visible_mask_at_cache[(position, face)] = result
    return result


# ---------- 缓存管理 ----------


def clear_caches():
    # 清空本模块的全部记忆化缓存。
    # 缓存的 key 不含地图信息，所以每次更换地图后必须清空，否则会读到旧地图的结果
    block_cache.clear()
    can_see_cache.clear()
    visible_mask_at_cache.clear()
    check_cache.clear()


# ---------- 安全性检查 ----------

check_cache = {}


def check(position1, face1, position2=(-1, -1), face2=0, cleared_mask=0):
    # face 用整数标记，取值 0-11，实际角度 = face * math.pi / 6
    # position2 = (-1, -1) 表示单人模式
    key = (position1, face1, position2, face2, cleared_mask)
    if key in check_cache:
        return check_cache[key]
    for i in range(constants.width):
        for j in range(constants.height):
            if (cleared_mask >> constants.idx(i, j)) & 1:
                continue
            if not constants.is_open(i, j):
                continue
            if (i, j) == position1 or (i, j) == position2:
                continue
            if block((i, j), position1):
                continue
            if position2 != (-1, -1) and block((i, j), position2):
                continue
            if can_see((i, j), position1, face1):
                continue
            if position2 != (-1, -1) and can_see((i, j), position2, face2):
                continue
            check_cache[key] = False
            return False
    check_cache[key] = True
    return True


# 移动动作对应的位移量
_MOVES = {
    'up': (0, 1), 'down': (0, -1), 'left': (-1, 0), 'right': (1, 0),
}


def apply_one(pos, face, act):
    # 执行单步动作，返回新的 (位置, 面向)
    if act in _MOVES:
        dx, dy = _MOVES[act]
        return (pos[0] + dx, pos[1] + dy), face
    if act == 'anticlock':
        return pos, (face + constants.delta) % 12
    if act == 'clock':
        return pos, (face - constants.delta) % 12
    raise ValueError(f"apply_one 收到未知动作: {act!r}")


def next_step_generator(state, action1, action2):
    # 双人状态是一个五元组：守卫1位置、守卫1面向、守卫2位置、守卫2面向、已清除集合
    # action1 / action2 各有六种取值；两个动作一起返回，方便后面记录 path
    guard1, face1, guard2, face2, cleared_mask = state
    new_guard1, new_face1 = apply_one(guard1, face1, action1)
    new_guard2, new_face2 = apply_one(guard2, face2, action2)
    new_state = (new_guard1, new_face1, new_guard2, new_face2, cleared_mask)
    return new_state, action1, action2


# ---------- 状态准备 ----------

def find_all_empty_mask():
    # 生成所有空格子的位掩码，存入共享状态并返回
    # 与具体搜索算法无关，所以放在这里而不是某个算法模块里
    m = 0
    for i in range(constants.width):
        for j in range(constants.height):
            if constants.is_open(i, j):
                m |= 1 << constants.idx(i, j)
    constants.all_empty_mask = m
    return m
