# ==================== test：多种搜索算法对比 ====================
# 像 main 一样输入地图，然后对所有注册的搜索算法跑同样的搜索任务，
# 每个算法开始前清空所有记忆化缓存，保证计时公平。
# 输出对比表格（人数 / 步数 / 面向 / 耗时），有解的算法把路径导出到 output/，
# 并生成耗时 / 步数对比条形图（保存为 output/comparison.png）。
import matplotlib
matplotlib.use('TkAgg')          # 强制有界面后端；若报错改 'QtAgg'
import matplotlib.pyplot as plt

import constants
import user_input
import search_registry
from simulation import visible_mask_at, find_all_empty_mask, clear_caches
from main import solve_single, solve_double, export_solution, facing_txt


def benchmark_one(name, algo, start, test_double=False):
    # 测一个算法，返回结果行（dict）
    clear_caches()
    row = {'algo': name}
    print(f'\n--- 正在测试 {name}（单人搜索，12 个初始面向）---')
    res1 = solve_single(algo, start)
    row.update(single_ok=res1['ok'], single_ms=res1['ms'],
               single_steps=res1['steps'] if res1['ok'] else None)
    print(f"{name} 单人：{res1['steps'] if res1['ok'] else '无解'}，耗时 {res1['ms']:.1f} ms")

    # 双人搜索非常慢，只有明确要求（且单人无解）时才测
    if test_double and not res1['ok']:
        print(f'--- 正在测试 {name}（双人搜索，可能很慢）---')
        res2 = solve_double(algo, start)
        row.update(double_ok=res2['ok'], double_ms=res2['ms'],
                   double_steps=res2['steps'] if res2['ok'] else None,
                   double_faces=res2['faces'] if res2['ok'] else None,
                   double_path=res2['path'] if res2['ok'] else None)
        print(f"{name} 双人：{res2['steps'] if res2['ok'] else '无解'}，耗时 {res2['ms']:.1f} ms")

    # 有解就导出路径：单人有解记 1 人；单人无解双人有解记 2 人
    if res1['ok']:
        facing = facing_txt(res1['face'])
        row.update(guards=1, steps=res1['steps'], facing=facing)
        export_solution(f'solution_{name}.txt', name, 1, res1['steps'], facing, res1['path'])
    elif row.get('double_ok'):
        f1, f2 = row['double_faces']
        facing = f'{facing_txt(f1)} / {facing_txt(f2)}'
        row.update(guards=2, steps=row['double_steps'], facing=facing)
        export_solution(f'solution_{name}.txt', name, 2, row['double_steps'], facing,
                        row['double_path'])
    return row


def print_table(rows):
    # 打印对比表格：最少人数、步数、守卫面向、单/双人耗时
    def fmt(v, suffix=''):
        # None 显示 '-'，其余正常显示
        return '-' if v is None else f'{v}{suffix}'

    print('\n==================== 对比结果 ====================')
    print(f'{"算法":<8}{"最少人数":<8}{"步数":<6}{"面向":<16}'
          f'{"单人耗时(ms)":<12}{"双人耗时(ms)":<12}')
    for r in rows:
        guards = r.get('guards', '-')
        facing = r.get('facing', '-')
        facing_str = facing if len(facing) <= 14 else facing[:13] + '…'
        print(f"{r['algo']:<8}{guards:<8}{fmt(r.get('steps')):<6}{facing_str:<16}"
              f"{r['single_ms']:<12.1f}{fmt(r.get('double_ms'), ''):<12}")
        if len(facing) > 14:
            print(f'{"":<22}{facing}')


def plot_comparison(rows, has_double):
    # 画对比条形图：单人人手一份（耗时、步数）；若测了双人再补两幅
    names = [r['algo'] for r in rows]
    ncols = 4 if has_double else 2
    fig, axes = plt.subplots(1, ncols, figsize=(6 * ncols, 5))

    def bar(ax, values, title, unit, labels=None, colors=None):
        bars = ax.bar(names, values, color=colors)
        ax.set_title(title)
        ax.set_ylabel(unit)
        ax.grid(axis='y', alpha=0.4)
        for i, (bar, v) in enumerate(zip(bars, values)):
            text = labels[i] if labels else f'{v:.3f}'
            ax.annotate(text, xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        ha='center', va='bottom')

    single_times = [r['single_ms'] / 1000 for r in rows]
    single_steps = [r['single_steps'] if r['single_ok'] else 0 for r in rows]
    single_labels = [str(r['single_steps']) if r['single_ok'] else 'no solution' for r in rows]
    single_colors = ['#4C9BE8' if r['single_ok'] else '#D9534F' for r in rows]

    bar(axes[0], single_times, 'Single-guard total time (12 initial facings)', 'seconds')
    bar(axes[1], single_steps, 'Single-guard optimal steps (lower is better)', 'steps',
        labels=single_labels, colors=single_colors)

    if has_double:
        double_times = [(r.get('double_ms') or 0) / 1000 for r in rows]
        double_steps = [r['double_steps'] if r.get('double_ok') else 0 for r in rows]
        double_labels = [str(r['double_steps']) if r.get('double_ok') else
                         ('no solution' if r.get('double_ok') is not None else 'not tested') for r in rows]
        double_colors = ['#5CB85C' if r.get('double_ok') else
                         ('#D9534F' if r.get('double_ok') is not None else '#B0B0B0') for r in rows]
        bar(axes[2], double_times, 'Double-guard total time', 'seconds')
        bar(axes[3], double_steps, 'Double-guard optimal steps (lower is better)', 'steps',
            labels=double_labels, colors=double_colors)

    fig.suptitle('Search Algorithm Comparison')
    fig.tight_layout()
    save_path = constants.output_path('comparison.png')
    fig.savefig(save_path, dpi=150)
    print(f'\n对比图已保存为 {save_path}')
    plt.show(block=True)


def main():
    # ---------- 输入（和 main 一样） ----------
    start = user_input.choose_map()
    user_input.read_delta()
    find_all_empty_mask()

    # ---------- 是否测双人 ----------
    print('\n注意：双人搜索非常慢。单人无解的地图才会涉及双人搜索。')
    ans = input('单人无解时是否继续测双人搜索？（y/n，直接回车默认 n）：').strip().lower()
    test_double = (ans == 'y')

    # ---------- 逐个算法计时 ----------
    all_names = search_registry.names()
    print(f'\n共注册 {len(all_names)} 个算法：{"、".join(all_names)}')
    rows = [benchmark_one(name, search_registry.get(name), start, test_double)
            for name in all_names]

    # ---------- 输出对比 ----------
    print_table(rows)
    has_double = any(r.get('double_ms') is not None for r in rows)
    plot_comparison(rows, has_double)


if __name__ == '__main__':
    main()
