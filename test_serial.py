"""
串口通信测试 - 上位机
功能：发送指令给Arduino，测试通信是否正常
"""

import serial
import serial.tools.list_ports
import time


def auto_find_arduino():
    """自动查找Arduino端口"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        print(f"发现端口: {port.device} - {port.description}")
        if 'Arduino' in port.description or 'USB' in port.description:
            return port.device
    return None


def send_command(ser, cmd, wait_time=1):
    """发送指令并等待响应"""
    print(f"\n📤 发送: {cmd}")
    ser.write((cmd + '\n').encode('utf-8'))
    time.sleep(wait_time)

    # 读取所有响应
    while ser.in_waiting > 0:
        line = ser.readline().decode('utf-8').strip()
        if line:
            print(f"📥 收到: {line}")


def main():
    # 1. 查找Arduino端口
    port = auto_find_arduino()
    if port is None:
        print("❌ 未找到Arduino，请检查USB连接")
        return

    print(f"\n✅ 找到Arduino: {port}")

    # 2. 连接串口
    try:
        ser = serial.Serial(port, 115200, timeout=2)
        time.sleep(2)  # 等待Arduino复位
        print(f"✅ 串口连接成功\n")
    except Exception as e:
        print(f"❌ 串口连接失败: {e}")
        return

    # 3. 发送测试指令
    print("=" * 50)
    print("开始串口通信测试")
    print("=" * 50)

    # 测试1: PING
    send_command(ser, "PING")

    # 测试2: 点亮LED1
    send_command(ser, "LED:1,ON")

    # 测试3: LED1闪烁
    send_command(ser, "LED:1,BLINK")

    # 测试4: 熄灭LED1
    send_command(ser, "LED:1,OFF")

    # 测试5: 蜂鸣器
    send_command(ser, "BUZZER:200")

    # 测试6: 入口舵机
    send_command(ser, "SERVO_IN:90")
    time.sleep(1)
    send_command(ser, "SERVO_IN:0")

    # 测试7: 出口舵机
    send_command(ser, "SERVO_OUT:90")
    time.sleep(1)
    send_command(ser, "SERVO_OUT:0")

    # 测试8: 状态查询
    send_command(ser, "STATUS")

    # 4. 关闭串口
    print("\n" + "=" * 50)
    print("测试完成，关闭串口")
    ser.close()


if __name__ == "__main__":
    main()