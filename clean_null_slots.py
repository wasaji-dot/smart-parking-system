# coding:utf-8
"""
批量清理脚本：删除所有 slot_id 为 NULL 的无效车辆记录
使用方法：运行 python clean_null_slots.py
"""

import sqlite3
import os


def get_resource_path(relative_path):
    """获取文件路径"""
    return os.path.join(os.path.dirname(__file__), relative_path)


def clean_null_slots():
    """清理所有 slot_id 为 NULL 的车辆记录"""
    db_path = get_resource_path("parking.db")

    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 查看当前有多少条无效记录
    cursor.execute("SELECT id, carnumber, slot_id, state FROM ParkingVehicles WHERE slot_id IS NULL")
    null_records = cursor.fetchall()

    if not null_records:
        print("✅ 没有找到 slot_id 为 NULL 的车辆记录，无需清理")
        conn.close()
        return

    print(f"⚠️ 找到 {len(null_records)} 条无效记录：")
    print("-" * 50)
    for row in null_records:
        print(f"  ID: {row[0]}, 车牌: {row[1]}, slot_id: {row[2]}, state: {row[3]}")
    print("-" * 50)

    # 2. 确认是否删除
    confirm = input(f"\n是否删除以上 {len(null_records)} 条记录？(y/n): ")
    if confirm.lower() != 'y':
        print("❌ 已取消操作")
        conn.close()
        return

    # 3. 执行删除
    try:
        cursor.execute("DELETE FROM ParkingVehicles WHERE slot_id IS NULL")
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"✅ 成功删除 {deleted_count} 条无效记录")
    except Exception as e:
        print(f"❌ 删除失败: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    clean_null_slots()