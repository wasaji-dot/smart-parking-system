# flask_app.py
import sqlite3
from flask import Flask, request, jsonify, render_template_string

# 注意：这个路径必须和你的 main.py 里的路径完全一致
DB_PATH = "parking.db"

app = Flask(__name__)


# 连接数据库函数
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 支持按列名获取数据
    return conn


# =========== 核心接口：反向寻车 ===========
@app.route('/api/search', methods=['GET'])
def search_car():
    plate = request.args.get('plate', '').strip()
    if not plate:
        return jsonify({'success': False, 'msg': '请输入车牌号'})

    conn = get_db()
    # 查询当前还在停车场内的车辆 (state=1)
    cur = conn.cursor()
    cur.execute('''
        SELECT carnumber, slot_id, date 
        FROM ParkingVehicles 
        WHERE carnumber = ? AND state = 1
    ''', (plate,))
    row = cur.fetchone()
    conn.close()

    if row:
        # 🟢 Web端查询成功！

        # 1. 向数据库 Commands 表发送一条触发硬件的指令
        conn_ins = sqlite3.connect(DB_PATH)
        cur_ins = conn_ins.cursor()
        cur_ins.execute("INSERT INTO Commands (action, slot, status) VALUES (?, ?, 0)",
                        ('LED_BLINK', row['slot_id']))  # 写入指令：LED闪烁，目标车位是 row['slot_id']
        conn_ins.commit()
        conn_ins.close()

        # 2. 服务端控制台打印（供你答辩时看日志用）
        print(f"\n【🔥 硬件触发指令已写入数据库】")
        print(f"用户查询到车牌：{plate}，Web端将控制 {row['slot_id']} 车位 LED 闪烁 + 蜂鸣器 30 秒")

        # 3. 返回 JSON 给前端
        return jsonify({
            'success': True,
            'plate': row['carnumber'],
            'slot': row['slot_id'],
            'entry_time': row['date']
        })

# =========== 前端页面（HTML/CSS/JS） ===========
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
            const plate = document.getElementById('plate').value;
            const resDiv = document.getElementById('result');
            resDiv.className = '';
            if(!plate) { 
                resDiv.innerHTML = '⚠️ 请输入车牌号'; 
                resDiv.className = 'error';
                return; 
            }

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
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)


if __name__ == '__main__':
    print("🚀 Flask 反向寻车服务已启动！请在浏览器访问: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)