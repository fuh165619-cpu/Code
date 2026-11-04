# ==================== 地图加载 ====================
# 三种地图来源，都最终写入 constants 的共享状态：
#   1. 文件读取 load_file：文本文件，. / 0 = 空地，# / 1 = 墙，S = 守卫起点
#   2. 预设示例 load_preset：maps/ 文件夹里的 .txt
#   3. 随机生成 generate_random：按墙密度撒墙，只保留"所有空地与起点连通"的地图
# 本模块只做解析和生成，不做交互；交互入口在 user_input.choose_map()
# 地图大小一律从内容自动读取（行数 = 高度，行内字符数 = 宽度），不需要手动指定
import os
import random
from collections import deque

import constants
import simulation

PRESET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'maps')


def parse_map_text(text):
    # 解析地图文本，返回 (map1, start)
    # start 可能是 None（没写 S，需要用户再手动输入起点）
    rows = []
    start = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue  # 跳过空行和注释
        rows.append(line)
    if not rows:
        raise ValueError('地图文件里没有任何地图行')
    height = len(rows)
    width = len(rows[0])
    map1 = [[0] * height for _ in range(width)]
    for y, row in enumerate(rows):
        if len(row) != width:
            raise ValueError(f'第 {y + 1} 行长度 {len(row)} 与第 1 行长度 {width} 不一致')
        for x, ch in enumerate(row):
            if ch in '.0':
                pass
            elif ch in '#1':
                map1[x][y] = 1
            elif ch in 'Ss':
                if start is not None:
                    raise ValueError(f'地图里出现了多个起点 S（第 {y + 1} 行第 {x + 1} 个字符）')
                start = (x, y)
            else:
                raise ValueError(f'第 {y + 1} 行第 {x + 1} 个字符是非法字符 {ch!r}，'
                                 f'只支持 . 0（空地）和 # 1（墙）和 S（起点）')
    return map1, start


def apply_map(map1, start=None):
    # 把地图写入 constants 共享状态，大小从内容自动推断，返回 start
    # 换地图必须清空 simulation 的记忆化缓存（缓存的 key 不含地图信息）
    constants.width = len(map1)
    constants.height = len(map1[0]) if map1 else 0
    constants.map1 = map1
    simulation.clear_caches()
    return start


def load_file(path):
    # 从文本文件加载地图，返回起点（可能为 None）
    with open(path, encoding='utf-8') as f:
        map1, start = parse_map_text(f.read())
    return apply_map(map1, start)


def load_preset(name):
    # 加载 maps/ 文件夹里的预设地图（name 不带 .txt 后缀）
    return load_file(os.path.join(PRESET_DIR, name + '.txt'))


def list_presets():
    # 列出所有预设地图名（不带后缀）
    if not os.path.isdir(PRESET_DIR):
        return []
    return sorted(f[:-4] for f in os.listdir(PRESET_DIR)
                  if f.endswith('.txt'))


def _connected(map1, width, height, start):
    # 判断所有空地是否都与 start 连通（四方向）
    total_open = sum(row.count(0) for row in map1)
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((0, 1), (0, -1), (-1, 0), (1, 0)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < width and 0 <= ny < height
                    and map1[nx][ny] == 0 and (nx, ny) not in seen):
                seen.add((nx, ny))
                queue.append((nx, ny))
    return len(seen) == total_open


def generate_random(width, height, density):
    # 随机生成地图：按 density 概率撒墙，反复重试直到
    # "存在空地、起点随机选在空地、所有空地与起点连通"
    # 返回起点
    for attempt in range(50):
        map1 = [[1 if random.random() < density else 0 for _ in range(height)]
                for _ in range(width)]
        opens = [(x, y) for x in range(width) for y in range(height) if map1[x][y] == 0]
        if not opens:
            continue
        start = random.choice(opens)
        if _connected(map1, width, height, start):
            apply_map(map1, start)
            return start
    raise RuntimeError('尝试 50 次都没能生成连通地图，请降低墙密度后重试')
