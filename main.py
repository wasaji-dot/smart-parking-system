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
import threading

# ============================================================
# 一、串口通信类（新协议）
# ============================================================
class SerialComm:
    """串口通信类 - 新协议（字符串指令，以\\n结尾）"""

    def __init__(self, port=None, baudrate=115200):
        self.ser = None
        self.is_connected = False
        self.running = False
        self.received_data = []
        self.callbacks = {
            'IR_IN': [],
            'IR_OUT': [],
            'RFID_UID': [],
            'SLOT_STATUS': [],
            'ENTRY_OK': [],
            'ENTRY_FULL': [],
            'EXIT_PAID': [],
            'EXIT_FREE': [],
            'FIND_OK': [],
            'PONG': [],
        }

        if port is None:
            self.auto_connect(baudrate)
        else:
            self.connect(port, baudrate)

    def auto_connect(self, baudrate=115200):
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if 'Arduino' in port.description or 'USB' in port.description:
                if self.connect(port.device, baudrate):
                    print(f"✅ 串口连接成功: {port.device}")
                    return True
        print("❌ 未找到Arduino，请检查USB连接")
        return False

    def connect(self, port, baudrate=115200):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            time.sleep(2)
            self.is_connected = True
            self.running = True
            self.thread = threading.Thread(target=self._receive_loop)
            self.thread.daemon = True
            self.thread.start()
            print(f"✅ 串口已连接: {port} (波特率: {baudrate})")
            return True
        except Exception as e:
            print(f"❌ 串口连接失败: {e}")
            return False

    def _receive_loop(self):
        while self.running and self.is_connected:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:
                        self.received_data.append(line)
                        self._dispatch(line)
            except:
                pass
            time.sleep(0.01)

    def _dispatch(self, line):
        """解析串口数据并触发回调"""
        if line == "IR_IN":
            for cb in self.callbacks.get('IR_IN', []):
                cb()
        elif line == "IR_OUT":
            for cb in self.callbacks.get('IR_OUT', []):
                cb()
        elif line.startswith("RFID_UID:"):
            uid = line[9:]
            for cb in self.callbacks.get('RFID_UID', []):
                cb(uid)
        elif line.startswith("SLOT_STATUS:"):
            parts = line[12:].split(',')
            if len(parts) == 2:
                status = parts[0]
                available = int(parts[1])
                for cb in self.callbacks.get('SLOT_STATUS', []):
                    cb(status, available)
        elif line.startswith("ENTRY_OK:"):
            parts = line[9:].split(',')
            if len(parts) == 2:
                plate = parts[0]
                slot = parts[1]
                for cb in self.callbacks.get('ENTRY_OK', []):
                    cb(plate, slot)
        elif line == "ENTRY_FULL":
            for cb in self.callbacks.get('ENTRY_FULL', []):
                cb()
        elif line.startswith("EXIT_PAID:"):
            parts = line[10:].split(',')
            if len(parts) == 2:
                plate = parts[0]
                fee = int(parts[1])
                for cb in self.callbacks.get('EXIT_PAID', []):
                    cb(plate, fee)
        elif line.startswith("EXIT_FREE:"):
            plate = line[10:]
            for cb in self.callbacks.get('EXIT_FREE', []):
                cb(plate)
        elif line.startswith("FIND_OK:"):
            slot = int(line[8:])
            for cb in self.callbacks.get('FIND_OK', []):
                cb(slot)
        elif line == "PONG":
            for cb in self.callbacks.get('PONG', []):
                cb()
        elif line == "READY":
            print("Arduino 已就绪")

    def on(self, event, callback):
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def send(self, command):
        if not self.is_connected:
            print("串口未连接")
            return False
        try:
            self.ser.write((command + '\n').encode('utf-8'))
            print(f"发送: {command}")
            return True
        except Exception as e:
            print(f"发送失败: {e}")
            return False

    def control_servo_in(self, angle):
        self.send(f"SERVO_IN:{angle}")

    def control_servo_out(self, angle):
        self.send(f"SERVO_OUT:{angle}")

    def close(self):
        self.running = False
        if self.ser:
            self.ser.close()
            self.is_connected = False


# ============================================================
# 二、初始化串口
# ============================================================
ser_comm = SerialComm()
if not ser_comm.is_connected:
    print("⚠️ 串口未连接，系统将工作在离线模式")

SLOT_LIST = ['A01', 'A02', 'A03', 'B01', 'B02', 'B03']

BG = (73, 119, 142)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
BLUE = (72, 61, 139)
RED = (220, 20, 60)
YELLOW = (255, 255, 0)

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


# ============================================================
# 三、开闸/关闸函数（新协议）
# ============================================================
def open_gate(plate=None):
    if ser_comm.is_connected:
        if plate:
            ser_comm.send(f"ENTRY_PLATE:{plate}")
        else:
            ser_comm.send("ENTRY_PLATE:自动识别")
    else:
        print("⚠️ 离线模式：模拟开闸")


def open_gate_exit(plate, fee):
    if ser_comm.is_connected:
        ser_comm.send(f"EXIT_PLATE:{plate},{fee}")
    else:
        print(f"⚠️ 离线模式：模拟离场 {plate} 收费 {fee} 元")


def find_car(slot_num):
    if ser_comm.is_connected:
        ser_comm.send(f"FIND_CAR:{slot_num}")
    else:
        print(f"⚠️ 离线模式：模拟寻车 A0{slot_num}")


def stop_find():
    if ser_comm.is_connected:
        ser_comm.send("STOP_FIND")


def ping_arduino():
    if ser_comm.is_connected:
        ser_comm.send("PING")
        return True
    return False


def close_gate():
    print("关闸（新协议自动处理）")


ser = None


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
    xtfont = create_font(20)
    n = 0
    try:
        cursor.execute("SELECT carnumber, date FROM ParkingInfo ORDER BY id DESC LIMIT 10")
        display_list = cursor.fetchall()
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
        pass


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
    try:
        global global_cursor
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
        pass


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
        image = pygame.transform.smoothscale(image, (550, 480))
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
    pass


# ============================================================
# 红外自动触发回调函数
# ============================================================
auto_mode = True


def on_ir_in():
    global txt1, txt2, txt3, global_conn, global_cursor
    print("🚗 入口红外触发，启动车牌识别...")

    if not auto_mode:
        print("⏸️ 自动识别模式已关闭")
        return

    try:
        if not init_opencv():
            raise Exception('无法获取实时图片')
        img_path = "./file/test2.jpg"
        if not os.path.exists(img_path):
            raise FileNotFoundError('图片不存在')

        carnumber = ocrutil.getcn(img_path)
        current_time = time.strftime('%Y-%m-%d %H:%M', time.localtime())

        if not carnumber:
            raise Exception('OCR识别失败')

        # 直接使用全局连接，不新建
        global_cursor.execute(
            "SELECT id, date, slot_id FROM ParkingVehicles WHERE carnumber=? AND state=1",
            (carnumber,))
        existing_car = global_cursor.fetchone()

        if existing_car:
            txt1 = f"{carnumber} 已在场内"
            txt2 = ""
            txt3 = ""
            print(f"⚠️ {carnumber} 已在场内")
            return

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
            print("❌ 车位已满")
            return

        global_cursor.execute(
            '''INSERT INTO ParkingVehicles (carnumber, date, price, state, slot_id) VALUES (?, ?, 0, 1, ?)''',
            (carnumber, current_time, allocated_slot))
        global_conn.commit()

        ser_comm.send(f"ENTRY_PLATE:{carnumber}")
        time.sleep(0.5)
        ser_comm.control_servo_in(90)
        time.sleep(3.0)
        ser_comm.control_servo_in(0)

        txt1 = f"🚗 {carnumber} 入场"
        txt2 = f"车位: {allocated_slot}"
        txt3 = f"时间: {current_time}"
        print(f"✅ {carnumber} 入场 -> {allocated_slot}")

    except Exception as e:
        txt1 = f"识别失败: {str(e)}"
        txt2 = ""
        txt3 = ""
        print(f"❌ 识别失败: {e}")


def on_ir_out():
    global txt1, txt2, txt3, global_conn, global_cursor
    print("🚗 出口红外触发，启动车牌识别...")

    if not auto_mode:
        print("⏸️ 自动识别模式已关闭")
        return

    try:
        if not init_opencv():
            raise Exception('无法获取实时图片')
        img_path = "./file/test2.jpg"
        if not os.path.exists(img_path):
            raise FileNotFoundError('图片不存在')

        carnumber = ocrutil.getcn(img_path)
        current_time = time.strftime('%Y-%m-%d %H:%M', time.localtime())

        if not carnumber:
            raise Exception('OCR识别失败')

        global_cursor.execute(
            "SELECT id, date, slot_id FROM ParkingVehicles WHERE carnumber=? AND state=1",
            (carnumber,))
        existing_car = global_cursor.fetchone()

        if not existing_car:
            txt1 = f"{carnumber} 未找到入场记录"
            txt2 = ""
            txt3 = ""
            print(f"⚠️ {carnumber} 未找到入场记录")
            return

        start_time = existing_car[1]
        slot_id = existing_car[2]
        hours = timeutil.DtCale(start_time, time.localtime())
        price = hours * 5

        global_cursor.execute(
            '''INSERT INTO ParkingInfo (carnumber, date, price, state, slot_id) VALUES (?, ?, ?, 2, ?)''',
            (carnumber, current_time, price, slot_id))
        global_cursor.execute("DELETE FROM ParkingVehicles WHERE carnumber=? AND state=1", (carnumber,))
        global_conn.commit()

        ser_comm.send(f"EXIT_PLATE:{carnumber},{price}")
        time.sleep(0.5)
        ser_comm.control_servo_out(90)
        time.sleep(3.0)
        ser_comm.control_servo_out(0)

        txt1 = f"🚗 {carnumber} 离场"
        txt2 = f"停车 {hours} 小时"
        txt3 = f"收费 {price} 元"
        print(f"✅ {carnumber} 离场，收费 {price} 元")

    except Exception as e:
        txt1 = f"识别失败: {str(e)}"
        txt2 = ""
        txt3 = ""
        print(f"❌ 识别失败: {e}")


# ============================================================
# main() 主函数（参照旧版：全局连接，不刷屏）
# ============================================================
def main():
    global global_conn, global_cursor
    global txt1, txt2, txt3, income_switch, gate_open_time, gate_opening

    # 1. 导入 Excel 数据
    print("正在从 Excel 导入数据到数据库，请稍候...")
    info_excel = get_resource_path(os.path.join("datafile", "停车场信息表.xlsx"))
    vehicle_excel = get_resource_path(os.path.join("datafile", "停车场车辆表.xlsx"))
    db_utils.import_excel_to_db(
        excel_info_path=info_excel,
        excel_vehicle_path=vehicle_excel,
        db_filename=get_resource_path("parking.db")
    )

    # 2. 建立全局数据库连接（只连一次！）
    global_conn, global_cursor = db_utils.connect_db(db_filename=get_resource_path("parking.db"))

    # 3. 注册红外事件回调
    ser_comm.on('IR_IN', on_ir_in)
    ser_comm.on('IR_OUT', on_ir_out)
    print("✅ 红外联动已开启，红外触发将自动识别车牌")

    # 4. 初始化摄像头
    save_data()
    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # 5. Pygame 初始化
    pygame.init()
    size = 1400, 630
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption('智能停车场车牌识别计费系统')
    clock = pygame.time.Clock()
    FPS = 60

    # 6. 定时器用于处理数据库指令（反向寻车）
    last_cmd_check = 0

    Running = True
    while Running:
        # ========== 使用全局连接查询数据库 ==========
        global_cursor.execute("SELECT carnumber, date, slot_id FROM ParkingVehicles WHERE state=1")
        current_cars = global_cursor.fetchall()
        carn = len(current_cars)

        global_cursor.execute("SELECT SUM(price) FROM ParkingInfo")
        sum_price_res = global_cursor.fetchone()
        sum_price = sum_price_res[0] if sum_price_res[0] else 0.0

        # ========== 硬件指令监听模块（反向寻车） ==========
        now = pygame.time.get_ticks()
        if now - last_cmd_check > 1000:
            try:
                global_cursor.execute("SELECT id, action, slot FROM Commands WHERE status=0 ORDER BY id ASC LIMIT 1")
                cmd = global_cursor.fetchone()
                if cmd:
                    cmd_id, action, slot = cmd
                    if action == 'LED_BLINK':
                        if slot is not None and len(slot) > 1:
                            slot_num = int(slot[1:])
                            ser_comm.send(f"FIND_CAR:{slot_num}")
                            print(f"✅ 硬件指令已执行: 寻车 {slot}")
                        else:
                            print(f"⚠️ 反向寻车指令缺少有效的车位编号: slot={slot}")
                    global_cursor.execute("UPDATE Commands SET status=1 WHERE id=?", (cmd_id,))
                    global_conn.commit()
            except Exception as e:
                print(f"❌ 处理硬件指令时出错: {e}")
            last_cmd_check = now

        # ========== 绘制 UI ==========
        screen.fill(BG)
        text0(screen, current_cars)
        text1(screen, carn)
        text2(screen)
        text3(screen, global_cursor)
        text4(screen, txt1, txt2, txt3)
        text5(screen, sum_price)

        ret, frame = cam.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.flip(frame, 1)
            frame = frame.swapaxes(0, 1)
            frame = pygame.surfarray.make_surface(frame)
            frame = pygame.transform.scale(frame, (600, 425))
            screen.blit(frame, (20, 50))

        button_go = btn.Button(screen, (640, 480), 150, 60, BLUE, WHITE, '识别', 25)
        button_go.draw_button()
        button_go1 = btn.Button(screen, (990, 480), 100, 40, RED, WHITE, '收入统计', 20)
        button_go1.draw_button()

        # ========== 事件监听 ==========
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                Running = False
                pygame.quit()
                global_conn.close()
                ser_comm.close()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()

                if 492 <= mouse_pos[0] <= 642 and 422 <= mouse_pos[1] <= 482:
                    print('手动点击识别')
                    try:
                        if not init_opencv():
                            raise Exception('无法获取实时图片')
                        img_path = "./file/test2.jpg"
                        if not os.path.exists(img_path):
                            raise FileNotFoundError(f'图片不存在: {img_path}')

                        carnumber = ocrutil.getcn(img_path)
                        current_time = time.strftime('%Y-%m-%d %H:%M', time.localtime())

                        if not carnumber:
                            raise Exception('OCR识别失败')

                        global_cursor.execute(
                            "SELECT id, date, slot_id FROM ParkingVehicles WHERE carnumber=? AND state=1",
                            (carnumber,))
                        existing_car = global_cursor.fetchone()

                        if existing_car:
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

                            ser_comm.send(f"EXIT_PLATE:{carnumber},{price}")
                            time.sleep(0.5)
                            ser_comm.control_servo_out(90)
                            time.sleep(1.5)
                            ser_comm.control_servo_out(0)

                            txt1 = f"{carnumber} 已离场"
                            txt2 = f"停车 {hours} 小时"
                            txt3 = f"收费 {price} 元"
                        else:
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

                                ser_comm.send(f"ENTRY_PLATE:{carnumber}")
                                time.sleep(0.5)
                                ser_comm.control_servo_in(90)
                                time.sleep(1.5)
                                ser_comm.control_servo_in(0)

                                txt1 = f"{carnumber} 入场"
                                txt2 = f"时间 {current_time}"
                                txt3 = f"分配车位: {allocated_slot}"

                    except Exception as e:
                        txt1 = f"识别失败：{str(e)}"
                        txt2 = ""
                        txt3 = ""

                if 940 <= mouse_pos[0] <= 1040 and 440 <= mouse_pos[1] <= 480:
                    income_switch = not income_switch
                    income_img_path = get_resource_path(os.path.join("file", "income.png"))
                    if os.path.exists(income_img_path):
                        os.remove(income_img_path)
                    if income_switch:
                        try:
                            global_cursor.execute("SELECT date, price FROM ParkingInfo")
                            rows = global_cursor.fetchall()
                            if rows:
                                df = pd.DataFrame(rows, columns=['date', 'price'])
                                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                                df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
                                daily_income = df.groupby(df['date'].dt.date)['price'].sum()
                                today = pd.Timestamp.today().date()
                                if today not in daily_income.index:
                                    daily_income.loc[today] = 0
                                daily_income = daily_income.sort_index()
                                plt.figure(figsize=(12, 7))
                                daily_income.plot(kind='bar')
                                plt.title('停车场日收入统计', fontsize=24)
                                plt.xlabel('日期', fontsize=16)
                                plt.ylabel('收入（元）', fontsize=16)
                                plt.xticks(rotation=30, fontsize=16)
                                plt.tight_layout()
                                plt.savefig(income_img_path, dpi=120)
                                plt.close()
                                txt1 = "收入统计已生成"
                            else:
                                txt1 = "暂无收入数据"
                        except Exception as e:
                            txt1 = f"生成统计失败: {str(e)}"
                    else:
                        txt1 = "收入统计已隐藏"

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