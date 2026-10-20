import math
import collections
#输入模块
#这里用列表套列表来实现矩阵效果
#先把行数和列数读进来
width = int(input("width: "))
height = int(input("height: "))
#然后创建一个空地图，左上角是（0， 0）
#x轴水平向右，y轴水平向下
if width <= 0 or height <= 0:
    print("地图大小必须大于0")
    exit(1)
map1 = [[0 for _ in range(height)] for _ in range(width)]
#eps很多地方都要用，我直接拿出来当全局变量了
eps = 0.0001
#因为后面很多地方都要用delta，不高兴一个个函数传了，直接当全局变量用
#因为这里角度都是用整数来标记的，所以delta的取值也只取1和2
#分别对应30度和60度
temp = int(input('请输入每次转头的角度delta，只能是30或60：'))
while not temp in [30, 60]:
    print('错误！当前版本只支持取delta为30或60！')
    temp = int(input('请输入每次转头的角度delta，只能是30或60：'))
delta = temp / 30
#为了使用位掩码我在这里定义一个函数idx，输入x, y得到位掩码
def idx(x, y):
    return x * height + y
#这里可以有两种输入格式
#一种是输入所有有墙的格子的坐标
#一种是一行一行从左到右把每个格子都输进来
#这里我就定义两个函数，按需取用
def input1():
    while True:
        try:
            x, y = (int(i.strip()) for i in input("请输入墙的坐标（x, y），输入（-1， -1）结束输入").split(","))
            #规定输入-1，-1表示输入结束
            if (x, y) == (-1, -1):
                break
            if 0 <= x < width and 0 <= y < height:
                map1[x][y] = 1
            else:
                print("坐标超出范围，请重新输入")
        except ValueError:
            print("输入格式错误，请输入两个整数，用逗号分隔")
def input2():
    print('按行输入，两个格子间不分隔，回车输入下一列')
    for i in range(height):
        temp = [int(j) for j in input()]
        if len(temp) != width:
            print("输入的格子数与列数不符，请重新输入")
        else:
            for j in range(width):
                map1[j][i] = temp[j]
#然后输入起始格子和起始面向
def input_start():
    start_x, start_y = (int(i.strip()) for i in input("请输入起始格子的坐标（x, y）: ").split(","))
    while not (0 <= start_x < width and 0 <= start_y < height and map1[start_x][start_y] == 0):
        print('错误！起始格子必须在地图内且不为墙格！')
        start_x, start_y = (int(i.strip()) for i in input("请输入起始格子的坐标（x, y）: ").split(","))
    return start_x, start_y
#输入部分结束，下面先写个check函数检查当前状态是否安全
#“被墙挡住”的判定比较复杂，这里写一个block函数
# def block(point1, point2):
#     #思路是这样：如果两个格子之间被墙挡住，那么这面墙要么横着要么竖着，要么都是
#     #所以先检查是否被横着的墙挡住，再检查是否被竖着的墙挡住
#     x1, y1 = point1
#     x2, y2 = point2
#     left = min(x1, x2)
#     right = max(x1, x2)
#     low = min(y1, y2)
#     high = max(y1, y2)
#     #先测一下有效性防止出现除0问题
#     #这里就把两个点重合定义为没有被挡住了，其实定义成什么都一样，后面调用的时候应该会避免这种情况
#     #顺便把紧邻着的情况也处理掉，不然后面range可能会下标越界
#     if -1 <= x1 - x2 <= 1 and -1 <= y1 - y2 <= 1:
#         return False
#     k = (y2 - y1) / (x2 - x1 + eps)
#     #先检查横着的墙
#     if x1 != x2:
#         for dx in range(1, right - left):
#             #生成left + dx的对应y值，然后检查：如果floor(y)和floor(y) + 1都是墙，那么就可以确定被挡住
#             y = k * (left + dx - x1) + y1
#             if y - math.floor(y) < 0.1:
#                 if map1[left + dx][int(y)] == 1:
#                     return True
#             elif map1[left + dx][math.floor(y)] == 1 and map1[left + dx][math.floor(y) + 1] == 1:
#                 return True
#             else:
#                 pass
#     #然后是竖着的，照抄一遍即可
#     if y1 != y2:
#         m = 1 / k + eps
#         for dy in range(1, high - low):
#             x = m * (low + dy - y1) + x1
#             if x - math.floor(x) < 0.1:
#                 if map1[int(x)][low + dy] == 1:
#                     return True
#             elif map1[math.floor(x)][low + dy] == 1 and map1[math.floor(x) + 1][low + dy] == 1:
#                 return True
#     return False
#原block函数怎么修都修不好，重写一个
#block的步长还蛮小的，计算次数比较多，这里也做个记忆化优化一下
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
#因为后面搜索的时候需要经常用到“已经看到的格子”，所以这里专门定义一个can_see函数
#如果这个格子能被守卫看到就返回True，反之就返回False
#并且做一下记忆化，因为can_see会被多次调用
#为了记忆化这里定义个全局变量，话说这里用全局变量会不会有点危险
#不过应该够用了
can_see_cache = {}
def can_see(position, guard, face):
    if (position, guard, face) in can_see_cache:
        return can_see_cache[(position, guard, face)]
    #这个if是为了兼容后面搜索中要用到的seen
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
#为了优化这里再定义一个visible_mask_at函数，带缓存
#ai建议用一个库里的什么东西，不过为了方便修我还是用全局变量了
visible_mask_at_cache = {}
def visible_mask_at(position, face):
    if (position, face) in visible_mask_at_cache:
        return visible_mask_at_cache[(position, face)]
    result = 0
    for i in range(width):
        for j in range(height):
            if can_see((i, j), position, face):
                result |= 1 << idx(i, j)
    visible_mask_at_cache[position, face] = result
    return result
#因为每次check都要遍历所有格子，虽然check依托的函数都已经记忆化
#这里还是给check做一个记忆化
check_cache = {}
def check(position1, face1, position2 = (-1, -1), face2 = 0, cleared_mask = 0):
    #这里角度取值用整数标记，face可以取0 - 11，对应关系是实际角度 = face * math.pi / 6
    if (position1, face1, position2, face2, cleared_mask) in check_cache:
        return check_cache[(position1, face1, position2, face2, cleared_mask)]
    for i in range(width):
        for j in range(height):
            if (cleared_mask >> idx(i, j)) & 1:
                continue
            if map1[i][j] == 1:
                continue
            if (i, j) == position1 or (i, j) == position2:
                continue
            #这里发现要处理“被墙挡住”的情况比较复杂，所以回过头去写一个block函数
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
            check_cache[(position1, face1, position2, face2, cleared_mask)] = False
            return False
    check_cache[(position1, face1, position2, face2, cleared_mask)] = True
    return True
#准备工作基本已经完成，接下来是主干部分
#这里决定用广搜
#单人搜索
#这里先生成一个全局变量all_empty表示所有空的格子，如果所有空的格子都看过了那么就结束
#这里也改用位掩码
#为了防止后面出现语法错误这里预先定义一个全局变量all_empty_mask
#不调用find_all_empty_mask的时候这个变量是空的
all_empty_mask = 0
def find_all_empty_mask():
    all_empty_mask = 0
    for i in range(width):
        for j in range(height):
            if map1[i][j] == 0:
                all_empty_mask |= 1 << idx(i, j)
    return all_empty_mask
#为了优化这里做一个剪枝，搜索的时候传一个上界进去
#如果步数超过上界就直接退出
def search1(initial, upper):
    #search1需要传一个叫做initial的形参进去
    #initial应该是一个tuple，包含三样东西：
    #守卫位置（用tuple标记），面向（从0取到11的一个整数），已清除集合(这里用位掩码表示)
    #这里用到一个ai教给我的类型，叫做collections.deque
    queue = collections.deque()
    queue.append(initial)
    seen = {initial}
    parent = {}
    action = {}
    parent[initial] = None
    action[initial] = None
    #这里单独加一个初始状态的检验
    if not check(initial[0], initial[1], cleared_mask = initial[2]):
        return False, None, -1
    depth = {initial: 0}
    while queue:
        state = queue.popleft()
        #终止条件
        if state[2] == all_empty_mask:
            path = []
            current = state
            while not current == None:
                path.append(action[current])
                current = parent[current]
            path.reverse()
            return True, path, depth[state]
        if depth[state] >= upper:
            return False, None, -1
        #这里要特别注意，虽然整体代码能跑起来，但是search1和search2不能单用了
        #因为步数上界的存在，可能会返回假阴性
        #下面生成所有可能的后继情况
        #对于单人搜索，一共有6种后继：上、下、左、右、逆时针转delta、顺时针转delta
        all_possible_next = collections.deque()
        guard = state[0]
        face = state[1]
        guard_up = (guard[0], guard[1] + 1)
        guard_down = (guard[0], guard[1] - 1)
        guard_left = (guard[0] - 1, guard[1])
        guard_right = (guard[0] + 1, guard[1])
        face_anticlock = (face + delta) % 12
        face_clock = (face - delta) % 12
        all_possible_next.append(((guard_up, face, state[2]), 'up'))
        all_possible_next.append(((guard_down, face, state[2]), 'down'))
        all_possible_next.append(((guard_left, face, state[2]), 'left'))
        all_possible_next.append(((guard_right, face, state[2]), 'right'))
        all_possible_next.append(((guard, face_anticlock, state[2]), 'anticlock'))
        all_possible_next.append(((guard, face_clock, state[2]), 'clock'))
        #然后检查所有的可能后继，先检查有没有超出地图
        for next_state, act in all_possible_next:
            guard_x, guard_y = next_state[0]
            if 0 <= guard_x < width and 0 <= guard_y < height and map1[guard_x][guard_y] == 0:
                #接下来过一遍check函数
                if check(next_state[0], next_state[1], cleared_mask = state[2]):
                    #check也过了就说明这个状态是合法的
                    #我们维护一下cleared和seen
                    new_cleared = next_state[2] | visible_mask_at(next_state[0], next_state[1])
                    next_state_changed = (next_state[0], next_state[1], new_cleared)
                    if not next_state_changed in seen:
                        seen.add(next_state_changed)
                        queue.append(next_state_changed)
                        parent[next_state_changed] = state
                        action[next_state_changed] = act
                        depth[next_state_changed] = depth[state] + 1
    return False, None, -1
#test
#先留着后面可能要用
# input2()
# start = input_start()
# solution = False
# all_empty_mask = find_all_empty_mask()
# for face in range(12):
#     initial_mask = visible_mask_at(start, face)
#     initial = (start, face, initial_mask)
#     result, path = search1(initial)
#     if result:
#         print(path)
#         solution = True
#         break
# if not solution:
#     print('无解！')
#单人搜索测试完毕，下面做个双人搜索
def next_step_generator(state, action1, action2):
    #state也是一个包含五样东西的tuple，依次为：
    #守卫1位置，守卫1面向，守卫2位置，守卫2面向，已清除集合（用位掩码表示）
    #action1有6种取值，分别对应'up', 'down', 'left', 'right', 'anticlock', 'clock'
    #action2也是一样
    guard1, face1, guard2, face2, cleared_mask = state
    if action1 == 'up':
        new_guard1 = (guard1[0], guard1[1] + 1)
        new_face1 = face1
    if action1 == 'down':
        new_guard1 = (guard1[0], guard1[1] - 1)
        new_face1 = face1
    if action1 == 'left':
        new_guard1 = (guard1[0] - 1, guard1[1])
        new_face1 = face1
    if action1 == 'right':
        new_guard1 = (guard1[0] + 1, guard1[1])
        new_face1 = face1
    if action1 == 'anticlock':
        new_guard1 = guard1
        new_face1 = (face1 + delta) % 12
    if action1 == 'clock':
        new_guard1 = guard1
        new_face1 = (face1 - delta) % 12
    if action2 == 'up':
        new_guard2 = (guard2[0], guard2[1] + 1)
        new_face2 = face2
    if action2 == 'down':
        new_guard2 = (guard2[0], guard2[1] - 1)
        new_face2 = face2
    if action2 == 'left':
        new_guard2 = (guard2[0] - 1, guard2[1])
        new_face2 = face2
    if action2 == 'right':
        new_guard2 = (guard2[0] + 1, guard2[1])
        new_face2 = face2
    if action2 == 'anticlock':
        new_guard2 = guard2
        new_face2 = (face2 + delta) % 12
    if action2 == 'clock':
        new_guard2 = guard2
        new_face2 = (face2 - delta) % 12
    new_state = (new_guard1, new_face1, new_guard2, new_face2, cleared_mask)
    #这里action1，action2一起还回去，方便后面记录path
    return new_state, action1, action2
#同理给search2加个上界
def search2(initial, upper):
    #传进去的initial应该是一个包含五样东西的tuple，依次为：
    #守卫1位置，守卫1面向，守卫2位置，守卫2面向，已清除集合
    #这里每一次生成后续都有36种情况，手写太麻烦
    #回过头去写一个next_step_generator
    #初始化
    queue = collections.deque()
    queue.append(initial)
    seen = {initial}
    parent = {}
    action = {}
    parent[initial] = None
    action[initial] = None
    #初始情况检验
    if not check(initial[0], initial[1], initial[2], initial[3], initial[4]):
            return False, None, -1
    depth = {initial: 0}
    while queue:
        state = queue.popleft()
        #终止条件
        if state[4] == all_empty_mask:
            path = []
            current = state
            while not current == None:
                path.append(action[current])
                current = parent[current]
            path.reverse()
            return True, path, depth[state]
        if depth[state] >= upper:
            return False, None, -1
        #接下来生成所有可能的下一步
        all_possible_next = collections.deque()
        for action1 in ['up', 'down', 'left', 'right', 'anticlock', 'clock']:
            for action2 in ['up', 'down', 'left', 'right', 'anticlock', 'clock']:
                all_possible_next.append(next_step_generator(state, action1, action2))
        for next_state, action1, action2 in all_possible_next:
            guard1, face1, guard2, face2, cleared_mask = next_state
            x1, y1 = guard1
            x2, y2 = guard2
            if 0 <= x1 < width and 0 <= y1 < height and 0 <= x2 < width and 0 <= y2 < height and map1[x1][y1] == 0 and map1[x2][y2] == 0:
                if check(guard1, face1, guard2, face2, cleared_mask):
                    #这里说明状态合法，维护cleared_mask和seen
                    new_cleared_mask = (cleared_mask | visible_mask_at(guard1, face1)) | visible_mask_at(guard2, face2)
                    next_state_changed = (guard1, face1, guard2, face2, new_cleared_mask)
                    if not next_state_changed in seen:
                        seen.add(next_state_changed)
                        queue.append(next_state_changed)
                        parent[next_state_changed] = state
                        action[next_state_changed] = (action1, action2)
                        depth[next_state_changed] = depth[state] + 1
    return False, None, -1
#前置部分全部完成，下面编写主函数
#下面这个是初版，因为初始情况比较复杂所以是一旦搜到就立刻返回
#但是紧接着就发现要求步数下界并不难，所以后面写了一个求步数下界的版本
# input2()
# start = input_start()
# solution = False
# all_empty_mask = find_all_empty_mask()
# # 先进行单人搜索
# for face in range(12):
#     initial_mask = visible_mask_at(start, face)
#     initial = (start, face, initial_mask)
#     result, path = search1(initial)
#     if result:
#         print('本地图可以单人搜索完毕，其中一个路径如下：')
#         print(path)
#         solution = True
#         break
# # 如果单人没搜出来接下来进双人搜索
# if not solution:
#     found = False
#     for face1 in range(12):
#         for face2 in range(12):
#             cleared = visible_mask_at(start, face1) | visible_mask_at(start, face2)
#             initial = (start, face1, start, face2, cleared)
#             result, path = search2(initial)
#             if result:
#                 print('本地图需要至少两人才可安全搜索，其中一个路径如下：')
#                 print(path)
#                 solution = True
#                 found = True
#                 break
#         if found:
#             break
# if not solution:
#     #如果双人也没搜出来就输出退化解
#     print('本地图需要至少三人才可安全搜索。没有非平凡的安全路径。')
#以下为输出最短路径的结果
input2()
start = input_start()
solution = False
all_empty_mask = find_all_empty_mask()
# memo1 = {}
# 先进行单人搜索
final_path = None
final_step = -1
best_face = -1
best = 9999999
for face in range(12):
    initial_mask = visible_mask_at(start, face)
    initial = (start, face, initial_mask)
    result, path, step = search1(initial, best)
    if result:
        final_path, final_step, best_face = path, step, face
        best = step
        solution = True
if solution:
    print(f'本地图可以单人完成搜索，最小步数为{final_step}，可以在初始面向取{best_face * 30}度时取得，一个最优路径为{final_path}。')
#这段是老版本，弃用了
    # if result:
    #     memo1[face] = (path, len(path) - 1)
    #     best = len(path - 1)
# if memo1 != {}:
#     solution = True
#     steps_min = 10000
#     best_initial_face = -1
#     for face in memo1:
#         if memo1[face][1] < steps_min:
#             steps_min = memo1[face][1]
#             best_initial_face = face
#     print(f'本地图可以单人完成搜索，最小步数为{memo1[best_initial_face][1]}，可以在初始面向取{best_initial_face * 30}度时取得，一个最优路径为{memo1[best_initial_face][0]}。')
# 如果单人没搜出来接下来进双人搜索
# memo2 = {}
best_faces = (-1, -1)
final_path = None
final_step = -1
best = 9999999
#理论上来说除了best之外其他几个变量都不用重置
#但是为了保险起见还是重置一下，没啥影响
if not solution:
    for face1 in range(12):
        for face2 in range(face1, 12):
            cleared = visible_mask_at(start, face1) | visible_mask_at(start, face2)
            initial = (start, face1, start, face2, cleared)
            result, path, step = search2(initial, best)
            if result:
                final_path , final_step, best_faces = path, step, (face1, face2)
                best = step
                solution = True
    if solution:
        print(f'本地图至少需要两人才可安全搜索，最小步数为{final_step}，可以在两个守卫分别面向{best_faces[0] * 30}度和{best_faces[1] * 30}度时取得，与之对应的一个最优路径为{final_path}')
    #下面的弃用了
    #         if result:
    #             memo2[(face1, face2)] = (path, len(path) - 1)
    # if memo2 != {}:
    #     solution = True
    #     steps_min = 10000
    #     best_initial_face1, best_initial_face2 = -1, -1
    #     for faces in memo2:
    #         if memo2[faces][1] < steps_min:
    #             steps_min = memo2[faces][1]
    #             best_initial_face1, best_initial_face2 = faces
    #             best_path = memo2[faces][0]
    # print(f'本地图至少需要两人才可安全搜索，最小步数为{steps_min}，可以在两个守卫分别面向{best_initial_face1 * 30}度和{best_initial_face2 * 30}度时取得，与之对应的一个最优路径为{best_path}')
if not solution:
    #如果双人也没搜出来就输出退化解
    print('本地图需要至少三人才可安全搜索。没有非平凡的安全路径。')
#不知道为什么双人搜的很慢，耐心等待即可，主要是我懒得优化了
    

        
    



                        



    
    
    
