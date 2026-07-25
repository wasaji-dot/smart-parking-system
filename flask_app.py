# flask_app.py
import sqlite3
from flask import Flask, request, jsonify, render_template_string

DB_PATH = 'parking.db'
app = Flask(__name__)


def get_db(timeout=10):
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    conn.row_factory = sqlite3.Row
    # 开启 WAL 模式，提高并发性能
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


# ============================================================
# 首页 - 反向寻车页面（添加了 @app.route('/')）
# ============================================================
@app.route('/')
def index():
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>智能停车场 - 反向寻车</title>
        <style>
            body { font-family: "Microsoft YaHei", Arial; text-align: center; background: #f0f2f5; margin-top: 80px;}
            .container { background: white; width: 500px; margin: 0 auto; padding: 40px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            input { padding: 12px; width: 70%; border: 1px solid #ccc; border-radius: 6px; font-size: 16px; }
            button { padding: 12px 20px; background: #49778e; color: white; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; }
            button:hover { background: #3a5f72; }
            #result { margin-top: 30px; padding: 15px; border-radius: 6px; font-size: 18px; }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .loading { background: #cce5ff; color: #004085; border: 1px solid #b8daff; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2 style="color: #333;">🔍 反向寻车系统</h2>
            <p style="color: #666; margin-bottom: 20px;">请输入您的车牌号，查询车辆停放位置</p>
            <div>
                <input type="text" id="plate" placeholder="例如：粤K98A25">
                <button onclick="search()">立即查询</button>
            </div>
            <div id="result"></div>
        </div>

        <script>
        async function search() {
            const plate = document.getElementById('plate').value.trim();
            const resDiv = document.getElementById('result');
            resDiv.className = '';

            if(!plate) { 
                resDiv.innerHTML = '⚠️ 请输入车牌号'; 
                resDiv.className = 'error';
                return; 
            }

            resDiv.innerHTML = '⏳ 查询中...';
            resDiv.className = 'loading';

            try {
                const resp = await fetch(`/api/search?plate=${encodeURIComponent(plate)}`);
                const data = await resp.json();
                if(data.success) {
                    resDiv.innerHTML = `✅ 查询成功！<br><br>
                                        👉 您的爱车 <b>${data.plate}</b><br>
                                        👉 停在 <b style="color: red; font-size: 24px;">${data.slot}</b> 号车位<br>
                                        <small style="color: #666;">入场时间: ${data.entry_time}</small>`;
                    resDiv.className = 'success';
                } else {
                    resDiv.innerHTML = `❌ ${data.msg}`;
                    resDiv.className = 'error';
                }
            } catch(e) {
                resDiv.innerHTML = '❌ 网络请求失败，请重试';
                resDiv.className = 'error';
            }
        }

        // 回车键触发查询
        document.getElementById('plate').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') search();
        });
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)


# ============================================================
# 反向寻车 API（增加重试机制）
# ============================================================
@app.route('/api/search', methods=['GET'])
def search_car():
    plate = request.args.get('plate', '').strip()
    if not plate:
        return jsonify({'success': False, 'msg': '请输入车牌号'})

    # 重试3次，防止 database is locked
    for attempt in range(3):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute('SELECT carnumber, slot_id, date FROM ParkingVehicles WHERE carnumber = ? AND state = 1',
                        (plate,))
            row = cur.fetchone()

            if row:
                # 插入指令到 Commands 表
                cur.execute('INSERT INTO Commands (action, slot, status) VALUES (?, ?, 0)',
                            ('LED_BLINK', row['slot_id']))
                conn.commit()
                conn.close()
                return jsonify({
                    'success': True,
                    'plate': row['carnumber'],
                    'slot': row['slot_id'],
                    'entry_time': row['date']
                })
            else:
                conn.close()
                return jsonify({'success': False, 'msg': '未找到该车辆，或车辆已离场'})

        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e) and attempt < 2:
                import time
                time.sleep(0.5)  # 等待0.5秒后重试
                continue
            else:
                return jsonify({'success': False, 'msg': f'数据库繁忙，请稍后重试'})
        except Exception as e:
            return jsonify({'success': False, 'msg': f'查询失败: {str(e)}'})


# ============================================================
# 启动 Flask 服务
# ============================================================
if __name__ == '__main__':
    # 确保 Commands 表存在
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS Commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            slot TEXT,
            status INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("🚀 Flask 反向寻车服务已启动！请在浏览器访问: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)