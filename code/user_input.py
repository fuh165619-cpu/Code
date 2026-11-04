# ==================== 用户输入模块 ====================
# 地图来源统一从 choose_map() 进入（预设 / 文件 / 随机 / 手动）
# 地图大小一律自动从内容读取，不需要手动输入长宽
import constants
import map_loader


def read_delta():
    # 角度用整数标记，delta 只取 1 和 2，分别对应 30 度和 60 度
    temp = int(input('请输入每次转头的角度delta，只能是30或60：'))
    while temp not in [30, 60]:
        print('错误！当前版本只支持取delta为30或60！')
        temp = int(input('请输入每次转头的角度delta，只能是30或60：'))
    constants.delta = temp / 30


def manual_map():
    # 手动逐行输入地图：第一行决定宽度，输入空行结束，行数即高度
    # 与文件格式相同，直接复用 parse_map_text 做校验（含非法字符检查）
    print('逐行输入地图（. 或 0 = 空地，# 或 1 = 墙），第一行决定宽度，直接回车结束：')
    rows = []
    while True:
        line = input(f'第 {len(rows) + 1} 行: ').strip()
        if not line:
            if rows:
                break
            print('至少要输入一行')
            continue
        if rows and len(line) != len(rows[0]):
            print(f'与第 1 行长度（{len(rows[0])} 格）不一致，请重输')
            continue
        rows.append(line)
    map1, start = map_loader.parse_map_text('\n'.join(rows))
    return map_loader.apply_map(map1, start)


def input_start():
    # 输入起始格子坐标，必须在地图内且不为墙格
    start_x, start_y = (int(i.strip()) for i in input("请输入起始格子的坐标（x, y）: ").split(","))
    while not (constants.in_bounds(start_x, start_y) and constants.is_open(start_x, start_y)):
        print('错误！起始格子必须在地图内且不为墙格！')
        start_x, start_y = (int(i.strip()) for i in input("请输入起始格子的坐标（x, y）: ").split(","))
    return start_x, start_y


def choose_map():
    # 选择地图来源并加载，返回守卫起点坐标
    # 来源：1 预设示例（maps/ 文件夹） / 2 从文件读取 / 3 随机生成 / 4 手动输入
    print('地图来源：1. 预设示例（maps/ 文件夹）  2. 从文件读取  3. 随机生成  4. 手动输入')
    choice = input('请选择（直接回车默认 1）：').strip() or '1'
    while choice not in ('1', '2', '3', '4'):
        print('无效选择，请输入 1 到 4')
        choice = input('请选择（直接回车默认 1）：').strip() or '1'

    start = None
    if choice == '1':
        presets = map_loader.list_presets()
        if not presets:
            print('maps/ 文件夹里没有预设地图，改用手动输入')
            start = manual_map()
        else:
            print('可用预设地图：', '、'.join(presets))
            name = input('预设地图名（直接回车默认第一个）：').strip() or presets[0]
            while name not in presets:
                print('没有这个预设，请重新输入')
                name = input('预设地图名（直接回车默认第一个）：').strip() or presets[0]
            start = map_loader.load_preset(name)

    elif choice == '2':
        path = input('请输入地图文件路径：').strip()
        while True:
            try:
                start = map_loader.load_file(path)
                break
            except FileNotFoundError:
                print('文件不存在，请重新输入')
                path = input('请输入地图文件路径：').strip()
            except ValueError as e:
                print(f'地图格式有误：{e}')
                path = input('请输入地图文件路径：').strip()

    elif choice == '3':
        width = int(input('width: '))
        height = int(input('height: '))
        if width <= 0 or height <= 0:
            print("地图大小必须大于0")
            exit(1)
        density = float(input('请输入墙密度（0 到 1 之间的小数，直接回车默认 0.2）：').strip() or '0.2')
        while not 0 <= density < 1:
            print('墙密度必须是 0 到 1 之间的小数')
            density = float(input('请输入墙密度（直接回车默认 0.2）：').strip() or '0.2')
        start = map_loader.generate_random(width, height, density)

    else:
        start = manual_map()

    # 地图里没标 S 的话，手动补问起点
    if start is None:
        start = input_start()
    print(f'地图已加载：{constants.width} x {constants.height}，起点 {start}')
    return start
