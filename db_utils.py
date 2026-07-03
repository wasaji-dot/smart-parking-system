import sqlite3
import os
import pandas as pd
import sys
import traceback


def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_db_path(db_filename="parking.db"):
    db_path = get_resource_path(db_filename)
    print(f"📂 数据库文件路径：{db_path}")
    print(f"✅ 路径是否存在：{os.path.exists(db_path)}")
    return db_path


def connect_db(db_filename="parking.db"):
    db_path = get_db_path(db_filename)
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        return conn, cursor
    except Exception as e:
        print(f"❌ 数据库连接失败：{str(e)}")
        exit()


def init_tables_safe(cursor):
    """安全创建表，并兼容旧库自动增加 slot_id 列"""
    cursor.execute('''  
    CREATE TABLE IF NOT EXISTS ParkingVehicles ( 
        id INTEGER PRIMARY KEY AUTOINCREMENT,  
        carnumber TEXT NOT NULL,  
        date TEXT,  
        price REAL, 
        state INTEGER  
    )
    ''')
    try:
        cursor.execute("ALTER TABLE ParkingVehicles ADD COLUMN slot_id TEXT")
        print("✅ 已为 ParkingVehicles 表添加 slot_id 列")
    except sqlite3.OperationalError:
        pass

    cursor.execute('''  
    CREATE TABLE IF NOT EXISTS ParkingInfo (  
        id INTEGER PRIMARY KEY AUTOINCREMENT,  
        carnumber TEXT NOT NULL,  
        date TEXT,  
        price REAL,  
        state INTEGER  
    )
    ''')
    try:
        cursor.execute("ALTER TABLE ParkingInfo ADD COLUMN slot_id TEXT")
        print("✅ 已为 ParkingInfo 表添加 slot_id 列")
    except sqlite3.OperationalError:
        pass

    print("\n✅ 表结构初始化完成")


def import_excel_to_db(excel_info_path, excel_vehicle_path, db_filename="parking.db"):
    """导入Excel数据到数据库（加入了详细报错打印和空值过滤）"""
    conn, cursor = connect_db(db_filename)
    try:
        # 1. 导入信息表（历史记录）
        if os.path.exists(excel_info_path):
            info_df = pd.read_excel(excel_info_path)
            if 'slot_id' not in info_df.columns:
                info_df['slot_id'] = None
            info_df.to_sql('ParkingInfo', conn, if_exists='append', index=False)
            print(f"✅ 导入停车场信息表 {len(info_df)} 条数据")

        # 2. 导入车辆表（当前停车）
        if os.path.exists(excel_vehicle_path):
            vehicle_df = pd.read_excel(excel_vehicle_path)

            # 🟢 核心修复：过滤掉车牌号为空的行，避免 NOT NULL 约束报错
            before_len = len(vehicle_df)
            vehicle_df = vehicle_df.dropna(subset=['carnumber'])
            dropped = before_len - len(vehicle_df)
            if dropped > 0:
                print(f"⚠️ 发现并自动过滤了 {dropped} 行车牌号为空的无效数据")

            if 'slot_id' not in vehicle_df.columns:
                vehicle_df['slot_id'] = None

            vehicle_df.to_sql('ParkingVehicles', conn, if_exists='append', index=False)
            print(f"✅ 导入停车场车辆表 {len(vehicle_df)} 条数据")

        conn.commit()
    except Exception as e:
        conn.rollback()
        print("\n" + "=" * 50)
        print("❌ 导入Excel失败！具体原因如下：")
        print("-" * 50)
        traceback.print_exc()
        print("=" * 50 + "\n")
    finally:
        conn.close()


def query_existing_data(table_name, cursor, limit=10):
    try:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        data = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        print(f"\n📊 表【{table_name}】前{limit}条数据：")
        print(" | ".join(columns))
        print("-" * 50)
        for row in data:
            print(" | ".join(map(str, row)))
        return data
    except Exception as e:
        print(f"❌ 查询 {table_name} 失败：{e}")
        return []