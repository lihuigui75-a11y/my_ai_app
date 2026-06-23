import sqlite3
import streamlit as st
from datetime import datetime, timedelta

DB_PATH = "users.db"

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'user',
            credits INTEGER DEFAULT 3,
            membership_type TEXT DEFAULT 'free',
            credits_expire_date TEXT,
            registration_ip TEXT,
            is_banned INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            amount INTEGER,
            balance INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recharge_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            package_name TEXT,
            amount INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_user_credits(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT credits, credits_expire_date FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row['credits']
    return 0

def update_user_credits(username, amount):
    conn = get_db()
    cursor = conn.cursor()
    current = get_user_credits(username)
    new_balance = max(0, current + amount)
    cursor.execute("UPDATE users SET credits = ? WHERE username = ?", (new_balance, username))
    cursor.execute("INSERT INTO credit_logs (username, action, amount, balance) VALUES (?, ?, ?, ?)",
                   (username, "consume" if amount < 0 else "add", amount, new_balance))
    conn.commit()
    conn.close()
    return new_balance

def reset_all_monthly_credits():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET credits = 0 WHERE role = 'user'")
    conn.commit()
    conn.close()

def get_registration_ip(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT registration_ip FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row['registration_ip'] if row else None

def count_registrations_from_ip(ip):
    if not ip:
        return 0
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE registration_ip = ?", (ip,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def ban_user(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned = 1 WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def unban_user(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned = 0 WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def is_user_banned(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT is_banned FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row and row['is_banned'] == 1

def get_all_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, email, role, credits, membership_type, is_banned, created_at FROM users ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_credit_logs(username=None):
    conn = get_db()
    cursor = conn.cursor()
    if username:
        cursor.execute("SELECT * FROM credit_logs WHERE username = ? ORDER BY created_at DESC LIMIT 50", (username,))
    else:
        cursor.execute("SELECT * FROM credit_logs ORDER BY created_at DESC LIMIT 100")
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_recharge_request(username, package_name, amount):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO recharge_requests (username, package_name, amount, status) VALUES (?, ?, ?, ?)",
                   (username, package_name, amount, 'pending'))
    conn.commit()
    conn.close()

def get_pending_recharge_requests():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recharge_requests WHERE status = 'pending' ORDER BY created_at ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def approve_recharge_request(request_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, amount FROM recharge_requests WHERE id = ?", (request_id,))
    req = cursor.fetchone()
    if req:
        username = req['username']
        amount = req['amount']
        update_user_credits(username, amount)
        cursor.execute("UPDATE recharge_requests SET status = 'approved' WHERE id = ?", (request_id,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False
