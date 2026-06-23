import streamlit as st
from utils.database import init_db, get_credits, is_user_banned, get_setting
from utils.payment import PACKAGES, create_payment_order, generate_pay_url, verify_payment
import time

init_db()
st.set_page_config(page_title='个人中心', page_icon='👤')
if not st.session_state.get('authenticated'):
    st.warning('⚠️ 请先登录')
    st.stop()
username = st.session_state.username
if is_user_banned(username):
    st.error('⛔ 账户已封禁')
    st.stop()

st.title('👤 个人中心')
st.subheader(f'用户名：{username}')
st.metric('💰 当前积分', get_credits(username))

st.subheader('📦 充值套餐（周/月/季/年）')
pkg_names = list(PACKAGES.keys())
selected_pkg = st.selectbox('选择套餐', pkg_names)
pkg_info = PACKAGES[selected_pkg]
st.markdown(f'**{selected_pkg}**：{pkg_info["points"]} 积分，有效期 {pkg_info["valid_days"]} 天，价格 **{pkg_info["price"]} 元**')

# 收款二维码
st.subheader('📱 收款二维码')
qr_data = get_setting('qr_image_bytes', '')
if qr_data:
    import base64
    try:
        st.image(base64.b64decode(qr_data), caption='请扫码支付', width=200)
    except:
        st.warning('收款码数据损坏，请联系管理员')
else:
    st.warning('⚠️ 收款二维码未上传，请联系管理员')

# 支付按钮
if 'pay_url' not in st.session_state:
    st.session_state.pay_url = ''
if 'out_trade_no' not in st.session_state:
    st.session_state.out_trade_no = ''

if st.button('💸 创建支付宝订单'):
    out_trade_no = create_payment_order(username, selected_pkg, pkg_info['points'], pkg_info['price'])
    pay_url = generate_pay_url(out_trade_no, pkg_info['price'], f'阳雯科技-{selected_pkg}')
    if pay_url:
        st.session_state.pay_url = pay_url
        st.session_state.out_trade_no = out_trade_no
        st.success('订单已创建，请点击链接支付')
    else:
        st.error('支付服务未配置，请联系管理员')

if st.session_state.pay_url:
    st.markdown(f'[点击跳转到支付宝支付]({st.session_state.pay_url})')

if st.session_state.out_trade_no:
    if st.button('✅ 查询支付结果'):
        if verify_payment(st.session_state.out_trade_no):
            st.success('支付成功，积分已到账！')
            st.balloons()
            st.session_state.pay_url = ''
            st.session_state.out_trade_no = ''
            time.sleep(1)
            st.rerun()
        else:
            st.warning('支付尚未完成，请完成付款后再查询')

# 充值记录
st.subheader('📋 充值记录')
from utils.database import get_db
conn = get_db()
orders = conn.execute('SELECT * FROM orders WHERE username=? ORDER BY created_at DESC', (username,)).fetchall()
conn.close()
if orders:
    for o in orders:
        st.write(f"{o['package_name']} - {o['points']}积分 - {o['price']}元 - {o['status']}")
else:
    st.info('暂无记录')
