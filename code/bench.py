# ==================== 大尺寸地图基准测试 ====================
# 跑 maps/bench/ 下的 10x10 / 20x20 测试地图，对比 Fast 与 BFS。
#
# 每个 (地图, 算法) 都放在独立子进程里跑：超过时间上限就结束进程并记为"超时"，
# 这样一张 20x20 地图卡住不会拖住后面的用例，也不会把主进程一起卡死。
#
# 用法：
#   python bench.py                 # 全部地图，每个用例最多 600 秒
#   python bench.py --timeout 120   # 自定义单次上限（秒）
#   python bench.py --maps t10      # 只跑名字以 t10 开头的地图
#
# 结果同时写入 output/bench_results.txt
import argparse
import glob
import json
import os
import subprocess
import sys
import time
import uuid

import constants
import map_loader
import search_registry
from simulation import (find_all_empty_mask, clear_caches, visible_mask_at,
                        check, apply_one)
from main import solve_single, solve_double

BENCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'maps', 'bench')
ALGOS = ('Fast', 'BFS')
DELTA = 1                      # 30 度


# ---------- 路径校验：确认搜索返回的路径真的安全且清空全图 ----------

def verify_single(start, face, path, steps):
    pos, f = start, int(face)
    cleared = visible_mask_at(pos, f)
    if len(path) != steps or not check(pos, f, cleared_mask=cleared):
        return False
    for act in path:
        pos, f = apply_one(pos, f, act)
        if not check(pos, f, cleared_mask=cleared):
            return False
        cleared |= visible_mask_at(pos, f)
    return cleared == constants.all_empty_mask


def verify_double(start, faces, path, steps):
    g1, f1 = start, int(faces[0])
    g2, f2 = start, int(faces[1])
    cleared = visible_mask_at(g1, f1) | visible_mask_at(g2, f2)
    if len(path) != steps or not check(g1, f1, g2, f2, cleared):
        return False
    for item in path:
        a1, a2 = item
        g1, f1 = apply_one(g1, f1, a1)
        g2, f2 = apply_one(g2, f2, a2)
        if not check(g1, f1, g2, f2, cleared):
            return False
        cleared |= visible_mask_at(g1, f1) | visible_mask_at(g2, f2)
    return cleared == constants.all_empty_mask


# ---------- 子进程 worker ----------

def run_worker(algo_name, map_path, out_path):
    result = {'ok': False, 'guards': None, 'steps': None, 'ms': None,
              'valid': None, 'error': None}
    try:
        start = map_loader.load_file(map_path)
        constants.delta = DELTA
        find_all_empty_mask()
        clear_caches()
        algo = search_registry.get(algo_name)
        single = solve_single(algo, start)
        if single['ok']:
            result.update(ok=True, guards=1, steps=single['steps'],
                          ms=single['ms'],
                          valid=verify_single(start, single['face'],
                                              single['path'], single['steps']))
        else:
            double = solve_double(algo, start)
            if double['ok']:
                result.update(ok=True, guards=2, steps=double['steps'],
                              ms=double['ms'],
                              valid=verify_double(start, double['faces'],
                                                  double['path'], double['steps']))
            else:
                # 双人也无解：没有路径可校验，valid 留空
                result.update(ok=False, steps=None, ms=double['ms'], valid=None)
    except Exception as exc:                       # noqa: BLE001 - 只用于测试脚本
        result['error'] = f'{type(exc).__name__}: {exc}'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)


# ---------- 主进程：起子进程 + 超时控制 ----------

def run_case(map_path, algo, timeout):
    name = os.path.splitext(os.path.basename(map_path))[0]
    tmp = constants.output_path(f'_bench_{uuid.uuid4().hex}.json')
    cmd = [sys.executable, os.path.abspath(__file__), '--worker',
           algo, os.path.abspath(map_path), tmp]
    started = time.perf_counter()
    status = '完成'
    try:
        subprocess.run(cmd, timeout=timeout, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)
    except subprocess.TimeoutExpired:
        status = '超时'
    wall = time.perf_counter() - started

    data = None
    if os.path.exists(tmp):
        try:
            with open(tmp, encoding='utf-8') as f:
                data = json.load(f)
        finally:
            os.remove(tmp)

    row = {'map': name, 'algo': algo, 'wall': wall, 'status': status,
           'guards': None, 'steps': None, 'ms': None, 'valid': None}
    if status == '超时':
        return row
    if data is None:
        row['status'] = '进程异常退出'
        return row
    if data['error']:
        row['status'] = '出错'
        row['error'] = data['error']
        return row
    row.update(guards=data['guards'], steps=data['steps'], ms=data['ms'],
               valid=data['valid'])
    if not data['ok']:
        row['status'] = '无解'
    return row


def print_table(rows, timeout):
    print()
    print(f'{"地图":<16}{"算法":<7}{"人数":<6}{"步数":<6}'
          f'{"搜索耗时":<12}{"进程耗时":<12}{"状态":<10}校验')
    for r in rows:
        guards = '-' if r['guards'] is None else r['guards']
        steps = '-' if r['steps'] is None else r['steps']
        ms = '-' if r['ms'] is None else f'{r["ms"] / 1000:.3f} s'
        wall = f'{r["wall"]:.3f} s'
        status = r['status']
        if status == '超时':
            wall = f'>{timeout:.0f} s'
        valid = '-' if r['valid'] is None else ('OK' if r['valid'] else 'FAIL')
        print(f'{r["map"]:<16}{r["algo"]:<7}{str(guards):<6}{str(steps):<6}'
              f'{ms:<12}{wall:<12}{status:<10}{valid}')
        if r.get('error'):
            print(f'{"":<16}错误：{r["error"]}')


def main():
    ap = argparse.ArgumentParser(description='10x10 / 20x20 基准测试')
    ap.add_argument('--timeout', type=float, default=600.0,
                    help='单个用例的时间上限（秒），默认 600')
    ap.add_argument('--maps', default=None,
                    help='只跑文件名以该前缀开头的地图，例如 t10')
    ap.add_argument('--worker', nargs=3, metavar=('ALGO', 'MAP', 'OUT'),
                    help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.worker:
        run_worker(*args.worker)
        return

    maps = sorted(glob.glob(os.path.join(BENCH_DIR, '*.txt')))
    if args.maps:
        maps = [m for m in maps if os.path.basename(m).startswith(args.maps)]
    if not maps:
        print(f'没有找到测试地图：{BENCH_DIR}')
        return

    print(f'共 {len(maps)} 张地图 × {len(ALGOS)} 个算法，'
          f'单个用例上限 {args.timeout:.0f} 秒（超时即结束该进程）')
    rows = []
    for index, path in enumerate(maps, 1):
        name = os.path.splitext(os.path.basename(path))[0]
        for algo in ALGOS:
            print(f'[{index}/{len(maps)}] {name} / {algo} ...', flush=True)
            row = run_case(path, algo, args.timeout)
            rows.append(row)
            extra = '' if row['status'] != '超时' else f'（超过 {args.timeout:.0f} 秒）'
            print(f'    -> {row["status"]}{extra}', flush=True)

    print_table(rows, args.timeout)
    report_path = constants.output_path('bench_results.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f'10x10 / 20x20 基准测试（delta=30°，单用例上限 {args.timeout:.0f}s）\n\n')
        for r in rows:
            f.write(f'{r["map"]}\t{r["algo"]}\t'
                    f'guards={r["guards"]}\tsteps={r["steps"]}\t'
                    f'ms={r["ms"]}\twall={r["wall"]:.3f}s\t'
                    f'status={r["status"]}\tvalid={r["valid"]}\n')
    print(f'\n结果已保存到 {report_path}')


if __name__ == '__main__':
    main()
