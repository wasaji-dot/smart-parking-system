import pygame
import sys
import json
import os
import hashlib

# ---------------- 全国省份简称 ----------------
PROVINCES = ["京","沪","粤","苏","浙","鲁","川","渝","冀","晋","辽","吉","黑","皖","闽","赣","豫","鄂","湘","琼","贵","云","陕","甘","青","蒙","桂","藏","宁","新"]

# ---------------- 字体 ----------------
def create_font(size=24):
    try:
        return pygame.font.Font("C:/Windows/Fonts/simhei.ttf", size)
    except:
        return pygame.font.Font(None, size)

# ---------------- 加密 ----------------
def encrypt(password):
    return hashlib.md5(password.encode()).hexdigest()

# ---------------- 读取用户 ----------------
def load_users():
    USER_FILE = "users.json"
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------- 保存用户 ----------------
def save_users(users):
    USER_FILE = "users.json"
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

# ---------------- 注册（自动拼车牌） ----------------
def register(username, password, province, plate):
    users = load_users()

    if username in users:
        return False, "账户已存在"

    # ✅ 关键：账号是 admin → 自动设为管理员
    if username == "admin":
        role = "admin"
        full_plate = ""  # 管理员不需要车牌
    else:
        role = "user"
        full_plate = province + plate  # 普通用户自动拼车牌

    users[username] = {
        "password": encrypt(password),
        "role": role,
        "plate": full_plate
    }

    save_users(users)
    return True, "注册成功"

# ---------------- 登录（返回角色） ----------------
def login(username, password):
    users = load_users()
    if username in users:
        if users[username]["password"] == encrypt(password):
            return True, users[username]["role"]
    return False, None

# ---------------- 输入框 ----------------
class InputBox:
    def __init__(self, x, y, w, h, font, is_password=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = ""
        self.active = False
        self.font = font
        self.is_password = is_password

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                self.active = False
            else:
                char = event.unicode
                if char.isalnum():
                    self.text += char

    def draw(self, screen):
        pygame.draw.rect(screen, (255,255,255), self.rect)
        show = "*"*len(self.text) if self.is_password else self.text
        surf = self.font.render(show, True, (0,0,0))
        screen.blit(surf, (self.rect.x+5, self.rect.y+5))
        pygame.draw.rect(screen, (0,0,0), self.rect, 2)

# ---------------- 按钮 ----------------
class Button:
    def __init__(self, x, y, w, h, text, font):
        self.rect = pygame.Rect(x,y,w,h)
        self.text = text
        self.font = font

    def draw(self, screen):
        pygame.draw.rect(screen, (0,128,255), self.rect)
        txt = self.font.render(self.text, True, (255,255,255))
        screen.blit(txt, txt.get_rect(center=self.rect.center))

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos)

# ---------------- 登录主界面 ----------------
def run_login():
    pygame.init()
    pygame.font.init()
    w, h = 600, 400
    screen = pygame.display.set_mode((w, h))
    pygame.display.set_caption("登录")
    font = create_font(24)
    small_font = create_font(18)

    username_ipt = InputBox(200,100,220,40, font)
    password_ipt = InputBox(200,160,220,40, font, is_password=True)
    plate_ipt = InputBox(270,220,150,40, font)
    province_btn = Button(200,220,60,40, "粤", font)
    login_btn = Button(150,290,110,45, "登录", font)
    reg_btn = Button(340,290,110,45, "注册", font)

    show_plate = False
    msg = ""
    clock = pygame.time.Clock()

    while True:
        screen.fill((255,255,255))
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            username_ipt.handle_event(e)
            password_ipt.handle_event(e)
            if show_plate:
                plate_ipt.handle_event(e)

            # 登录
            if login_btn.is_clicked(e):
                show_plate = False
                u = username_ipt.text.strip()
                p = password_ipt.text.strip()
                if not u or not p:
                    msg = "账号密码不能为空"
                else:
                    ok, role = login(u, p)
                    if ok:
                        pygame.quit()
                        return (u, role)
                    else:
                        msg = "账号或密码错误"

            # 注册
            if reg_btn.is_clicked(e):
                show_plate = True
                u = username_ipt.text.strip()
                p = password_ipt.text.strip()
                pl = plate_ipt.text.strip()
                if not u or not p:
                    msg = "账号密码不能为空"
                elif not pl:
                    msg = "车牌不能为空"
                else:
                    ok, msg = register(u, p, province_btn.text, pl)

            # 切换省份
            if province_btn.is_clicked(e):
                idx = PROVINCES.index(province_btn.text)
                province_btn.text = PROVINCES[(idx+1)%len(PROVINCES)]

        # 绘制
        title = font.render("停车场管理系统",True,(0,0,0))
        screen.blit(title, (w//2-title.get_width()//2, 30))
        screen.blit(font.render("账号:",True,(0,0,0)), (130,110))
        screen.blit(font.render("密码:",True,(0,0,0)), (130,170))

        username_ipt.draw(screen)
        password_ipt.draw(screen)
        login_btn.draw(screen)
        reg_btn.draw(screen)

        if show_plate:
            screen.blit(font.render("车牌:",True,(0,0,0)), (130,230))
            province_btn.draw(screen)
            plate_ipt.draw(screen)

        if msg:
            c = (255,0,0) if "错误" in msg or "不能为空" in msg or "已存在" in msg else (0,180,0)
            ms = small_font.render(msg, True, c)
            screen.blit(ms, (w//2-ms.get_width()//2, 350))

        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    run_login()