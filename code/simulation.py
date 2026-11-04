# ==================== 模拟运行规则 ====================
# 视觉部分：守卫的可见性判定（120度视野锥 + 被墙遮挡则不可见）
#   block / can_see / visible_mask_at 会被搜索频繁调用，都做了记忆化
# 规则部分：
#   check：检查当前状态是否安全（每个空地要么已被清除，要么正被某个守卫看到）
#   动作系统：只有六种动作——上、下、左、右、逆时针转、顺时针转
#
# 性能说明：
#   搜索每展开一个后继都要做一次安全性检查，原来的 check 每次都要遍历全图、
#   逐格调用 block / can_see。这里把"某个 (位置, 面向) 在格子未清除时会判定为
#   不安全的格子集合"预先压成位掩码（exposed_mask），check 退化成几次位运算；
#   可见性也改成按 (格子, 守卫位置) 缓存 12 个面向的可见位（角度只算一次）。
#   判定结果与原逐格实现完全一致（单人和双人的语义都保持不变）。
import math
import constants

block_cache = {}


def block(position1, position2):
    # 判断两格连线之间是否被墙挡住：沿连线密集采样，踩到墙格即算挡住
    # 两个点重合视为没被挡住（调用时会避免这种情况），端点格子本身不算遮挡
    key = (position1, position2)
    cached = block_cache.get(key)
    if cached is not None:
        return cached
    x1, y1 = position1
    x2, y2 = position2
    step = max(abs(x1 - x2), abs(y1 - y2)) * 20
    blocked = False
    if step > 1:
        map1 = constants.map1
        width, height = constants.width, constants.height
        for i in range(1, step):
            t = i / step
            ix = int(round((1 - t) * x1 + t * x2))
            iy = int(round((1 - t) * y1 + t * y2))
            if (0 <= ix < width and 0 <= iy < height and map1[ix][iy] != 0
                    and (ix, iy) != position1 and (ix, iy) != position2):
                blocked = True
                break
    block_cache[key] = blocked
    return blocked


# 每个 (格子, 守卫位置) 能看到它的面向集合（12 位掩码），角度只算一次
_ALL_FACES = (1 << 12) - 1
_see_faces_cache = {}


def _see_faces(position, guard):
    key = (position, guard)
    faces = _see_faces_cache.get(key)
    if faces is not None:
        return faces
    if not constants.is_open(*position):
        faces = 0
    elif position == guard:
        faces = _ALL_FACES
    elif block(position, guard):
        faces = 0
    else:
        # 视野锥为面朝方向左右各60度，共120度
        theta = math.atan2(position[1] - guard[1], position[0] - guard[0])
        limit = 2 * math.pi / 3 + constants.eps
        faces = 0
        for face in range(12):
            if (theta - face * math.pi / 6) % (2 * math.pi) <= limit:
                faces |= 1 << face
    _see_faces_cache[key] = faces
    return faces


def can_see(position, guard, face):
    # position 能否被守卫看到
    # face 用整数标记，取值 0-11，实际角度 = face * 30 度
    return bool(_see_faces(position, guard) >> int(face) & 1)


visible_mask_at_cache = {}


def visible_mask_at(position, face):
    # 该状态下守卫能看到的全部格子，压成一个位掩码
    face = int(face)
    key = (position, face)
    result = visible_mask_at_cache.get(key)
    if result is not None:
        return result
    result = 0
    for i in range(constants.width):
        for j in range(constants.height):
            if _see_faces((i, j), position) >> face & 1:
                result |= 1 << constants.idx(i, j)
    visible_mask_at_cache[key] = result
    return result


# ---------- 缓存管理 ----------


def clear_caches():
    # 清空本模块的全部记忆化缓存。
    # 缓存的 key 不含地图信息，所以每次更换地图后必须清空，否则会读到旧地图的结果
    block_cache.clear()
    _see_faces_cache.clear()
    visible_mask_at_cache.clear()
    los_mask_cache.clear()
    exposed_mask_cache.clear()


# ---------- 安全性检查 ----------

los_mask_cache = {}


def los_mask(position):
    # 与 position 之间"没有墙挡住视线"的所有空地，压成位掩码
    mask = los_mask_cache.get(position)
    if mask is None:
        mask = 0
        for i in range(constants.width):
            for j in range(constants.height):
                if constants.is_open(i, j) and not block((i, j), position):
                    mask |= 1 << constants.idx(i, j)
        los_mask_cache[position] = mask
    return mask


exposed_mask_cache = {}


def exposed_mask(position, face):
    # 该 (位置, 面向) 下"没有被看到、但又能看到守卫"的格子：
    # 这些格子只要还没被清除，就说明守卫会先被对方发现，状态不安全。
    face = int(face)
    key = (position, face)
    mask = exposed_mask_cache.get(key)
    if mask is None:
        mask = los_mask(position) & ~visible_mask_at(position, face)
        exposed_mask_cache[key] = mask
    return mask


def check(position1, face1, position2=(-1, -1), face2=0, cleared_mask=0):
    # face 用整数标记，取值 0-11，实际角度 = face * math.pi / 6
    # position2 = (-1, -1) 表示单人模式
    # 逐格判定的等价写法：
    #   单人：存在"有视线但没被看到且未清除"的格子 -> 不安全
    #   双人：存在"对两个守卫都有视线、都没被看到且未清除"的格子 -> 不安全
    if position2 == (-1, -1):
        return not (exposed_mask(position1, face1) & ~cleared_mask)
    return not (exposed_mask(position1, face1) & exposed_mask(position2, face2)
                & ~cleared_mask)


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
