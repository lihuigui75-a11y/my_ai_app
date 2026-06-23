import streamlit as st
from alipay import AliPay
import uuid
from utils.database import create_order, update_order_status, get_order, add_credits, PACKAGES

def _fix_key(key, key_type='private'):
    """如果密钥没有 PEM 头尾，自动添加"""
    if not key:
        return key
    key = key.strip()
    if key_type == 'private':
        if not key.startswith('-----BEGIN'):
            key = "-----BEGIN RSA PRIVATE KEY-----\n" + key + "\n-----END RSA PRIVATE KEY-----"
    elif key_type == 'public':
        if not key.startswith('-----BEGIN'):
            key = "-----BEGIN PUBLIC KEY-----\n" + key + "\n-----END PUBLIC KEY-----"
    return key

def get_alipay_client():
    app_id = st.secrets.get('ALIPAY_APP_ID', '')
    private_key = _fix_key(st.secrets.get('ALIPAY_PRIVATE_KEY', ''), 'private')
    alipay_public_key = _fix_key(st.secrets.get('ALIPAY_PUBLIC_KEY', ''), 'public')
    if not app_id:
        return None
    return AliPay(
        appid=app_id,
        app_notify_url=None,
        app_private_key_string=private_key,
        alipay_public_key_string=alipay_public_key,
        sign_type='RSA2',
        debug=False   # 测试环境改为 True，正式环境 False
    )

def generate_pay_url(out_trade_no, total_amount, subject):
    alipay = get_alipay_client()
    if not alipay:
        return None
    order_string = alipay.api_alipay_trade_page_pay(
        out_trade_no=out_trade_no,
        total_amount=float(total_amount),
        subject=subject,
        return_url=None,
        notify_url=None
    )
    return f'https://openapi.alipay.com/gateway.do?{order_string}'

def create_payment_order(username, package_name, points, price):
    out_trade_no = f'YW{username}_{uuid.uuid4().hex[:8]}'
    create_order(out_trade_no, username, package_name, points, price)
    return out_trade_no

def verify_payment(out_trade_no):
    alipay = get_alipay_client()
    if not alipay:
        return False
    result = alipay.api_alipay_trade_query(out_trade_no=out_trade_no)
    if result.get('trade_status') == 'TRADE_SUCCESS':
        order = get_order(out_trade_no)
        if order and order['status'] == 'pending':
            add_credits(order['username'], order['points'])
            update_order_status(out_trade_no, 'paid')
            return True
    return False