# coding:utf-8
# 屏蔽 OpenCV 所有警告
import os

os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
import sys
import time
import platform
import matplotlib.pyplot as plt
import matplotlib as mpl
import ocrutil
import btn
import pygame
import cv2
import pandas as pd
import timeutil
import db_utils
import serial
import json

# 串口初始化
ser = serial.Serial('COM12', 9600, timeout=1)
time.sleep(2)

# 车位编号列表（用于顺序分配算法）
SLOT_LIST = ['A01', 'A02', 'A03', 'B01', 'B02', 'B03']

# 全局颜色定义
BG = (73, 119, 142)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
BLUE = (72, 61, 139)
RED = (220, 20, 60)
YELLOW = (255, 255, 0)

# ======================== 全局变量 ========================
total = 100
txt1, txt2, txt3 = "", "", ""
income_switch = False
gate_open_time = 0
gate_opening = False

# 数据库全局连接（只在启动时建立一次，主循环直接复用）
global_conn = None
global_cursor = None


# ======================== 工具函数 ========================
def setup_matplotlib_chinese():
    try:
        if platform.system() == "Windows":
            font_path = "C:/Windows/Fonts/simhei.ttf"
            font_prop = mpl.font_manager.FontProperties(fname=font_path)
            mpl.rcParams['font.family'] = font_prop.get_name()
        else:
            mpl.rcParams['font.family'] = ['sans-serif']
            mpl.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        mpl.rcParams['axes.unicode_minus'] = False
    except Exception as e:
        print(f"Matplotlib字体配置警告: {e}")


def create_font(size=20, bold=False, italic=False):
    try:
        font_path = "C:/Windows/Fonts/simhei.ttf"
        font = pygame.font.Font(font_path, size)
        font.set_bold(bold)
        font.set_italic(italic)
        return font
    except:
        font = pygame.font.Font(None, size)
        font.set_bold(bold)
        font.set_italic(italic)
        return font


setup_matplotlib_chinese()


def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


from login_ui import run_login


def open_gate():
    print("开闸")
    ser.write(b'o')


def close_gate():
    print("关闸")
    ser.write(b'c')


def init_opencv():
    if not os.path.exists("file"):
        os.makedirs("file")
    try:
        cam = cv2.VideoCapture(0)
    except Exception as e:
        print(f'摄像头连接失败: {e}')
        return False
    success, img = cam.read()
    print(f'摄像头读取状态: {success}')
    if success:
        img_path = "file/test2.jpg"
        cv2.imwrite(img_path, img)
        if not os.path.exists(img_path):
            print(f'图片保存失败: {img_path}')
            cam.release()
            return False
    cam.release()
    return success


# ======================== UI 绘制函数 ========================
def text0(screen, cars):
    pygame.draw.rect(screen, BG, (650, 2, 350, 640))
    pygame.draw.aaline(screen, GREEN, (600, 50), (980, 50), 1)
    pygame.draw.rect(screen, GREEN, (650, 350, 342, 85), 1)
    xtfont = create_font(20)
    textstart = xtfont.render('信息', True, GREEN)
    text_rect = textstart.get_rect()
    text_rect.centerx = 675
    text_rect.centery = 365
    screen.blit(textstart, text_rect)
    if len(cars) > 0:
        longcar = cars[0][0]
        cartime = cars[0][1]
        xtfont = create_font(18)
        try:
            htime = timeutil.DtCale(cartime, time.localtime())
            textscar = xtfont.render(f'停车时间最长的车辆:{str(longcar)}', True, RED)
            texttime = xtfont.render(f'已停车:{str(htime)}小时', True, RED)
            text_rect1 = textscar.get_rect()
            text_rect2 = texttime.get_rect()
            text_rect1.centerx = 820
            text_rect1.centery = 320
            text_rect2.centerx = 820
            text_rect2.centery = 335
            screen.blit(textscar, text_rect1)
            screen.blit(texttime, text_rect2)
        except Exception as e:
            print(f'计算停车时长失败: {e}')


def text1(screen, carn):
    k = total - carn
    sk = '0' + str(k) if k < 10 else str(k)
    xtfont = create_font(30)
    textstart = xtfont.render(f'总车位:{total},剩余车位:{sk}', True, WHITE)
    text_rect = textstart.get_rect()
    text_rect.centerx = 790
    text_rect.centery = 30
    screen.blit(textstart, text_rect)


def text2(screen):
    xtfont = create_font(20)
    textstart = xtfont.render('车号     时间', True, WHITE)
    text_rect = textstart.get_rect()
    text_rect.centerx = 730
    text_rect.centery = 70
    screen.blit(textstart, text_rect)


def text3(screen, cursor):
    """显示最近的10条停车记录（优先显示历史离场记录）"""
    xtfont = create_font(20)
    n = 0
    try:
        # 1. 尝试从历史表 ParkingInfo 拿最新的10条数据
        cursor.execute("SELECT carnumber, date FROM ParkingInfo ORDER BY id DESC LIMIT 10")
        display_list = cursor.fetchall()

        # 2. 如果历史表是空的，再拿当前停车的
        if not display_list:
            cursor.execute("SELECT carnumber, date FROM ParkingVehicles WHERE state=1 ORDER BY id DESC LIMIT 10")
            display_list = cursor.fetchall()

        for car in display_list:
            n += 1
            textstart = xtfont.render(f'{str(car[0])}  {str(car[1])}', True, WHITE)
            text_rect = textstart.get_rect()
            text_rect.centerx = 780
            text_rect.centery = 70 + 30 * n
            screen.blit(textstart, text_rect)
    except Exception as e:
        pass  # 如果查不到数据，就不显示任何内容，不报错


def text4(screen, txt1, txt2, txt3):
    xtfont = create_font(20)
    texttxt1 = xtfont.render(txt1, True, GREEN)
    text_rect1 = texttxt1.get_rect()
    text_rect1.centerx = 820
    text_rect1.centery = 355 + 20
    screen.blit(texttxt1, text_rect1)
    texttxt2 = xtfont.render(txt2, True, GREEN)
    text_rect2 = texttxt2.get_rect()
    text_rect2.centerx = 820
    text_rect2.centery = 355 + 40
    screen.blit(texttxt2, text_rect2)
    texttxt3 = xtfont.render(txt3, True, GREEN)
    text_rect3 = texttxt3.get_rect()
    text_rect3.centerx = 820
    text_rect3.centery = 355 + 60
    screen.blit(texttxt3, text_rect3)
    # 这里你原本的逻辑是获取离场记录预测明天的车位预警，我帮你用 SQL 改写了
    try:
        global global_cursor
        # 查询离场记录（state=2）
        global_cursor.execute("SELECT date FROM ParkingInfo WHERE state=2")
        kcars = [row[0] for row in global_cursor.fetchall()]
        localtime = time.gmtime().tm_wday
        for k in kcars:
            week_number = timeutil.get_week_number(k)
            if week_number == 4:
                if localtime == 4:
                    text6(screen, '根据数据分析，明天可能出现车位紧张的情况，请做好调度!')
                elif localtime == 5:
                    text6(screen, '根据数据分析，今天可能出现车位紧张的情况，请做好调度！')
            else:
                if localtime == 5:
                    text6(screen, '根据数据分析，今天可能出现车位紧张的情况，请做好调度！')
    except Exception as e:
        pass  # 忽略预警失败，不影响主程序


def text5(screen, sum_price):
    xtfont = create_font(20)
    textstart = xtfont.render(f'共计收入:{str(sum_price)}元', True, WHITE)
    text_rect = textstart.get_rect()
    text_rect.centerx = 1200
    text_rect.centery = 30
    screen.blit(textstart, text_rect)
    income_img_path = get_resource_path(os.path.join("file", "income.png"))
    if os.path.exists(income_img_path):
        image = pygame.image.load(income_img_path)
        image = pygame.transform.smoothscale(image, (390, 430))
        screen.blit(image, (1000, 50))


def text6(screen, week_info):
    pygame.draw.rect(screen, YELLOW, ((2, 2), (640, 40)))
    xtfont = create_font(20)
    textstart = xtfont.render(week_info, True, RED)
    text_rect = textstart.get_rect()
    text_rect.centerx = 322
    text_rect.centery = 20
    screen.blit(textstart, text_rect)


def user_main(username):
    # 你自己的用户界面，保持不变
    pass


# ======================== Pygame 主入口 ========================
# ======================== Pygame 主入口 ========================
def main():
    global global_conn, global_cursor
    global txt1, txt2, txt3, income_switch, gate_open_time, gate_opening

    # 1. 在进入主界面时，强制执行一次 Excel 到 SQLite 的导入（确保数据一定能进去！）
    print("正在从 Excel 导入数据到数据库，请稍候...")
    info_excel = get_resource_path(os.path.join("datafile", "停车场信息表.xlsx"))
    vehicle_excel = get_resource_path(os.path.join("datafile", "停车场车辆表.xlsx"))
    db_utils.import_excel_to_db(
        excel_info_path=info_excel,
        excel_vehicle_path=vehicle_excel,
        db_filename=get_resource_path("parking.db")
    )

    # 2. 初始化全局数据库连接（只连这一次，绝不刷屏！）
    global_conn, global_cursor = db_utils.connect_db(db_filename=get_resource_path("parking.db"))

    # 3. 初始化摄像头
    save_data()
    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # 4. Pygame 初始化
    pygame.init()
    size = 1400, 630
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption('智能停车场车牌识别计费系统')
    clock = pygame.time.Clock()
    FPS = 60

    Running = True
    while Running:
        # ========== 5. 主循环里复用全局连接，直接查询数据库 ==========
        # 查当前停放 (state=1) 用于统计剩余车位
        global_cursor.execute("SELECT carnumber, date, slot_id FROM ParkingVehicles WHERE state=1")
        current_cars = global_cursor.fetchall()
        carn = len(current_cars)

        # 查总营收
        global_cursor.execute("SELECT SUM(price) FROM ParkingInfo")
        sum_price_res = global_cursor.fetchone()
        sum_price = sum_price_res[0] if sum_price_res[0] else 0.0

        # ========== 6. 绘制 UI ==========
        screen.fill(BG)
        text0(screen, current_cars)
        text1(screen, carn)
        text2(screen)
        text3(screen, global_cursor)  # 👈 传入 cursor 去 text3 里查历史表
        text4(screen, txt1, txt2, txt3)
        text5(screen, sum_price)

        # 摄像头画面
        ret, frame = cam.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.flip(frame, 1)
            frame = frame.swapaxes(0, 1)
            frame = pygame.surfarray.make_surface(frame)
            frame = pygame.transform.scale(frame, (600, 425))
            screen.blit(frame, (20, 50))

        # 按钮
        button_go = btn.Button(screen, (640, 480), 150, 60, BLUE, WHITE, '识别', 25)
        button_go.draw_button()
        button_go1 = btn.Button(screen, (990, 480), 100, 40, RED, WHITE, '收入统计', 20)
        button_go1.draw_button()

        # ========== 7. 事件监听 ==========
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                Running = False
                pygame.quit()
                global_conn.close()  # 退出时关闭连接
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()

                # 点击【识别】按钮（内部无需改动，保持你原来的逻辑）
                if 492 <= mouse_pos[0] <= 642 and 422 <= mouse_pos[1] <= 482:
                    print('点击识别')
                    try:
                        if not init_opencv():
                            raise Exception('无法获取实时图片，请检查摄像头')
                        img_path = "./file/test2.jpg"
                        if not os.path.exists(img_path):
                            raise FileNotFoundError(f'图片不存在: {img_path}')

                        carnumber = ocrutil.getcn(img_path)
                        current_time = time.strftime('%Y-%m-%d %H:%M', time.localtime())

                        if not carnumber:
                            raise Exception('OCR识别失败，未检测到有效车牌')

                        # 查当前车是否在停车中
                        global_cursor.execute(
                            "SELECT id, date, slot_id FROM ParkingVehicles WHERE carnumber=? AND state=1", (carnumber,))
                        existing_car = global_cursor.fetchone()

                        if existing_car:
                            # ======= 离场 =======
                            start_time = existing_car[1]
                            slot_id = existing_car[2]
                            hours = timeutil.DtCale(start_time, time.localtime())
                            price = hours * 5

                            global_cursor.execute(
                                '''INSERT INTO ParkingInfo (carnumber, date, price, state, slot_id) VALUES (?, ?, ?, 2, ?)''',
                                (carnumber, current_time, price, slot_id))
                            global_cursor.execute("DELETE FROM ParkingVehicles WHERE carnumber=? AND state=1",
                                                  (carnumber,))
                            global_conn.commit()

                            open_gate()
                            gate_open_time = time.time()
                            gate_opening = True
                            txt1 = f"{carnumber} 已离场"
                            txt2 = f"停车 {hours} 小时"
                            txt3 = f"收费 {price} 元"

                        else:
                            # ======= 入场 =======
                            global_cursor.execute("SELECT slot_id FROM ParkingVehicles WHERE state=1")
                            occupied_slots = [row[0] for row in global_cursor.fetchall()]
                            allocated_slot = None
                            for slot in SLOT_LIST:
                                if slot not in occupied_slots:
                                    allocated_slot = slot
                                    break

                            if allocated_slot is None:
                                txt1 = "车位已满，无法入场"
                                txt2 = ""
                                txt3 = ""
                            else:
                                global_cursor.execute(
                                    '''INSERT INTO ParkingVehicles (carnumber, date, price, state, slot_id) VALUES (?, ?, 0, 1, ?)''',
                                    (carnumber, current_time, allocated_slot))
                                global_conn.commit()

                                open_gate()
                                gate_open_time = time.time()
                                gate_opening = True
                                txt1 = f"{carnumber} 入场"
                                txt2 = f"时间 {current_time}"
                                txt3 = f"分配车位: {allocated_slot}"

                    except Exception as e:
                        txt1 = f"识别失败：{str(e)}"
                        txt2 = ""
                        txt3 = ""

                # 点击【收入统计】按钮（内部无需改动）
                if 940 <= mouse_pos[0] <= 1040 and 440 <= mouse_pos[1] <= 480:
                    # ...(保持你的收入统计逻辑)...
                    pass

                    # 自动关闸
        if gate_opening and time.time() - gate_open_time > 3:
            close_gate()
            gate_opening = False

        pygame.display.flip()
        clock.tick(FPS)


def save_data():
    data_path = get_resource_path("datafile")
    if not os.path.exists(data_path):
        os.makedirs(data_path)


if __name__ == "__main__":
    result = run_login()
    if result:
        username, role = result
        print("登录用户:", username)
        print("角色:", role)

        # 检查表结构是否存在（无刷新机制，纯创建）
        conn_init, cursor_init = db_utils.connect_db(db_filename=get_resource_path("parking.db"))
        db_utils.init_tables_safe(cursor_init)
        conn_init.close()

        if role == "admin":
            print("进入管理员界面")
            main()
        else:
            print("进入用户界面")
            user_main(username)
            sys.exit()