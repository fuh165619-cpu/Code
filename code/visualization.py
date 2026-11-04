# ==================== 重放与可视化 ====================
# replay_*：按搜索得到的 path 重放，重建每一步的完整状态序列
# quick_anim：用 matplotlib 播放动画，可另存为 gif
import numpy as np
import matplotlib
matplotlib.use('TkAgg')          # 强制有界面后端；若报错改 'QtAgg'
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.patches as mpatches

import constants
from simulation import visible_mask_at, can_see, apply_one

_ani_keepalive = None


def replay_single(start, face0, path):
    states = []
    pos, face = start, face0
    cleared = visible_mask_at(pos, face)
    states.append((pos, face, cleared))
    for act in path:
        if act is None:
            continue
        pos, face = apply_one(pos, face, act)
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
        g1, f1 = apply_one(g1, f1, a1)
        g2, f2 = apply_one(g2, f2, a2)
        cleared |= visible_mask_at(g1, f1) | visible_mask_at(g2, f2)
        states.append((g1, f1, g2, f2, cleared))
    return states


def draw_guard(ax, gpos, gface, color):
    # 画一个守卫：渐变"手电筒"光锥 + 两条金色边界横线 + 本体圆点
    # 所有角度都和 simulation.can_see 用同一个坐标系（地图坐标，y 向下），
    # 视野锥是相对朝向 0 ~ 120 度，保证画面上的方向和实际判定完全一致
    x, y = gpos
    th1 = gface * 30          # 视野锥起始边
    th2 = th1 + 120           # 视野锥终止边
    # 光锥最大长度 = 地图长宽中较大的一边
    R = max(constants.width, constants.height)

    # 渐变光锥：8 层同心环形扇段，越靠近守卫越亮，模拟手电筒光衰减
    layers = 8
    for i in range(layers):
        r = R * (i + 1) / layers
        ax.add_patch(mpatches.Wedge((x, y), r, th1, th2, width=R / layers,
                                    facecolor=color,
                                    alpha=0.20 * (1 - i / layers) + 0.02,
                                    edgecolor='none', zorder=1))

    # 两条边界横线：长 1 格，金色醒目，标出视野范围两侧
    for th in (th1, th2):
        dx, dy = np.cos(np.radians(th)), np.sin(np.radians(th))
        ax.plot([x, x + dx], [y, y + dy], color='#FFD700', lw=3,
                zorder=6, solid_capstyle='round', clip_on=True)

    # 守卫本体
    ax.add_patch(mpatches.Circle((x, y), 0.3, color=color, zorder=7))


def quick_anim(states, mode='single', interval=400, save=None):
    # 播放动画；save 传文件名可同时保存为 gif
    global _ani_keepalive
    assert states, "states 为空，检查 replay_* 的输入"
    print(f"开始动画，共 {len(states)} 帧，后端 = {matplotlib.get_backend()}")

    fig, ax = plt.subplots(figsize=(7, 7))
    base = np.array(constants.map1).T  # 转置成 [y][x] 方便 imshow
    width, height = constants.width, constants.height

    def update(i):
        ax.clear()
        ax.imshow(base, cmap='gray_r', origin='upper',
                  extent=(-0.5, width - 0.5, height - 0.5, -0.5))
        # 固定显示范围为地图本身并关掉自动缩放：
        # 否则扇形等 patch 会撑大坐标轴，导致每帧地图忽大忽小、位置漂移
        ax.set_xlim(-0.5, width - 0.5)
        ax.set_ylim(height - 0.5, -0.5)   # y 反向，和 extent 保持一致
        ax.set_autoscale_on(False)
        # 网格线画在格子边界上（边界位于 ±0.5 的半整数位置），而不是穿过格子中心
        ax.set_xticks(np.arange(-0.5, width, 1))
        ax.set_yticks(np.arange(-0.5, height, 1))
        ax.grid(color='lightgray', lw=0.4)
        ax.set_aspect('equal')
        ax.tick_params(labelbottom=False, labelleft=False, length=0)

        st = states[i]
        if mode == 'single':
            g1, f1, cleared = st
            guards = [(g1, f1, 'red')]
        else:
            g1, f1, g2, f2, cleared = st
            guards = [(g1, f1, 'red'), (g2, f2, 'blue')]

        # 已清除的格子涂绿
        for x in range(width):
            for y in range(height):
                if (cleared >> constants.idx(x, y)) & 1 and constants.is_open(x, y):
                    ax.add_patch(mpatches.Rectangle((x - 0.5, y - 0.5), 1, 1,
                                                    facecolor='lime', alpha=0.3,
                                                    zorder=2))
        # 当前实际可见的格子（考虑墙遮挡）+ 守卫
        for gpos, gface, c in guards:
            for x in range(width):
                for y in range(height):
                    if constants.is_open(x, y) and can_see((x, y), gpos, gface):
                        ax.add_patch(mpatches.Rectangle((x - 0.5, y - 0.5), 1, 1,
                                                        facecolor=c, alpha=0.12,
                                                        zorder=3))
            draw_guard(ax, gpos, gface, c)
        facing_txt = ' / '.join(f'{g[1] * 30 % 360:.0f}°' for g in guards)
        ax.set_title(f'step {i}/{len(states) - 1}   facing {facing_txt}')

    ani = FuncAnimation(fig, update, frames=len(states),
                        interval=interval, repeat=False)
    _ani_keepalive = ani
    if save:
        ani.save(save, writer='pillow', fps=max(1, 1000 // interval))
        print(f"动画已保存到 {save}")
    plt.show(block=True)
    return ani
