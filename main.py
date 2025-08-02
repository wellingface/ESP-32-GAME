from machine import Pin, I2C, ADC, RTC
import network
import time
import random
import math
import ntptime
from ssd1306 import SSD1306_I2C

# 初始化OLED屏幕
WIDTH = 128
HEIGHT = 64
i2c = I2C(0, scl=Pin(1), sda=Pin(2), freq=400000)
oled = SSD1306_I2C(WIDTH, HEIGHT, i2c)

# 初始化PS2摇杆和按钮
JOYSTICK_X = ADC(Pin(13))
JOYSTICK_Y = ADC(Pin(14))
FIRE_BUTTON = Pin(12, Pin.IN, Pin.PULL_UP)  # 开火/跳跃按钮
SELECT_BUTTON = Pin(21, Pin.IN, Pin.PULL_UP)  # 选择按钮
JOYSTICK_X.atten(ADC.ATTN_11DB)
JOYSTICK_Y.atten(ADC.ATTN_11DB)

# 初始化实时时钟
rtc = RTC()

# 系统常量
DEADZONE = 1000
CENTER = 2048
SELECTED_ICON = 0
GAMES = 9  # 包含设置
IS_DESKTOP = False
CURRENT_GAME = None
CURRENT_SCREEN = "main"  # 用于设置界面导航

# 游戏图标坐标 (x, y)
ICON_POSITIONS = [
    (10, 10),   # 贪吃蛇
    (35, 10),   # 恐龙跳
    (60, 10),   # 打飞机
    (85, 10),   # 俄罗斯方块
    (110, 10),  # 推箱子
    (10, 35),   # 计算器
    (35, 35),   # 接球游戏
    (60, 35),   # 赛车游戏
    (85, 35)    # 设置
]

# WiFi设置相关变量
wifi_ssids = []
wifi_selected = 0
wifi_scroll = 0
wifi_password = ""
wifi_keyboard_pos = 0
keyboard_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
keyboard_page = 0
keyboard_pages = 3  # 3页键盘

# 时间设置相关变量
time_edit_pos = 0  # 0-5: H1 H2 : M1 M2 : S1 S2
time_values = [0, 0, 0, 0, 0, 0]

# 绘制填充圆形的函数
def fill_circle(x0, y0, r, c=1):
    x = r
    y = 0
    err = 0
    
    while x >= y:
        oled.pixel(x0 + x, y0 + y, c)
        oled.pixel(x0 + y, y0 + x, c)
        oled.pixel(x0 - y, y0 + x, c)
        oled.pixel(x0 - x, y0 + y, c)
        oled.pixel(x0 - x, y0 - y, c)
        oled.pixel(x0 - y, y0 - x, c)
        oled.pixel(x0 + y, y0 - x, c)
        oled.pixel(x0 + x, y0 - y, c)
        
        y += 1
        if err <= 0:
            err += 2*y + 1
        if err > 0:
            x -= 1
            err -= 2*x + 1

# 绘制完整矩形Windows徽标
def draw_win_logo(x, y):
    oled.fill_rect(x, y, 8, 8, 1)    # 左上
    oled.fill_rect(x+10, y, 8, 8, 1) # 右上
    oled.fill_rect(x, y+10, 8, 8, 1) # 左下
    oled.fill_rect(x+10, y+10, 8, 8, 1) # 右下
    oled.fill_rect(x+5, y+5, 8, 8, 0) # 中心

# 绘制圆形加载动画
def draw_loading_circle(x, y, progress):
    radius = 10
    # 绘制外圆
    for angle in range(360):
        rad = math.radians(angle)
        px = x + int(radius * math.cos(rad))
        py = y + int(radius * math.sin(rad))
        if 0 <= px < WIDTH and 0 <= py < HEIGHT:
            oled.pixel(px, py, 1)
    
    # 绘制进度弧
    for angle in range(int(progress * 3.6)):
        rad = math.radians(angle - 90)
        px = x + int(radius * 0.7 * math.cos(rad))
        py = y + int(radius * 0.7 * math.sin(rad))
        if 0 <= px < WIDTH and 0 <= py < HEIGHT:
            oled.pixel(px, py, 1)

# 绘制游戏图标
def draw_icons():
    # 1. 贪吃蛇图标
    x, y = ICON_POSITIONS[0]
    oled.fill_rect(x, y, 5, 5, 1)
    oled.fill_rect(x+7, y+2, 5, 5, 1)
    oled.pixel(x+5, y+2, 1)
    oled.pixel(x+6, y+2, 1)
    
    # 2. 恐龙跳图标
    x, y = ICON_POSITIONS[1]
    oled.fill_rect(x+2, y, 6, 2, 1)  # 头部
    oled.fill_rect(x, y+2, 10, 4, 1) # 身体
    oled.fill_rect(x-1, y+4, 2, 3, 1) # 腿
    
    # 3. 打飞机图标
    x, y = ICON_POSITIONS[2]
    oled.fill_rect(x+2, y, 6, 4, 1)  # 机身
    oled.fill_rect(x, y+2, 2, 2, 1)  # 左翼
    oled.fill_rect(x+8, y+2, 2, 2, 1) # 右翼
    oled.pixel(x+5, y-1, 1)  # 机头
    
    # 4. 俄罗斯方块图标
    x, y = ICON_POSITIONS[3]
    oled.fill_rect(x, y, 3, 3, 1)
    oled.fill_rect(x+3, y, 3, 3, 1)
    oled.fill_rect(x, y+3, 3, 3, 1)
    oled.fill_rect(x+3, y+3, 3, 3, 1)
    
    # 5. 推箱子图标
    x, y = ICON_POSITIONS[4]
    oled.fill_rect(x, y, 6, 6, 1)
    oled.fill_rect(x+2, y-2, 2, 2, 1)
    
    # 6. 计算器图标
    x, y = ICON_POSITIONS[5]
    oled.rect(x, y, 8, 8, 1)
    oled.hline(x+1, y+2, 6, 1)
    oled.hline(x+1, y+4, 6, 1)
    oled.hline(x+1, y+6, 6, 1)
    oled.vline(x+3, y+1, 7, 1)
    oled.vline(x+6, y+1, 7, 1)
    
    # 7. 接球游戏图标
    x, y = ICON_POSITIONS[6]
    oled.fill_rect(x, y+6, 10, 2, 1)  # 挡板
    fill_circle(x+5, y+3, 2, 1)  # 球
    
    # 8. 赛车游戏图标
    x, y = ICON_POSITIONS[7]
    oled.fill_rect(x+2, y+2, 6, 4, 1)  # 车身
    oled.fill_rect(x, y+4, 2, 2, 1)    # 左车轮
    oled.fill_rect(x+8, y+4, 2, 2, 1)  # 右车轮
    
    # 9. 设置图标
    x, y = ICON_POSITIONS[8]
    oled.rect(x, y, 8, 8, 1)
    oled.fill_rect(x+2, y+2, 2, 2, 1)
    oled.fill_rect(x+4, y+2, 2, 2, 1)
    oled.fill_rect(x+2, y+4, 2, 2, 1)
    oled.fill_rect(x+4, y+4, 2, 2, 1)

# 绘制选中框
def draw_selection():
    x, y = ICON_POSITIONS[SELECTED_ICON]
    oled.rect(x-2, y-2, 12, 12, 1)

# 绘制任务栏
def draw_taskbar():
    oled.fill_rect(0, HEIGHT-10, WIDTH, 10, 1)
    # 开始按钮
    draw_win_logo(2, HEIGHT-9)
    # 任务栏中间
    oled.text("GAME", 20, HEIGHT-8, 0)
    # 时间区域 - 显示当前时间
    try:
        t = rtc.datetime()
        time_str = f"{t[4]:02d}:{t[5]:02d}"
        oled.text(time_str, WIDTH-35, HEIGHT-8, 0)
    except:
        oled.text("--:--", WIDTH-35, HEIGHT-8, 0)

# 读取摇杆输入
def read_joystick():
    x = JOYSTICK_X.read()
    y = JOYSTICK_Y.read()
    
    if x < CENTER - DEADZONE:
        return "LEFT"
    elif x > CENTER + DEADZONE:
        return "RIGHT"
    elif y < CENTER - DEADZONE:
        return "UP"
    elif y > CENTER + DEADZONE:
        return "DOWN"
    return None

# 检查按钮状态
def is_fire_pressed():
    return FIRE_BUTTON.value() == 0

def is_select_pressed():
    return SELECT_BUTTON.value() == 0

# 启动界面（4秒）
def startup_screen():
    start_time = time.ticks_ms()
    
    while time.ticks_ms() - start_time < 4000:
        oled.fill(0)
        
        # 左侧显示完整Windows标志
        draw_win_logo(30, HEIGHT//2-10)
        
        # 显示启动文字（字母）
        oled.text("START", 60, HEIGHT//2-5)
        oled.text("SYSTM", 60, HEIGHT//2+5)
        
        # 右侧圆形加载动画
        progress = (time.ticks_ms() - start_time) / 4000
        draw_loading_circle(WIDTH-30, HEIGHT//2, progress)
        
        oled.show()
        time.sleep_ms(50)

# 桌面界面
def draw_desktop():
    oled.fill(0)
    # 桌面背景（简单网格）
    for x in range(0, WIDTH, 16):
        for y in range(0, HEIGHT-10, 16):
            oled.pixel(x, y, 1)
    
    # 绘制图标
    draw_icons()
    # 绘制选中框
    draw_selection()
    # 绘制任务栏
    draw_taskbar()
    oled.show()

# 贪吃蛇游戏
def snake_game():
    global IS_DESKTOP, CURRENT_GAME
    CURRENT_GAME = "snake"
    
    GRID = 8
    MAX_X = WIDTH//GRID - 1
    MAX_Y = (HEIGHT-10)//GRID - 1
    snake = [(5, 5), (4, 5), (3, 5)]
    direction = "RIGHT"
    food = (10, 5)
    score = 0
    game_over = False
    last_move = time.ticks_ms()
    
    def generate_food():
        while True:
            x = random.randint(0, MAX_X)
            y = random.randint(0, MAX_Y)
            if (x, y) not in snake:
                return (x, y)
    
    food = generate_food()
    
    while not game_over and CURRENT_GAME == "snake":
        if is_select_pressed():
            time.sleep_ms(500)
            if is_select_pressed():
                IS_DESKTOP = True
                return
        
        joy = read_joystick()
        if joy == "LEFT" and direction != "RIGHT":
            direction = "LEFT"
        elif joy == "RIGHT" and direction != "LEFT":
            direction = "RIGHT"
        elif joy == "UP" and direction != "DOWN":
            direction = "UP"
        elif joy == "DOWN" and direction != "UP":
            direction = "DOWN"
        
        if time.ticks_ms() - last_move > 200:
            head_x, head_y = snake[0]
            if direction == "LEFT":
                new_head = (head_x - 1, head_y)
            elif direction == "RIGHT":
                new_head = (head_x + 1, head_y)
            elif direction == "UP":
                new_head = (head_x, head_y - 1)
            else:
                new_head = (head_x, head_y + 1)
            
            if (new_head[0] < 0 or new_head[0] > MAX_X or
                new_head[1] < 0 or new_head[1] > MAX_Y or
                new_head in snake):
                game_over = True
            
            snake.insert(0, new_head)
            
            if new_head == food:
                score += 10
                food = generate_food()
            else:
                snake.pop()
            
            last_move = time.ticks_ms()
        
        oled.fill(0)
        hx, hy = snake[0]
        oled.fill_rect(hx*GRID, hy*GRID, GRID, GRID, 1)
        for (x, y) in snake[1:]:
            oled.fill_rect(x*GRID+1, y*GRID+1, GRID-2, GRID-2, 1)
        fx, fy = food
        oled.fill_rect(fx*GRID+2, fy*GRID+2, GRID-4, GRID-4, 1)
        oled.text(f"S:{score}", 5, HEIGHT-9)
        oled.text("BACK", WIDTH-30, HEIGHT-9)
        oled.hline(0, HEIGHT-10, WIDTH, 1)
        oled.show()
        time.sleep_ms(50)
    
    oled.fill(0)
    oled.text("OVER", 40, 20)
    oled.text(f"S:{score}", 35, 35)
    oled.text("MENU", 40, 50)
    oled.show()
    while not is_select_pressed():
        time.sleep_ms(50)
    IS_DESKTOP = True

# 恐龙跳游戏
def dino_game():
    global IS_DESKTOP, CURRENT_GAME
    CURRENT_GAME = "dino"
    
    dino_y = HEIGHT - 20
    velocity = 0
    gravity = 0.6
    jump_force = -9
    obstacles = []
    score = 0
    frame = 0
    game_over = False
    jump_available = True
    
    while not game_over and CURRENT_GAME == "dino":
        if is_select_pressed():
            time.sleep_ms(500)
            if is_select_pressed():
                IS_DESKTOP = True
                return
        
        if is_fire_pressed() and jump_available and dino_y >= HEIGHT - 20:
            velocity = jump_force
            jump_available = False
            while is_fire_pressed():
                time.sleep_ms(10)
        
        if not is_fire_pressed():
            jump_available = True
        
        velocity += gravity
        dino_y += velocity
        if dino_y > HEIGHT - 20:
            dino_y = HEIGHT - 20
            velocity = 0
        
        frame += 1
        if frame % 50 == 0:
            obstacles.append({"x": WIDTH, "w": 5, "h": random.randint(8, 12)})
        
        for obs in obstacles[:]:
            obs["x"] -= 2
            if obs["x"] < -obs["w"]:
                obstacles.remove(obs)
                score += 1
        
        dino_rect = (10, dino_y, 10, 12)
        for obs in obstacles:
            o_rect = (obs["x"], HEIGHT - 10 - obs["h"], obs["w"], obs["h"])
            if (dino_rect[0] < o_rect[0] + o_rect[2] and
                dino_rect[0] + dino_rect[2] > o_rect[0] and
                dino_rect[1] < o_rect[1] + o_rect[3] and
                dino_rect[1] + dino_rect[3] > o_rect[1]):
                game_over = True
        
        oled.fill(0)
        oled.hline(0, HEIGHT-10, WIDTH, 1)
        oled.fill_rect(10, int(dino_y), 10, 12, 1)
        oled.pixel(18, int(dino_y)+2, 0)
        for obs in obstacles:
            oled.fill_rect(obs["x"], HEIGHT - 10 - obs["h"], obs["w"], obs["h"], 1)
        oled.text(f"S:{score}", 5, HEIGHT-9)
        oled.text("JUMP", WIDTH-30, HEIGHT-9)
        oled.show()
        time.sleep_ms(30)
    
    oled.fill(0)
    oled.text("OVER", 40, 20)
    oled.text(f"S:{score}", 35, 35)
    oled.text("MENU", 40, 50)
    oled.show()
    while not is_select_pressed():
        time.sleep_ms(50)
    IS_DESKTOP = True

# 打飞机游戏
def plane_game():
    global IS_DESKTOP, CURRENT_GAME
    CURRENT_GAME = "plane"
    
    plane_x = WIDTH//2
    bullets = []
    enemies = []
    score = 0
    frame = 0
    game_over = False
    last_shot = 0
    
    while not game_over and CURRENT_GAME == "plane":
        if is_select_pressed():
            time.sleep_ms(500)
            if is_select_pressed():
                IS_DESKTOP = True
                return
        
        joy = read_joystick()
        if joy == "LEFT" and plane_x > 5:
            plane_x -= 3
        elif joy == "RIGHT" and plane_x < WIDTH - 13:
            plane_x += 3
        
        current_time = time.ticks_ms()
        if is_fire_pressed() and len(bullets) < 3 and current_time - last_shot > 300:
            bullets.append({"x": plane_x + 4, "y": HEIGHT - 20})
            last_shot = current_time
            while is_fire_pressed():
                time.sleep_ms(10)
        
        for b in bullets[:]:
            b["y"] -= 4
            if b["y"] < 0:
                bullets.remove(b)
        
        frame += 1
        if frame % 40 == 0:
            enemies.append({"x": random.randint(10, WIDTH-20), "y": 5})
        
        for e in enemies[:]:
            e["y"] += 2
            if e["y"] > HEIGHT:
                enemies.remove(e)
        
        p_rect = (plane_x, HEIGHT-15, 10, 8)
        for e in enemies:
            e_rect = (e["x"], e["y"], 8, 6)
            if (p_rect[0] < e_rect[0] + e_rect[2] and
                p_rect[0] + p_rect[2] > e_rect[0] and
                p_rect[1] < e_rect[1] + e_rect[3] and
                p_rect[1] + p_rect[3] > e_rect[1]):
                game_over = True
        
        for b in bullets[:]:
            b_rect = (b["x"], b["y"], 2, 4)
            for e in enemies[:]:
                e_rect = (e["x"], e["y"], 8, 6)
                if (b_rect[0] < e_rect[0] + e_rect[2] and
                    b_rect[0] + b_rect[2] > e_rect[0] and
                    b_rect[1] < e_rect[1] + e_rect[3] and
                    b_rect[1] + b_rect[3] > e_rect[1]):
                    bullets.remove(b)
                    enemies.remove(e)
                    score += 10
                    break
        
        oled.fill(0)
        oled.fill_rect(plane_x, HEIGHT-15, 10, 8, 1)
        oled.fill_rect(plane_x-2, HEIGHT-13, 2, 2, 1)
        oled.fill_rect(plane_x+10, HEIGHT-13, 2, 2, 1)
        for b in bullets:
            oled.fill_rect(b["x"], b["y"], 2, 4, 1)
        for e in enemies:
            oled.fill_rect(e["x"], e["y"], 8, 6, 1)
        oled.text(f"S:{score}", 5, HEIGHT-9)
        oled.text("FIRE", WIDTH-30, HEIGHT-9)
        oled.hline(0, HEIGHT-10, WIDTH, 1)
        oled.show()
        time.sleep_ms(30)
    
    oled.fill(0)
    oled.text("OVER", 40, 20)
    oled.text(f"S:{score}", 35, 35)
    oled.text("MENU", 40, 50)
    oled.show()
    while not is_select_pressed():
        time.sleep_ms(50)
    IS_DESKTOP = True

# 俄罗斯方块游戏
def tetris_game():
    global IS_DESKTOP, CURRENT_GAME
    CURRENT_GAME = "tetris"
    
    WIDTH_TET = 10
    HEIGHT_TET = 8
    GRID = 6
    board = [[0 for _ in range(WIDTH_TET)] for _ in range(HEIGHT_TET)]
    shapes = [
        [[1, 1, 1, 1]],  # I
        [[1, 1], [1, 1]],  # O
        [[1, 1, 1], [0, 1, 0]],  # T
        [[1, 1, 1], [1, 0, 0]],  # L
        [[1, 1, 1], [0, 0, 1]],  # J
        [[1, 1, 0], [0, 1, 1]],  # S
        [[0, 1, 1], [1, 1, 0]]   # Z
    ]
    current_shape = random.choice(shapes)
    shape_x = WIDTH_TET//2 - len(current_shape[0])//2
    shape_y = 0
    score = 0
    game_over = False
    last_fall = time.ticks_ms()
    
    def new_shape():
        nonlocal current_shape, shape_x, shape_y, game_over
        current_shape = random.choice(shapes)
        shape_x = WIDTH_TET//2 - len(current_shape[0])//2
        shape_y = 0
        for y, row in enumerate(current_shape):
            for x, cell in enumerate(row):
                if cell and (shape_y + y >= HEIGHT_TET or 
                            shape_x + x < 0 or 
                            shape_x + x >= WIDTH_TET or
                            board[shape_y + y][shape_x + x]):
                    game_over = True
    
    while not game_over and CURRENT_GAME == "tetris":
        if is_select_pressed():
            time.sleep_ms(500)
            if is_select_pressed():
                IS_DESKTOP = True
                return
        
        joy = read_joystick()
        if joy == "LEFT":
            new_x = shape_x - 1
            valid = True
            for y, row in enumerate(current_shape):
                for x, cell in enumerate(row):
                    if cell and (new_x + x < 0 or 
                                board[shape_y + y][new_x + x]):
                        valid = False
                        break
                if not valid:
                    break
            if valid:
                shape_x = new_x
        elif joy == "RIGHT":
            new_x = shape_x + 1
            valid = True
            for y, row in enumerate(current_shape):
                for x, cell in enumerate(row):
                    if cell and (new_x + x >= WIDTH_TET or 
                                board[shape_y + y][new_x + x]):
                        valid = False
                        break
                if not valid:
                    break
            if valid:
                shape_x = new_x
        elif joy == "DOWN":
            new_y = shape_y + 1
            valid = True
            for y, row in enumerate(current_shape):
                for x, cell in enumerate(row):
                    if cell and (new_y + y >= HEIGHT_TET or 
                                board[new_y + y][shape_x + x]):
                        valid = False
                        break
                if not valid:
                    break
            if valid:
                shape_y = new_y
        elif joy == "UP":
            rotated = list(zip(*current_shape[::-1]))
            valid = True
            for y, row in enumerate(rotated):
                for x, cell in enumerate(row):
                    if cell and (shape_y + y >= HEIGHT_TET or 
                                shape_x + x < 0 or 
                                shape_x + x >= WIDTH_TET or
                                board[shape_y + y][shape_x + x]):
                        valid = False
                        break
                if not valid:
                    break
            if valid:
                current_shape = [list(row) for row in rotated]
        
        if time.ticks_ms() - last_fall > 1000:
            new_y = shape_y + 1
            valid = True
            for y, row in enumerate(current_shape):
                for x, cell in enumerate(row):
                    if cell and (new_y + y >= HEIGHT_TET or 
                                board[new_y + y][shape_x + x]):
                        valid = False
                        break
                if not valid:
                    break
            if valid:
                shape_y = new_y
            else:
                for y, row in enumerate(current_shape):
                    for x, cell in enumerate(row):
                        if cell:
                            board[shape_y + y][shape_x + x] = 1
                lines_cleared = 0
                for y in range(HEIGHT_TET):
                    if all(board[y]):
                        lines_cleared += 1
                        for y2 in range(y, 0, -1):
                            board[y2] = board[y2-1][:]
                        board[0] = [0]*WIDTH_TET
                score += lines_cleared * 100
                new_shape()
            last_fall = time.ticks_ms()
        
        oled.fill(0)
        for y in range(HEIGHT_TET):
            for x in range(WIDTH_TET):
                if board[y][x]:
                    oled.fill_rect(x*GRID + 5, y*GRID + 5, GRID-1, GRID-1, 1)
        for y, row in enumerate(current_shape):
            for x, cell in enumerate(row):
                if cell:
                    oled.fill_rect((shape_x + x)*GRID + 5, 
                                  (shape_y + y)*GRID + 5, 
                                  GRID-1, GRID-1, 1)
        oled.text(f"S:{score}", 5, HEIGHT-9)
        oled.text("BACK", WIDTH-30, HEIGHT-9)
        oled.hline(0, HEIGHT-10, WIDTH, 1)
        oled.show()
        time.sleep_ms(50)
    
    oled.fill(0)
    oled.text("OVER", 40, 20)
    oled.text(f"S:{score}", 35, 35)
    oled.text("MENU", 40, 50)
    oled.show()
    while not is_select_pressed():
        time.sleep_ms(50)
    IS_DESKTOP = True

# 推箱子游戏
def sokoban_game():
    global IS_DESKTOP, CURRENT_GAME
    CURRENT_GAME = "sokoban"
    
    level = [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        [1, 0, 2, 0, 1, 0, 0, 2, 0, 1],
        [1, 0, 0, 0, 0, 0, 1, 0, 0, 1],
        [1, 1, 0, 2, 1, 1, 1, 0, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 2, 0, 2, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    ]
    player_x, player_y = 1, 1
    moves = 0
    game_over = False
    
    def check_win():
        for y in range(8):
            for x in range(10):
                if level[y][x] == 2:
                    return False
        return True
    
    while not game_over and CURRENT_GAME == "sokoban":
        if is_select_pressed():
            time.sleep_ms(500)
            if is_select_pressed():
                IS_DESKTOP = True
                return
        
        joy = read_joystick()
        dx, dy = 0, 0
        if joy == "LEFT":
            dx = -1
        elif joy == "RIGHT":
            dx = 1
        elif joy == "UP":
            dy = -1
        elif joy == "DOWN":
            dy = 1
        
        if dx != 0 or dy != 0:
            new_x = player_x + dx
            new_y = player_y + dy
            
            if level[new_y][new_x] == 1:
                dx, dy = 0, 0
            elif level[new_y][new_x] == 2:
                box_new_x = new_x + dx
                box_new_y = new_y + dy
                if level[box_new_y][box_new_x] in (0, 3):
                    level[new_y][new_x] -= 2
                    level[box_new_y][box_new_x] += 2
                else:
                    dx, dy = 0, 0
            
            if dx != 0 or dy != 0:
                player_x = new_x
                player_y = new_y
                moves += 1
                if check_win():
                    game_over = True
        
        oled.fill(0)
        for y in range(8):
            for x in range(10):
                if level[y][x] == 1:
                    oled.fill_rect(x*6 + 10, y*6 + 5, 5, 5, 1)
                elif level[y][x] in (2, 5):
                    oled.fill_rect(x*6 + 12, y*6 + 7, 3, 3, 1)
                elif level[y][x] == 3:
                    oled.rect(x*6 + 11, y*6 + 6, 4, 4, 1)
        
        oled.fill_rect(player_x*6 + 11, player_y*6 + 6, 4, 4, 1)
        oled.text(f"M:{moves}", 5, HEIGHT-9)
        oled.text("BACK", WIDTH-30, HEIGHT-9)
        oled.hline(0, HEIGHT-10, WIDTH, 1)
        oled.show()
        time.sleep_ms(100)
    
    oled.fill(0)
    oled.text("WIN!", 40, 20)
    oled.text(f"M:{moves}", 35, 35)
    oled.text("MENU", 40, 50)
    oled.show()
    while not is_select_pressed():
        time.sleep_ms(50)
    IS_DESKTOP = True

# 计算器（改进显示）
def calculator_game():
    global IS_DESKTOP, CURRENT_GAME
    CURRENT_GAME = "calc"
    
    # 计算器状态
    display = "0"
    current_num = "0"
    operator = None
    result = None
    mode = "INPUT"  # INPUT, OPERATOR, RESULT
    
    # 紧凑的按钮布局，缩小间距
    buttons = [
        {"x":2, "y":12, "w":16, "h":9, "label":"C"},
        {"x":20, "y":12, "w":16, "h":9, "label":"/"},
        {"x":38, "y":12, "w":16, "h":9, "label":"*"},
        {"x":56, "y":12, "w":16, "h":9, "label":"-"},
        {"x":74, "y":12, "w":16, "h":9, "label":"+"},
        {"x":92, "y":12, "w":34, "h":9, "label":"←"},
        
        {"x":2, "y":23, "w":16, "h":9, "label":"7"},
        {"x":20, "y":23, "w":16, "h":9, "label":"8"},
        {"x":38, "y":23, "w":16, "h":9, "label":"9"},
        {"x":56, "y":23, "w":16, "h":9, "label":"4"},
        {"x":74, "y":23, "w":16, "h":9, "label":"5"},
        {"x":92, "y":23, "w":16, "h":9, "label":"6"},
        
        {"x":2, "y":34, "w":16, "h":9, "label":"1"},
        {"x":20, "y":34, "w":16, "h":9, "label":"2"},
        {"x":38, "y":34, "w":16, "h":9, "label":"3"},
        {"x":56, "y":34, "w":16, "h":9, "label":"0"},
        {"x":74, "y":34, "w":16, "h":9, "label":"."},
        {"x":92, "y":34, "w":16, "h":18, "label":"="},
        
        {"x":2, "y":45, "w":70, "h":9, "label":"00"},
    ]
    selected_btn = 0
    
    def calculate():
        nonlocal result, current_num, operator
        if operator and current_num:
            try:
                num1 = float(result)
                num2 = float(current_num)
                if operator == "+":
                    result = str(num1 + num2)
                elif operator == "-":
                    result = str(num1 - num2)
                elif operator == "*":
                    result = str(num1 * num2)
                elif operator == "/":
                    if num2 != 0:
                        result = str(num1 / num2)
                    else:
                        result = "Err"
                # 移除尾部的.0
                if result.endswith(".0"):
                    result = result[:-2]
                return True
            except:
                result = "Err"
                return True
        return False
    
    while CURRENT_GAME == "calc":
        if is_select_pressed():
            time.sleep_ms(500)
            if is_select_pressed():
                IS_DESKTOP = True
                return
        
        # 导航按钮
        joy = read_joystick()
        current_time = time.ticks_ms()
        if joy == "LEFT" and current_time % 200 < 50:
            if selected_btn in [1,2,3,4,6,7,8,9,10,12]:
                selected_btn -= 1
        elif joy == "RIGHT" and current_time % 200 < 50:
            if selected_btn in [0,1,2,3,5,6,7,8,9,11]:
                selected_btn += 1
        elif joy == "UP" and current_time % 200 < 50:
            if selected_btn in [5,6,7,8,9,10,11,12]:
                if selected_btn == 5:
                    selected_btn = 0
                elif selected_btn in [6,7,8,9,10]:
                    selected_btn -=5
                elif selected_btn == 11:
                    selected_btn =4
                elif selected_btn ==12:
                    selected_btn =5
        elif joy == "DOWN" and current_time % 200 < 50:
            if selected_btn in [0,1,2,3,4,5,6,7,8,9,10]:
                if selected_btn ==0:
                    selected_btn =5
                elif selected_btn in [1,2,3,4,5]:
                    selected_btn +=5
                elif selected_btn in [6,7,8,9,10]:
                    selected_btn =12
        
        # 按下按钮
        if is_fire_pressed():
            label = buttons[selected_btn]["label"]
            
            if label == "C":  # 清除
                display = "0"
                current_num = "0"
                operator = None
                result = None
                mode = "INPUT"
            elif label == "←":  # 退格
                if len(current_num) > 1:
                    current_num = current_num[:-1]
                    display = current_num
                else:
                    current_num = "0"
                    display = "0"
            elif label in ["+", "-", "*", "/"]:  # 运算符
                if mode == "INPUT":
                    result = current_num
                    operator = label
                    mode = "OPERATOR"
                elif mode == "RESULT":
                    operator = label
                    mode = "OPERATOR"
            elif label == "=":  # 等于
                if calculate():
                    display = result
                    current_num = result
                    mode = "RESULT"
            elif label == ".":  # 小数点
                if "." not in current_num:
                    current_num += "."
                    display = current_num
            elif label == "00":  # 双零
                if current_num == "0":
                    current_num = "0"
                else:
                    current_num += "00"
                display = current_num
            else:  # 数字
                if mode == "INPUT" and current_num == "0":
                    current_num = label
                elif mode == "OPERATOR" or mode == "RESULT":
                    current_num = label
                    mode = "INPUT"
                else:
                    current_num += label
                display = current_num
            
            while is_fire_pressed():
                time.sleep_ms(10)
        
        # 绘制计算器 - 优化显示
        oled.fill(0)
        # 显示屏 - 加宽以显示更多内容
        oled.fill_rect(2, 2, 124, 9, 1)
        # 显示数字（右对齐）
        display_text = display[-12:]  # 增加可显示的字符数
        text_width = len(display_text) * 6
        oled.text(display_text, 124 - text_width, 3, 0)
        
        # 绘制按钮
        for i, btn in enumerate(buttons):
            if i == selected_btn:
                oled.fill_rect(btn["x"], btn["y"], btn["w"], btn["h"], 1)
                oled.text(btn["label"], btn["x"] + 2, btn["y"] + 1, 0)
            else:
                oled.rect(btn["x"], btn["y"], btn["w"], btn["h"], 1)
                oled.text(btn["label"], btn["x"] + 2, btn["y"] + 1)
        
        # 底部提示
        oled.text("MENU", WIDTH-30, HEIGHT-9)
        oled.hline(0, HEIGHT-10, WIDTH, 1)
        oled.show()
        time.sleep_ms(50)

# 接球游戏
def catch_game():
    global IS_DESKTOP, CURRENT_GAME
    CURRENT_GAME = "catch"
    
    paddle_x = WIDTH//2 - 15
    paddle_w = 30
    paddle_h = 5
    balls = []
    score = 0
    lives = 3
    frame = 0
    game_over = False
    
    while not game_over and CURRENT_GAME == "catch":
        if is_select_pressed():
            time.sleep_ms(500)
            if is_select_pressed():
                IS_DESKTOP = True
                return
        
        joy = read_joystick()
        if joy == "LEFT" and paddle_x > 5:
            paddle_x -= 4
        elif joy == "RIGHT" and paddle_x < WIDTH - paddle_w - 5:
            paddle_x += 4
        
        frame += 1
        if frame % 60 == 0:
            ball_x = random.randint(10, WIDTH-20)
            balls.append({"x": ball_x, "y": 10, "speed": random.uniform(1, 2)})
        
        for ball in balls[:]:
            ball["y"] += ball["speed"]
            if (ball["y"] + 3 >= HEIGHT - 15 and 
                paddle_x < ball["x"] + 3 < paddle_x + paddle_w):
                balls.remove(ball)
                score += 10
            elif ball["y"] > HEIGHT:
                balls.remove(ball)
                lives -= 1
                if lives <= 0:
                    game_over = True
        
        oled.fill(0)
        oled.fill_rect(paddle_x, HEIGHT - 15, paddle_w, paddle_h, 1)
        for ball in balls:
            fill_circle(int(ball["x"]), int(ball["y"]), 3, 1)
        oled.text(f"S:{score}", 5, 5)
        oled.text(f"L:{lives}", WIDTH-30, 5)
        oled.text("BACK", WIDTH-30, HEIGHT-9)
        oled.hline(0, HEIGHT-10, WIDTH, 1)
        oled.show()
        time.sleep_ms(30)
    
    oled.fill(0)
    oled.text("OVER", 40, 20)
    oled.text(f"S:{score}", 35, 35)
    oled.text("MENU", 40, 50)
    oled.show()
    while not is_select_pressed():
        time.sleep_ms(50)
    IS_DESKTOP = True

# 赛车游戏
def racing_game():
    global IS_DESKTOP, CURRENT_GAME
    CURRENT_GAME = "race"
    
    car_x = WIDTH//2 - 5
    car_w = 10
    car_h = 15
    obstacles = []
    score = 0
    speed = 3
    frame = 0
    game_over = False
    
    while not game_over and CURRENT_GAME == "race":
        if is_select_pressed():
            time.sleep_ms(500)
            if is_select_pressed():
                IS_DESKTOP = True
                return
        
        joy = read_joystick()
        if joy == "LEFT" and car_x > 10:
            car_x -= 3
        elif joy == "RIGHT" and car_x < WIDTH - car_w - 10:
            car_x += 3
        
        frame += 1
        if frame % 40 == 0:
            lane = random.choice([20, 50, 80, 110])
            obstacles.append({"x": lane, "y": -10, "w": 20, "h": 10})
        
        for obs in obstacles[:]:
            obs["y"] += speed
            if obs["y"] > HEIGHT:
                obstacles.remove(obs)
                score += 5
        
        if frame % 500 == 0 and speed < 6:
            speed += 0.2
        
        car_rect = (car_x, HEIGHT - car_h - 10, car_w, car_h)
        for obs in obstacles:
            o_rect = (obs["x"], obs["y"], obs["w"], obs["h"])
            if (car_rect[0] < o_rect[0] + o_rect[2] and
                car_rect[0] + car_rect[2] > o_rect[0] and
                car_rect[1] < o_rect[1] + o_rect[3] and
                car_rect[1] + car_rect[3] > o_rect[1]):
                game_over = True
        
        oled.fill(0)
        for y in range(0, HEIGHT, 10):
            oled.fill_rect(32, y, 2, 6, 1)
            oled.fill_rect(64, y, 2, 6, 1)
            oled.fill_rect(96, y, 2, 6, 1)
        oled.fill_rect(car_x, HEIGHT - car_h - 10, car_w, car_h, 1)
        oled.fill_rect(car_x - 2, HEIGHT - 15, 2, 5, 1)
        oled.fill_rect(car_x + car_w, HEIGHT - 15, 2, 5, 1)
        for obs in obstacles:
            oled.fill_rect(obs["x"], obs["y"], obs["w"], obs["h"], 1)
        oled.text(f"S:{score}", 5, 5)
        oled.text("BACK", WIDTH-30, HEIGHT-9)
        oled.hline(0, HEIGHT-10, WIDTH, 1)
        oled.show()
        time.sleep_ms(30)
    
    oled.fill(0)
    oled.text("OVER", 40, 20)
    oled.text(f"S:{score}", 35, 35)
    oled.text("MENU", 40, 50)
    oled.show()
    while not is_select_pressed():
        time.sleep_ms(50)
    IS_DESKTOP = True

# 设置界面 - 主界面
def settings_main():
    global IS_DESKTOP, CURRENT_SCREEN
    CURRENT_SCREEN = "main"
    options = ["WIFI", "TIME", "BACK"]
    selected = 0
    
    while CURRENT_SCREEN == "main":
        oled.fill(0)
        oled.text("SETTINGS", 30, 5)
        
        for i, opt in enumerate(options):
            if i == selected:
                oled.fill_rect(10, 20 + i*15, 108, 12, 1)
                oled.text(opt, 15, 21 + i*15, 0)
            else:
                oled.rect(10, 20 + i*15, 108, 12, 1)
                oled.text(opt, 15, 21 + i*15)
        
        oled.hline(0, HEIGHT-10, WIDTH, 1)
        oled.show()
        
        joy = read_joystick()
        if joy == "UP" and selected > 0:
            selected -= 1
            time.sleep_ms(200)
        elif joy == "DOWN" and selected < len(options)-1:
            selected += 1
            time.sleep_ms(200)
        
        if is_select_pressed():
            if selected == 0:
                # 进入WiFi设置
                settings_wifi()
            elif selected == 1:
                # 进入时间设置
                settings_time()
            elif selected == 2:
                # 返回桌面
                IS_DESKTOP = True
                return
            time.sleep_ms(200)
        
        time.sleep_ms(50)

# WiFi设置界面
def settings_wifi():
    global CURRENT_SCREEN, wifi_ssids, wifi_selected, wifi_scroll, wifi_password
    
    CURRENT_SCREEN = "wifi"
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    # 初始扫描WiFi
    if not wifi_ssids:
        scan_wifi()
    
    while CURRENT_SCREEN == "wifi":
        oled.fill(0)
        oled.text("WIFI SETUP", 25, 5)
        
        # 显示WiFi列表（带滚动）
        visible_count = 3  # 一屏显示3个
        start_idx = wifi_scroll
        end_idx = min(start_idx + visible_count, len(wifi_ssids))
        
        for i in range(start_idx, end_idx):
            pos = i - start_idx
            if i == wifi_selected:
                oled.fill_rect(10, 20 + pos*12, 108, 10, 1)
                ssid_text = wifi_ssids[i][:12]  # 限制长度
                oled.text(ssid_text, 15, 21 + pos*12, 0)
            else:
                oled.rect(10, 20 + pos*12, 108, 10, 1)
                ssid_text = wifi_ssids[i][:12]
                oled.text(ssid_text, 15, 21 + pos*12)
        
        # 底部操作提示
        oled.text("SEL:OK  FIRE:SCAN", 5, HEIGHT-9)
        oled.hline(0, HEIGHT-10, WIDTH, 1)
        oled.show()
        
        joy = read_joystick()
        if joy == "UP":
            if wifi_selected > 0:
                wifi_selected -= 1
                if wifi_selected < wifi_scroll:
                    wifi_scroll = wifi_selected
                time.sleep_ms(200)
        elif joy == "DOWN":
            if wifi_selected < len(wifi_ssids) - 1:
                wifi_selected += 1
                if wifi_selected >= wifi_scroll + visible_count:
                    wifi_scroll += 1
                time.sleep_ms(200)
        
        # 扫描WiFi
        if is_fire_pressed():
            scan_wifi()
            time.sleep_ms(500)
        
        # 选择WiFi
        if is_select_pressed():
            if wifi_ssids:
                selected_ssid = wifi_ssids[wifi_selected]
                wifi_password = ""
                settings_wifi_password(selected_ssid)
            time.sleep_ms(200)
        
        time.sleep_ms(50)

# 扫描WiFi
def scan_wifi():
    global wifi_ssids, wifi_selected, wifi_scroll
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    networks = wlan.scan()
    
    # 提取SSID并去重
    ssids = []
    seen = set()
    for net in networks:
        ssid = net[0].decode('utf-8')
        if ssid not in seen:
            seen.add(ssid)
            ssids.append(ssid)
    
    # 按SSID排序
    wifi_ssids = sorted(ssids)
    wifi_selected = 0
    wifi_scroll = 0

# WiFi密码输入界面
def settings_wifi_password(ssid):
    global CURRENT_SCREEN, wifi_password, wifi_keyboard_pos, keyboard_page
    
    CURRENT_SCREEN = "wifi_pwd"
    wifi_keyboard_pos = 0
    keyboard_page = 0
    
    while CURRENT_SCREEN == "wifi_pwd":
        oled.fill(0)
        oled.text("WIFI PWD", 30, 5)
        
        # 显示SSID
        oled.text(f"SSID:{ssid[:10]}", 5, 15)
        
        # 显示密码（用*表示）
        pwd_display = "*" * len(wifi_password) if wifi_password else "NONE"
        oled.text(f"PWD:{pwd_display}", 5, 25)
        
        # 显示当前页的键盘
        start = keyboard_page * 18
        end = start + 18
        page_chars = keyboard_chars[start:end]
        
        # 排列键盘（3行6列）
        for i, c in enumerate(page_chars):
            row = i // 6
            col = i % 6
            x = 10 + col * 20
            y = 40 + row * 8
            
            if i + start == wifi_keyboard_pos:
                oled.fill_rect(x, y, 15, 7, 1)
                oled.text(c, x + 3, y + 1, 0)
            else:
                oled.rect(x, y, 15, 7, 1)
                oled.text(c, x + 3, y + 1)
        
        # 页码指示器
        oled.text(f"{keyboard_page+1}/{keyboard_pages}", WIDTH-30, 35)
        
        # 底部提示
        oled.text("SEL:ENT  FIRE:DEL", 5, HEIGHT-9)
        oled.hline(0, HEIGHT-10, WIDTH, 1)
        oled.show()
        
        joy = read_joystick()
        if joy == "LEFT" and wifi_keyboard_pos > start:
            wifi_keyboard_pos -= 1
            time.sleep_ms(150)
        elif joy == "RIGHT" and wifi_keyboard_pos < min(end - 1, len(keyboard_chars) - 1):
            wifi_keyboard_pos += 1
            time.sleep_ms(150)
        elif joy == "UP":
            if wifi_keyboard_pos - 6 >= start:
                wifi_keyboard_pos -= 6
                time.sleep_ms(150)
            elif keyboard_page > 0:
                # 上一页
                keyboard_page -= 1
                wifi_keyboard_pos = start - 1
                time.sleep_ms(150)
        elif joy == "DOWN":
            if wifi_keyboard_pos + 6 < end and wifi_keyboard_pos + 6 < len(keyboard_chars):
                wifi_keyboard_pos += 6
                time.sleep_ms(150)
            elif keyboard_page < keyboard_pages - 1:
                # 下一页
                keyboard_page += 1
                wifi_keyboard_pos = start + 18
                time.sleep_ms(150)
        
        # 删除字符
        if is_fire_pressed():
            if wifi_password:
                wifi_password = wifi_password[:-1]
            time.sleep_ms(200)
        
        # 确认输入
        if is_select_pressed():
            if wifi_keyboard_pos < len(keyboard_chars):
                # 输入字符
                if len(wifi_password) < 16:  # 限制密码长度
                    wifi_password += keyboard_chars[wifi_keyboard_pos]
            else:
                # 连接WiFi
                connect_wifi(ssid, wifi_password)
                CURRENT_SCREEN = "wifi"
            time.sleep_ms(200)
        
        time.sleep_ms(50)

# 连接WiFi
def connect_wifi(ssid, password):
    oled.fill(0)
    oled.text("CONNECTING", 25, 25)
    oled.show()
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(ssid, password)
        
        # 等待连接（最多10秒）
        timeout = 100
        while not wlan.isconnected() and timeout > 0:
            time.sleep_ms(100)
            timeout -= 1
        
        if wlan.isconnected():
            oled.fill(0)
            oled.text("CONNECTED", 25, 25)
            oled.show()
            time.sleep(1)
            
            # 获取NTP时间
            try:
                ntptime.settime()
                oled.fill(0)
                oled.text("TIME UPDATED", 15, 25)
                oled.show()
                time.sleep(1)
            except:
                oled.fill(0)
                oled.text("TIME FAIL", 25, 25)
                oled.show()
                time.sleep(1)
        else:
            oled.fill(0)
            oled.text("FAILED", 35, 25)
            oled.show()
            time.sleep(1)

# 时间设置界面
def settings_time():
    global CURRENT_SCREEN, time_edit_pos, time_values
    
    # 初始化时间为当前时间
    try:
        t = rtc.datetime()
        time_values = [
            t[4] // 10, t[4] % 10,  # 小时
            t[5] // 10, t[5] % 10,  # 分钟
            t[6] // 10, t[6] % 10   # 秒钟
        ]
    except:
        time_values = [0, 0, 0, 0, 0, 0]
    
    CURRENT_SCREEN = "time"
    
    while CURRENT_SCREEN == "time":
        oled.fill(0)
        oled.text("TIME SETUP", 25, 5)
        
        # 显示时间格式: HH:MM:SS
        time_str = f"{time_values[0]}{time_values[1]}:{time_values[2]}{time_values[3]}:{time_values[4]}{time_values[5]}"
        oled.text(time_str, 30, 25)
        
        # 显示光标
        cursor_pos = [30, 36, 42, 48, 54, 60]  # 每个数字的x坐标
        oled.fill_rect(cursor_pos[time_edit_pos], 35, 5, 1, 1)
        
        # 底部提示
        oled.text("UP/DOWN:VAL", 5, HEIGHT-9)
        oled.text("LEFT/RIGHT:POS", 60, HEIGHT-9)
        oled.hline(0, HEIGHT-10, WIDTH, 1)
        oled.show()
        
        joy = read_joystick()
        if joy == "LEFT" and time_edit_pos > 0:
            time_edit_pos -= 1
            time.sleep_ms(200)
        elif joy == "RIGHT" and time_edit_pos < 5:
            time_edit_pos += 1
            time.sleep_ms(200)
        elif joy == "UP":
            # 增加数值
            max_vals = [2, 9, 5, 9, 5, 9]  # 每个位置的最大值
            if time_edit_pos == 0 and time_values[0] == 2:
                max_vals[1] = 3  # 小时十位为2时，个位最大3
            else:
                max_vals[1] = 9
                
            if time_values[time_edit_pos] < max_vals[time_edit_pos]:
                time_values[time_edit_pos] += 1
            else:
                time_values[time_edit_pos] = 0
            time.sleep_ms(150)
        elif joy == "DOWN":
            # 减少数值
            if time_values[time_edit_pos] > 0:
                time_values[time_edit_pos] -= 1
            else:
                max_vals = [2, 9, 5, 9, 5, 9]
                if time_edit_pos == 0 and time_values[0] == 0:
                    max_vals[1] = 9
                elif time_edit_pos == 0 and time_values[0] == 2:
                    max_vals[1] = 3
                time_values[time_edit_pos] = max_vals[time_edit_pos]
            time.sleep_ms(150)
        
        # 保存时间设置
        if is_select_pressed():
            try:
                # 转换为实际时间值
                hour = time_values[0] * 10 + time_values[1]
                minute = time_values[2] * 10 + time_values[3]
                second = time_values[4] * 10 + time_values[5]
                
                # 获取当前日期
                t = rtc.datetime()
                
                # 设置新时间（年, 月, 日, 星期, 时, 分, 秒, 微秒）
                rtc.datetime((t[0], t[1], t[2], t[3], hour, minute, second, 0))
                
                oled.fill(0)
                oled.text("SAVED", 35, 25)
                oled.show()
                time.sleep(1)
            except:
                oled.fill(0)
                oled.text("SAVE FAIL", 25, 25)
                oled.show()
                time.sleep(1)
            
            CURRENT_SCREEN = "main"
            time.sleep_ms(200)
        
        time.sleep_ms(50)

# 主程序
def main():
    global SELECTED_ICON, IS_DESKTOP, CURRENT_GAME
    
    # 启动界面
    startup_screen()
    
    # 进入桌面
    IS_DESKTOP = True
    last_input = time.ticks_ms()
    
    while True:
        if IS_DESKTOP:
            draw_desktop()
            
            # 读取摇杆
            joy = read_joystick()
            if joy == "LEFT" and time.ticks_ms() - last_input > 300:
                SELECTED_ICON = (SELECTED_ICON - 1) % GAMES
                last_input = time.ticks_ms()
            elif joy == "RIGHT" and time.ticks_ms() - last_input > 300:
                SELECTED_ICON = (SELECTED_ICON + 1) % GAMES
                last_input = time.ticks_ms()
            elif joy == "UP" and time.ticks_ms() - last_input > 300:
                # 上移
                if SELECTED_ICON >= 5:
                    SELECTED_ICON -= 5
                last_input = time.ticks_ms()
            elif joy == "DOWN" and time.ticks_ms() - last_input > 300:
                # 下移
                if SELECTED_ICON <= 3:
                    SELECTED_ICON += 5
                last_input = time.ticks_ms()
            
            # 选择游戏或设置
            if is_select_pressed():
                IS_DESKTOP = False
                if SELECTED_ICON == 0:
                    snake_game()
                elif SELECTED_ICON == 1:
                    dino_game()
                elif SELECTED_ICON == 2:
                    plane_game()
                elif SELECTED_ICON == 3:
                    tetris_game()
                elif SELECTED_ICON == 4:
                    sokoban_game()
                elif SELECTED_ICON == 5:
                    calculator_game()
                elif SELECTED_ICON == 6:
                    catch_game()
                elif SELECTED_ICON == 7:
                    racing_game()
                elif SELECTED_ICON == 8:
                    settings_main()  # 进入设置界面
                while is_select_pressed():
                    time.sleep_ms(50)
        
        time.sleep_ms(50)

if __name__ == "__main__":
    main()


