import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'app.db')

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

MODEL_GROUPS = {
    "domestic": {
        "models": [
            "ideogram/V_2_TURBO", "ideogram/V_2", "ideogram/V_3",
            "ideogram/V_2_A", "ideogram/V_2_A_TURBO",
            "ideogram/V_1", "ideogram/V_1_TURBO"
        ],
        "cost": 1,
    },
    "foreign": {
        "models": ["openai/dall-e-3"],
        "cost": 2,
    }
}

PACKAGES = {
    "周包 (7天)": {"points": 100, "valid_days": 7, "price": 12},
    "月包 (30天)": {"points": 500, "valid_days": 30, "price": 50},
    "季包 (90天)": {"points": 1500, "valid_days": 90, "price": 120},
    "年包 (365天)": {"points": 6000, "valid_days": 365, "price": 400},
}

def get_model_cost(model_name):
    for group in MODEL_GROUPS.values():
        if model_name in group['models']:
            return group['cost']
    return 1

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            credits INTEGER DEFAULT 3,
            role TEXT DEFAULT 'user',
            banned INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS orders (
            out_trade_no TEXT PRIMARY KEY,
            username TEXT,
            package_name TEXT,
            points INTEGER,
            price REAL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS credits_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            change INTEGER,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        INSERT OR IGNORE INTO users VALUES ('admin','admin123',999,'admin',0);
        INSERT OR IGNORE INTO users VALUES ('user','user123',3,'user',0);
        INSERT OR IGNORE INTO settings VALUES ('site_title','🎨 阳雯科技 · AI 图像生成器平台');
        INSERT OR IGNORE INTO settings VALUES ('home_custom_text','选择一种生成模式开始创作，新用户赠送3积分！');
        INSERT OR IGNORE INTO settings VALUES ('admin_qq','158261755');
        INSERT OR IGNORE INTO settings VALUES ('danmu_list','[]');
        INSERT OR IGNORE INTO settings VALUES ('registration_enabled','1');
        INSERT OR IGNORE INTO settings VALUES ('qr_image_bytes','');
    ''')
    conn.commit()
    conn.close()

def get_user(username):
    conn = get_db()
    row = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(username, password):
    conn = get_db()
    try:
        conn.execute('INSERT INTO users (username,password) VALUES (?,?)', (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_all_users():
    conn = get_db()
    rows = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_user(username, data):
    conn = get_db()
    sets = ', '.join([f"{k}=?" for k in data.keys()])
    vals = list(data.values()) + [username]
    conn.execute(f'UPDATE users SET {sets} WHERE username=?', vals)
    conn.commit()
    conn.close()

def get_credits(username):
    user = get_user(username)
    return user['credits'] if user else 0

def set_credits(username, amount):
    update_user(username, {'credits': amount})

def add_credits(username, amount):
    conn = get_db()
    conn.execute('UPDATE users SET credits=credits+? WHERE username=?', (amount, username))
    conn.execute('INSERT INTO credits_log (username,change,reason) VALUES (?,?,?)',
                 (username, amount, '充值' if amount>0 else '消费'))
    conn.commit()
    conn.close()

def deduct_credits(username, amount):
    if get_credits(username) >= amount:
        add_credits(username, -amount)
        return True
    return False

def is_user_banned(username):
    user = get_user(username)
    return user['banned'] == 1 if user else False

def create_order(out_trade_no, username, package_name, points, price):
    conn = get_db()
    conn.execute('INSERT INTO orders (out_trade_no,username,package_name,points,price) VALUES (?,?,?,?,?)',
                 (out_trade_no, username, package_name, points, price))
    conn.commit()
    conn.close()

def update_order_status(out_trade_no, status):
    conn = get_db()
    conn.execute('UPDATE orders SET status=? WHERE out_trade_no=?', (status, out_trade_no))
    conn.commit()
    conn.close()

def get_order(out_trade_no):
    conn = get_db()
    row = conn.execute('SELECT * FROM orders WHERE out_trade_no=?', (out_trade_no,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_setting(key, default=None):
    conn = get_db()
    row = conn.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    conn.close()
    return row['value'] if row else default

def set_setting(key, value):
    conn = get_db()
    conn.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, str(value)))
    conn.commit()
    conn.close()
