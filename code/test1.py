import math
import collections
import numpy as np
import matplotlib
matplotlib.use('TkAgg')          # 强制有界面后端；若报错改 'QtAgg'
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.patches as mpatches

# ==================== 输入模块 ====================
width = int(input("width: "))
height = int(input("height: "))
if width <= 0 or height <= 0:
    print("地图大小必须大于0")
    exit(1)

map1 = [[0 for _ in range(height)] for _ in range(width)]
eps = 0.0001

temp = int(input('请输入每次转头的角度delta，只能是30或60：'))
while temp not in [30, 60]:
    print('错误！当前版本只支持取delta为30或60！')
    temp = int(input('请输入每次转头的角度delta，只能是30或60：'))
delta = temp / 30

def idx(x, y):
    return x * height + y

def input2():
    print(f'请按行输入地图，共 {height} 行，每行 {width} 个字符（0=空，1=墙）')
    for i in range(height):
        while True:
            temp = input(f"第 {i+1} 行: ").strip()
            if len(temp) != width:
                print("输入的格子数与列数不符，请重新输入")
                continue
            for j in range(width):
                map1[j][i] = int(temp[j])
            break

def input_start():
    start_x, start_y = (int(i.strip()) for i in input("请输入起始格子的坐标（x, y）: ").split(","))
    while not (0 <= start_x < width and 0 <= start_y < height and map1[start_x][start_y] == 0):
        print('错误！起始格子必须在地图内且不为墙格！')
        start_x, start_y = (int(i.strip()) for i in input("请输入起始格子的坐标（x, y）: ").split(","))
    return start_x, start_y

# ==================== 视线遮挡 / 可见性 ====================
block_cache = {}
def block(position1, position2):
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
        if map1[ix][iy] == 1 and not (ix, iy) in [position1, position2]:
            block_cache[(position1, position2)] = True
            return True
    block_cache[(position1, position2)] = False
    return False

can_see_cache = {}
def can_see(position, guard, face):
    if (position, guard, face) in can_see_cache:
        return can_see_cache[(position, guard, face)]
    if map1[position[0]][position[1]] == 1:
        can_see_cache[position, guard, face] = False
        return False
    if position == guard:
        can_see_cache[position, guard, face] = True
        return True
    if block(position, guard):
        can_see_cache[position, guard, face] = False
        return False
    if (math.atan2(position[1] - guard[1], position[0] - guard[0]) - face * math.pi / 6) % (2 * math.pi) <= 2 * math.pi / 3 + eps:
        can_see_cache[position, guard, face] = True
        return True
    can_see_cache[position, guard, face] = False
    return False

visible_mask_at_cache = {}
def visible_mask_at(position, face):
    if (position, face) in visible_mask_at_cache:
        return visible_mask_at_cache[(position, face)]
    result = 0
    for i in range(width):
        for j in range(height):
            if can_see((i, j), position, face):
                result |= 1 << idx(i, j)
    visible_mask_at_cache[(position, face)] = result
    return result

def check(position1, face1, position2=(-1, -1), face2=0, cleared_mask=0):
    for i in range(width):
        for j in range(height):
            if (cleared_mask >> idx(i, j)) & 1:
                continue
            if map1[i][j] == 1:
                continue
            if (i, j) == position1 or (i, j) == position2:
                continue
            if block((i, j), position1):
                continue
            if position2 != (-1, -1):
                if block((i, j), position2):
                    continue
            if can_see((i, j), position1, face1):
                continue
            if position2 != (-1, -1):
                if can_see((i, j), position2, face2):
                    continue
            return False
    return True

# ==================== 搜索 ====================
all_empty_mask = 0
def find_all_empty_mask():
    m = 0
    for i in range(width):
        for j in range(height):
            if map1[i][j] == 0:
                m |= 1 << idx(i, j)
    return m

def search1(initial):
    queue = collections.deque([initial])
    seen = {initial}
    parent = {initial: None}
    action = {initial: None}
    if not check(initial[0], initial[1], cleared_mask=initial[2]):
        return False, None
    while queue:
        state = queue.popleft()
        if state[2] == all_empty_mask:
            path = []
            cur = state
            while parent[cur] is not None:        
                path.append(action[cur])
                cur = parent[cur]
            path.reverse()
            return True, path
        guard = state[0]; face = state[1]
        nxt = [
            ((guard[0], guard[1] + 1), face, state[2], 'up'),
            ((guard[0], guard[1] - 1), face, state[2], 'down'),
            ((guard[0] - 1, guard[1]), face, state[2], 'left'),
            ((guard[0] + 1, guard[1]), face, state[2], 'right'),
            (guard, (face + delta) % 12, state[2], 'anticlock'),
            (guard, (face - delta) % 12, state[2], 'clock'),
        ]
        for g, f, m, act in nxt:
            if 0 <= g[0] < width and 0 <= g[1] < height and map1[g[0]][g[1]] == 0:
                if check(g, f, cleared_mask=m):
                    new_m = m | visible_mask_at(g, f)
                    ns = (g, f, new_m)
                    if ns not in seen:
                        seen.add(ns); queue.append(ns)
                        parent[ns] = state; action[ns] = act
    return False, None

def next_step_generator(state, action1, action2):
    guard1, face1, guard2, face2, cleared_mask = state
    def apply(g, f, act):
        if act == 'up':    return (g[0], g[1] + 1), f
        elif act == 'down':  return (g[0], g[1] - 1), f
        elif act == 'left':  return (g[0] - 1, g[1]), f
        elif act == 'right': return (g[0] + 1, g[1]), f
        elif act == 'anticlock': return g, (f + delta) % 12
        elif act == 'clock':     return g, (f - delta) % 12
        else:
            raise ValueError(f"未知动作: {act!r}")
    ng1, nf1 = apply(guard1, face1, action1)
    ng2, nf2 = apply(guard2, face2, action2)
    return (ng1, nf1, ng2, nf2, cleared_mask), action1, action2

def search2(initial):
    queue = collections.deque([initial])
    seen = {initial}
    parent = {initial: None}
    action = {initial: None}
    if not check(initial[0], initial[1], initial[2], initial[3], initial[4]):
        return False, None
    while queue:
        state = queue.popleft()
        if state[4] == all_empty_mask:
            path = []
            cur = state
            while parent[cur] is not None:        
                path.append(action[cur])
                cur = parent[cur]
            path.reverse()
            return True, path
        acts = ['up', 'down', 'left', 'right', 'anticlock', 'clock']
        for a1 in acts:
            for a2 in acts:
                ns, _, _ = next_step_generator(state, a1, a2)
                g1, f1, g2, f2, m = ns
                if (0 <= g1[0] < width and 0 <= g1[1] < height and
                    0 <= g2[0] < width and 0 <= g2[1] < height and
                    map1[g1[0]][g1[1]] == 0 and map1[g2[0]][g2[1]] == 0):
                    if check(g1, f1, g2, f2, m):
                        new_m = (m | visible_mask_at(g1, f1)) | visible_mask_at(g2, f2)
                        ns2 = (g1, f1, g2, f2, new_m)
                        if ns2 not in seen:
                            seen.add(ns2); queue.append(ns2)
                            parent[ns2] = state; action[ns2] = (a1, a2)
    return False, None

# ==================== 重放 path 重建状态序列 ====================
def _apply_one(pos, face, act):
    if act is None:                            
        return pos, face
    if act == 'up':    return (pos[0], pos[1] + 1), face
    elif act == 'down':  return (pos[0], pos[1] - 1), face
    elif act == 'left':  return (pos[0] - 1, pos[1]), face
    elif act == 'right': return (pos[0] + 1, pos[1]), face
    elif act == 'anticlock': return pos, (face + delta) % 12
    elif act == 'clock':     return pos, (face - delta) % 12
    else:
        raise ValueError(f"_apply_one 收到未知动作: {act!r}")  
def replay_single(start, face0, path):
    states = []
    pos, face = start, face0
    cleared = visible_mask_at(pos, face)
    states.append((pos, face, cleared))
    for act in path:
        if act is None:                        
            continue
        pos, face = _apply_one(pos, face, act)
        cleared |= visible_mask_at(pos, face)
        states.append((pos, face, cleared))
    return states

def replay_double(start, face1_0, face2_0, path):
    states = []
    g1, f1, g2, f2 = start, face1_0, start, face2_0
    cleared = visible_mask_at(g1, f1) | visible_mask_at(g2, f2)
    states.append((g1, f1, g2, f2, cleared))
    for item in path:
        if item is None:                       
            continue
        a1, a2 = item
        g1, f1 = _apply_one(g1, f1, a1)
        g2, f2 = _apply_one(g2, f2, a2)
        cleared |= visible_mask_at(g1, f1) | visible_mask_at(g2, f2)
        states.append((g1, f1, g2, f2, cleared))
    return states

# ==================== 可视化 ====================
_ani_keepalive = None

def quick_anim(states, mode='single', interval=400, save=None):
    global _ani_keepalive
    assert states, "states 为空，检查 replay_* 的输入"
    print(f"开始动画，共 {len(states)} 帧，后端 = {matplotlib.get_backend()}")

    fig, ax = plt.subplots(figsize=(7, 7))
    base = np.array(map1).T  # [y][x]

    def update(i):
        ax.clear()
        ax.imshow(base, cmap='gray_r', origin='upper',
                  extent=(-0.5, width - 0.5, height - 0.5, -0.5))
        ax.set_xticks(range(width)); ax.set_yticks(range(height))
        ax.grid(color='lightgray', lw=0.4)
        ax.set_aspect('equal')

        st = states[i]
        if mode == 'single':
            g1, f1, cleared = st
            guards = [(g1, f1, 'red')]
        else:
            g1, f1, g2, f2, cleared = st
            guards = [(g1, f1, 'red'), (g2, f2, 'blue')]

        # 已清除格子
        for x in range(width):
            for y in range(height):
                if (cleared >> idx(x, y)) & 1 and map1[x][y] == 0:
                    ax.add_patch(mpatches.Rectangle((x - 0.5, y - 0.5), 1, 1,
                                                    facecolor='lime', alpha=0.3))
        # 守卫 + 当前视野格子
        for gpos, gface, c in guards:
            for x in range(width):
                for y in range(height):
                    if map1[x][y] == 0 and can_see((x, y), gpos, gface):
                        ax.add_patch(mpatches.Rectangle((x - 0.5, y - 0.5), 1, 1,
                                                        facecolor=c, alpha=0.12))
            ax.add_patch(mpatches.Circle(gpos, 0.3, color=c, zorder=5))
            th = gface * np.pi / 6
            ax.annotate('', xy=(gpos[0] + 0.45 * np.cos(th), gpos[1] + 0.45 * np.sin(th)),
                        xytext=gpos, arrowprops=dict(arrowstyle='-|>', color=c, lw=2))
        ax.set_title(f'step {i}/{len(states) - 1}')

    ani = FuncAnimation(fig, update, frames=len(states),
                        interval=interval, repeat=False)
    _ani_keepalive = ani
    if save:
        ani.save(save, writer='pillow', fps=max(1, 1000 // interval))
        print(f"动画已保存到 {save}")
    plt.show(block=True)
    return ani

# ==================== 主流程 ====================
input2()
start = input_start()
all_empty_mask = find_all_empty_mask()

memo1 = {}
for face in range(12):
    initial_mask = visible_mask_at(start, face)
    initial = (start, face, initial_mask)
    ok, path = search1(initial)
    if ok:
        memo1[face] = (path, len(path))         
        print(f"单人解：初始面向 {face*30}°，{len(path)} 步")

memo2 = {}
if not memo1:
    for face1 in range(12):
        for face2 in range(12):
            cleared = visible_mask_at(start, face1) | visible_mask_at(start, face2)
            initial = (start, face1, start, face2, cleared)
            ok, path = search2(initial)
            if ok:
                memo2[(face1, face2)] = (path, len(path))   
                print(f"双人解：初始面向 {face1*30}° / {face2*30}°，{len(path)} 步")

if memo1:
    best_face = min(memo1, key=lambda f: memo1[f][1])
    path, steps = memo1[best_face]
    print(f"\n=== 最优单人解：{steps} 步，初始面向 {best_face*30}° ===")
    print("路径：", path)
    states = replay_single(start, best_face, path)
    quick_anim(states, mode='single', interval=400, save='single.gif')
elif memo2:
    best = min(memo2, key=lambda k: memo2[k][1])
    path, steps = memo2[best]
    f1, f2 = best
    print(f"\n=== 最优双人解：{steps} 步，初始面向 {f1*30}° / {f2*30}° ===")
    print("路径：", path)
    states = replay_double(start, f1, f2, path)
    quick_anim(states, mode='double', interval=500, save='double.gif')
else:
    print("本地图需要至少三人才可安全搜索。没有非平凡的安全路径。")
