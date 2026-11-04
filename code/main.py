# ==================== main：串联并运行所有模块 ====================
# 模块结构：
#   constants       常数与共享状态
#   user_input      用户输入
#   simulation      视觉（遮挡/可见性）+ 模拟运行规则（安全性检查、动作系统）
#   BFS_search 等   搜索算法（统一提供 search_single / search_double 接口）
#   search_registry 搜索算法注册表，main 启动时从这里选算法
#   visualization   重放与动画
import time

import constants
import user_input
import search_registry
from simulation import visible_mask_at, find_all_empty_mask
from visualization import replay_single, replay_double, quick_anim

UPPER_INIT = 9999999  # 剪枝上界的初始值


def solve_single(algo, start):
    # 用指定算法做单人搜索：对 12 个初始面向都试一遍，
    # 用当前已知最优步数做剪枝上界，越搜越快
    # 返回 dict：ok 是否有解 / path 路径 / steps 步数 / face 最优初始面向 / ms 耗时
    t0 = time.perf_counter()
    solution = False
    final_path = None
    final_step = -1
    best_face = -1
    best = UPPER_INIT
    for face in range(12):
        initial = (start, face, visible_mask_at(start, face))
        result, path, step = algo.search_single(initial, best)
        if result:
            final_path, final_step, best_face = path, step, face
            best = step
            solution = True
    ms = (time.perf_counter() - t0) * 1000
    return {'ok': solution, 'path': final_path, 'steps': final_step,
            'face': best_face, 'ms': ms}


def solve_double(algo, start):
    # 用指定算法做双人搜索（单人无解时调用）
    # 返回 dict：ok / path / steps / faces 最优初始面向组合 / ms 耗时
    t0 = time.perf_counter()
    solution = False
    final_path = None
    final_step = -1
    best_faces = (-1, -1)
    best = UPPER_INIT
    for face1 in range(12):
        # face2 从 face1 开始：两个初始面向对称，省一半
        for face2 in range(face1, 12):
            cleared = visible_mask_at(start, face1) | visible_mask_at(start, face2)
            initial = (start, face1, start, face2, cleared)
            result, path, step = algo.search_double(initial, best)
            if result:
                final_path, final_step, best_faces = path, step, (face1, face2)
                best = step
                solution = True
    ms = (time.perf_counter() - t0) * 1000
    return {'ok': solution, 'path': final_path, 'steps': final_step,
            'faces': best_faces, 'ms': ms}


def facing_txt(face):
    # 把面向编号转成角度文本，如 9 -> '270°'
    return f'{face * 30 % 360:.0f}°'


def export_solution(filename, algo_name, num_guards, steps, facing, path):
    # 把最优解导出为文本文件到 output/
    lines = [
        f'算法: {algo_name}',
        f'最少人数: {num_guards}',
        f'守卫初始面向: {facing}',
        f'最少步数: {steps}',
        f'最优路径: {path}',
    ]
    save_path = constants.output_path(filename)
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'最优路径已导出到 {save_path}')


def print_solution(num_guards, steps, facing):
    # 求解结果：最少人数、最少步数、守卫面向
    print('\n========== 求解结果 ==========')
    print(f'最少人数 : {num_guards}')
    print(f'最少步数 : {steps}')
    print(f'守卫面向 : {facing}')


def print_time_table(rows):
    # 耗时统计表：rows 是 (阶段, 耗时ms, 步数) 列表
    print('\n耗时统计：')
    print(f'{"阶段":<10}{"耗时(ms)":<12}{"步数":<8}')
    total = 0.0
    for name, ms, steps in rows:
        print(f'{name:<10}{ms:<12.1f}{steps}')
        total += ms
    print(f'{"总计":<10}{total:<12.1f}')


def choose_algorithm():
    # 启动时选择搜索算法，直接回车用默认（第一个注册的）
    # 返回 (算法模块, 算法名)
    all_names = search_registry.names()
    prompt = f'请选择算法（直接回车默认 {all_names[0]}）：'
    print('可用搜索算法：', '、'.join(all_names))
    name = input(prompt).strip() or all_names[0]
    while name not in all_names:
        print('没有注册这个算法，请重新输入')
        name = input(prompt).strip() or all_names[0]
    return search_registry.get(name), name


def main():
    # ---------- 输入 ----------
    start = user_input.choose_map()   # 地图 + 起点（预设/文件/随机/手动）
    user_input.read_delta()           # 转头角度
    find_all_empty_mask()

    # ---------- 选择搜索算法 ----------
    algo, algo_name = choose_algorithm()
    print(f'已选择算法：{algo_name}')

    # ---------- 单人搜索 ----------
    time_rows = []
    res1 = solve_single(algo, start)
    time_rows.append(('单人搜索', res1['ms'], res1['steps'] if res1['ok'] else '无解'))
    if res1['ok']:
        facing = facing_txt(res1['face'])
        print_solution(1, res1['steps'], facing)
        print_time_table(time_rows)
        export_solution('solution.txt', algo_name, 1, res1['steps'], facing, res1['path'])
        states = replay_single(start, res1['face'], res1['path'])
        quick_anim(states, mode='single', interval=400, save=constants.output_path('single.gif'))
        return

    # ---------- 双人搜索 ----------
    res2 = solve_double(algo, start)
    time_rows.append(('双人搜索', res2['ms'], res2['steps'] if res2['ok'] else '无解'))
    if res2['ok']:
        facing = f'{facing_txt(res2["faces"][0])} / {facing_txt(res2["faces"][1])}'
        print_solution(2, res2['steps'], facing)
        print_time_table(time_rows)
        export_solution('solution.txt', algo_name, 2, res2['steps'], facing, res2['path'])
        states = replay_double(start, res2['faces'][0], res2['faces'][1], res2['path'])
        quick_anim(states, mode='double', interval=500, save=constants.output_path('double.gif'))
    else:
        print_solution('3+', '-', '-')
        print_time_table(time_rows)
        print('本地图需要至少三人才可安全搜索。没有非平凡的安全路径。')


if __name__ == '__main__':
    main()
