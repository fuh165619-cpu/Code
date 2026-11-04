# ==================== 搜索算法：位掩码 + 支配剪枝的最优搜索 ====================
# 与 BFS_search 完全相同的对外接口，返回的也是"最少步数"意义下的最优解，
# 但通过下面三层优化，在需要展开大量状态的地图（尤其是双人搜索）上
# 比逐格判定的 BFS 快一个数量级以上：
#
#   1. 安全性检查 O(1) 化
#      simulation.check 每次要遍历全图所有格子，逐格调用 block / can_see。
#      这里在搜索开始前把每个 (位置, 面向) 的"暴露集合"预计算成位掩码：
#          exposed(sid) = { 未清除时会判定为不安全的格子 }
#      之后每一步只需一次位运算 exposed(nsid) & ~cleared 就能判断是否安全，
#      而且与 simulation.check 的判定逐格等价（含单人 / 双人的边界语义）。
#
#   2. 后继动作预计算 + 状态整数编码
#      每个 (位置, 面向) 的合法后继（上/下/左/右/逆时针/顺时针）只算一次，
#      连"这一步能新看到哪些格子"的位掩码一起缓存；状态打包成整数，
#      用位运算拼 key，避免反复构造元组、降低哈希开销。
#
#   3. 支配剪枝（本模块最大的加速来源）
#      如果两个状态守卫的位置和面向完全相同，而 A 的已清除集合包含 B 的，
#      并且 A 的步数不大于 B，那么 B 的所有后续走法从 A 出发同样合法、
#      而且只会清得更多。因此 B 被 A 支配，可以安全地整枝丢掉。
#      BFS 按步数分层扩展，天然保证先入队的更浅，所以只需在同一
#      (位置, 面向) 上维护一个"极大已清除集合"的反链即可。
#
# 说明：这里没有用堆式 A*。本题可用的启发式（剩余格子数、最远格距离等）
# 非常弱，而状态数极多，堆的 log 开销和新状态排序反而比 BFS 慢；最优性
# 又要求启发式可采纳。因此最终实现是"带位掩码与支配剪枝的最优 BFS"，
# 它保留了 A* 的完备性与最优性，却没有堆开销。
#
# 接口约定：search_single / search_double，返回 (是否有解, 路径, 步数)，
# 与 BFS_search 一致，可直接在 search_registry 里注册给 main / test 使用。
import constants
import simulation

# 六种动作，顺序与 BFS_search 保持一致（便于对照调试与复现）
ACTIONS = ('up', 'down', 'left', 'right', 'anticlock', 'clock')

# 四个平移动作的位移量，与 BFS_search 中 up/down/left/right 的定义完全一致
_MOVES = ((0, 1), (0, -1), (-1, 0), (1, 0))

# 每个 (位置, 面向) 最多记录多少个"极大已清除集合"。
# 反链长度理论上可能变大；超过上限就对该 (位置, 面向) 停止继续加剪枝记录，
# 这只减少剪枝、不影响正确性，用来防止极端地图上剪枝本身变成瓶颈。
_FRONT_CAP = 48


class _MapData:
    # 与当前地图 / 转头角度绑定的一份预计算数据。
    # 地图或 delta 改变后整份重建（判断方式见 _current）。
    __slots__ = (
        'map1', 'width', 'height', 'delta', 'npos', 'nsid', 'all_open', 'bits',
        'pos_xy', 'sid_pos',
        '_vis', '_exp', '_trans',
    )

    def __init__(self):
        self.map1 = constants.map1
        self.width = constants.width
        self.height = constants.height
        self.delta = int(constants.delta)      # 只支持 1 / 2，转成整数避免浮点 key
        self.npos = self.width * self.height
        self.nsid = 12 * self.npos
        self.all_open = constants.all_empty_mask
        # 打包 key 时用来装下 sid 的位数
        self.bits = max(1, (self.nsid - 1).bit_length())

        width, height, map1 = self.width, self.height, constants.map1
        # 下标 -> 坐标、状态编号 -> 位置下标（搜索热路径直接查表）
        self.pos_xy = [(i // height, i % height) for i in range(self.npos)]
        self.sid_pos = [i // 12 for i in range(self.nsid)]

        self._vis = {}      # sid -> 可见格子位掩码
        self._exp = {}      # sid -> 暴露集合（未清除时判定为不安全的格子）
        self._trans = {}    # sid -> 合法后继 ((nsid, 动作编号, 新增可见掩码, 后继暴露集合), ...)

    # ---------- 位掩码预计算 ----------

    def vis(self, sid):
        # 该状态能看到的全部格子（复用 simulation 的记忆化结果，保证与判定一致）
        mask = self._vis.get(sid)
        if mask is None:
            pidx = self.sid_pos[sid]
            mask = simulation.visible_mask_at(self.pos_xy[pidx], sid % 12)
            self._vis[sid] = mask
        return mask

    def exposed(self, sid):
        # 暴露集合 = 有视线 + 没被看到 -> 只要还没清除就判定为不安全。
        # 单人的判据：exposed & ~cleared == 0
        # 双人的判据：exposed1 & exposed2 & ~cleared == 0
        # 这里直接复用 simulation 的暴露集合缓存（与 check 的判定完全同源）
        mask = self._exp.get(sid)
        if mask is None:
            pidx = self.sid_pos[sid]
            mask = simulation.exposed_mask(self.pos_xy[pidx], sid % 12)
            self._exp[sid] = mask
        return mask

    def trans(self, sid):
        # 预计算该状态的六个候选后继（上/下/左/右/逆时针/顺时针），
        # 只保留"在新位置且是空地"的那些，与 BFS_search 的过滤条件一致。
        table = self._trans.get(sid)
        if table is not None:
            return table
        pidx = self.sid_pos[sid]
        face = sid % 12
        x, y = self.pos_xy[pidx]
        width, height, map1 = self.width, self.height, self.map1
        out = []
        # 每项都预先带好：后继状态编号、动作编号、这一步新看到的掩码、后继的暴露集合
        for act, (dx, dy) in enumerate(_MOVES):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and map1[nx][ny] == 0:
                nsid = (nx * height + ny) * 12 + face
                out.append((nsid, act, self.vis(nsid), self.exposed(nsid)))
        delta = self.delta
        nsid = pidx * 12 + (face + delta) % 12      # 逆时针
        out.append((nsid, 4, self.vis(nsid), self.exposed(nsid)))
        nsid = pidx * 12 + (face - delta) % 12      # 顺时针
        out.append((nsid, 5, self.vis(nsid), self.exposed(nsid)))
        table = tuple(out)
        self._trans[sid] = table
        return table


# 当前预计算数据与其绑定的地图对象；用 is 比较判断是否需要重建，
# 同时持有 map1 的引用，避免旧列表被回收后判断出现歧义。
_DATA = None


def _current():
    global _DATA
    data = _DATA
    if (data is None or data.map1 is not constants.map1
            or data.delta != int(constants.delta)):
        data = _MapData()
        _DATA = data
    return data


def reset():
    # 主动丢弃预计算数据（换地图时可由外部调用；不调用也会自动检测重建）
    global _DATA
    _DATA = None


def _rebuild_single(parent, key):
    # 沿 parent 链回溯动作编号，再翻译成动作名
    acts = []
    while key in parent:
        value = parent[key]
        acts.append(ACTIONS[value & 7])
        key = value >> 3
    acts.reverse()
    return acts


def _rebuild_double(parent, key):
    # 双人动作编码为 a1 * 6 + a2
    acts = []
    while key in parent:
        value = parent[key]
        code = value & 63
        acts.append((ACTIONS[code // 6], ACTIONS[code % 6]))
        key = value >> 6
    acts.reverse()
    return acts


def search_single(initial, upper):
    # 单人搜索。initial = (守卫位置, 面向, 已清除集合位掩码)
    # upper 是步数上界：只找步数不超过 upper 的解，超过的层不再展开。
    data = _current()
    pos, face, cleared = initial
    pidx = pos[0] * data.height + pos[1]
    sid = pidx * 12 + int(face)
    exposed = data.exposed
    if exposed(sid) & ~cleared:                # 初始状态本身就不安全
        return False, None, -1
    goal = data.all_open
    if cleared == goal:                        # 起点就已经清完（地图只有起点）
        return True, [], 0
    if upper <= 0:
        return False, None, -1

    bits = data.bits
    trans = data.trans
    parent = {}                                # 状态 key -> (父 key << 3 | 动作编号)
    frontier = [(sid, cleared)]
    front = {sid: [cleared]}                   # (位置, 面向) -> 极大已清除集合反链
    fget = front.get                           # 绑成局部变量，减少热循环里的属性查找
    depth = 0
    cap = _FRONT_CAP

    while frontier and depth < upper:
        depth += 1
        nxt = []
        for psid, m in frontier:
            pkey = (m << bits) | psid
            not_m = ~m
            for nsid, act, add, e in trans(psid):
                if e & not_m:                  # 走完不安全（用走之前的清除集合判定）
                    continue
                nm = m | add
                if nm == goal:                 # 到达目标，回溯路径立即返回
                    key = (nm << bits) | nsid
                    parent[key] = (pkey << 3) | act
                    return True, _rebuild_single(parent, key), depth
                # ---- 支配剪枝：同一 (位置, 面向) 下已被更大的清除集合支配 ----
                lst = fget(nsid)
                if lst is None:
                    front[nsid] = [nm]
                else:
                    dominated = False
                    for k in lst:
                        if k & nm == nm:       # 已有的集合包含新集合
                            dominated = True
                            break
                    if dominated:
                        continue
                    if len(lst) < cap:
                        # 新集合包含旧集合时，旧集合对未来剪枝不再有额外作用
                        if any(k & nm == k for k in lst):
                            lst = [k for k in lst if k & nm != k]
                            front[nsid] = lst
                        lst.append(nm)
                key = (nm << bits) | nsid
                parent[key] = (pkey << 3) | act
                nxt.append((nsid, nm))
        frontier = nxt
    return False, None, -1


def search_double(initial, upper):
    # 双人搜索。initial = (守卫1位置, 面向1, 守卫2位置, 面向2, 已清除集合)
    # 每个状态 6 * 6 = 36 个后继，同样带步数上界与支配剪枝。
    data = _current()
    pos1, face1, pos2, face2, cleared = initial
    p1 = pos1[0] * data.height + pos1[1]
    p2 = pos2[0] * data.height + pos2[1]
    sid1 = p1 * 12 + int(face1)
    sid2 = p2 * 12 + int(face2)
    exposed = data.exposed
    if exposed(sid1) & exposed(sid2) & ~cleared:   # 初始状态不安全
        return False, None, -1
    goal = data.all_open
    if cleared == goal:
        return True, [], 0
    if upper <= 0:
        return False, None, -1

    nsid_total = data.nsid
    bits = max(1, (nsid_total * nsid_total - 1).bit_length())
    trans = data.trans
    parent = {}
    frontier = [(sid1, sid2, cleared)]
    front = {sid1 * nsid_total + sid2: [cleared]}
    fget = front.get
    depth = 0
    cap = _FRONT_CAP

    while frontier and depth < upper:
        depth += 1
        nxt = []
        for ps1, ps2, m in frontier:
            pkey = (m << bits) | (ps1 * nsid_total + ps2)
            not_m = ~m
            # t1 / t2 的每一项已经带好后继的暴露集合，36 次循环里不再查表
            t1 = trans(ps1)
            t2 = trans(ps2)
            for n1, a1, add1, e1 in t1:
                base = m | add1
                for n2, a2, add2, e2 in t2:
                    if e1 & e2 & not_m:        # 双人判据：两边都暴露才算不安全
                        continue
                    nm = base | add2
                    if nm == goal:
                        key = (nm << bits) | (n1 * nsid_total + n2)
                        parent[key] = (pkey << 6) | (a1 * 6 + a2)
                        return True, _rebuild_double(parent, key), depth
                    sid = n1 * nsid_total + n2
                    lst = fget(sid)
                    if lst is None:
                        front[sid] = [nm]
                    else:
                        dominated = False
                        for k in lst:
                            if k & nm == nm:
                                dominated = True
                                break
                        if dominated:
                            continue
                        if len(lst) < cap:
                            if any(k & nm == k for k in lst):
                                lst = [k for k in lst if k & nm != k]
                                front[sid] = lst
                            lst.append(nm)
                    key = (nm << bits) | sid
                    parent[key] = (pkey << 6) | (a1 * 6 + a2)
                    nxt.append((n1, n2, nm))
        frontier = nxt
    return False, None, -1


# 与 BFS_search 相同的别名，方便老代码 / 文档按 search1 / search2 调用
search1 = search_single
search2 = search_double
