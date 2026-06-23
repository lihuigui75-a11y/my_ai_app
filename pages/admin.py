import streamlit as st
import pandas as pd
from utils.database import init_db, get_all_users, add_credits, update_user, is_user_banned, PACKAGES, get_setting, set_setting
import json
import base64

init_db()
st.set_page_config(page_title='后台管理', page_icon='🛡️')
if not st.session_state.get('authenticated') or st.session_state.role != 'admin':
    st.error('⛔ 无权访问')
    st.stop()

st.title('🛡️ 后台管理')
tabs = st.tabs(['👥 用户管理', '💵 充值审核', '💬 弹幕管理', '📝 首页文案', '📱 收款码'])

with tabs[0]:
    st.subheader('所有用户')
    users = get_all_users()
    if users:
        df = pd.DataFrame(users)[['username','credits','role','banned']]
        st.dataframe(df)
    target = st.text_input('输入目标用户名', key='admin_target').strip()
    col1, col2 = st.columns(2)
    with col1:
        if st.button('➕ 增加 10 积分'):
            if target and get_user(target):
                add_credits(target, 10)
                st.success(f'已为 {target} 增加 10 积分')
            else:
                st.error('用户不存在')
    with col2:
        if st.button('🚫 封禁/解封'):
            if target and get_user(target):
                banned = is_user_banned(target)
                update_user(target, {'banned': 0 if banned else 1})
                st.success(f'已{"解封" if banned else "封禁"} {target}')
            else:
                st.error('用户不存在')

with tabs[1]:
    st.subheader('待审核充值')
    from utils.database import get_db
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders WHERE status='pending'").fetchall()
    conn.close()
    if not orders:
        st.info('暂无待审核订单')
    else:
        for o in orders:
            st.write(f"{o['username']} - {o['package_name']} - {o['points']}积分 - {o['price']}元")
            if st.button('✅ 手动到账', key=f"manual_{o['out_trade_no']}"):
                add_credits(o['username'], o['points'])
                from utils.database import update_order_status
                update_order_status(o['out_trade_no'], 'paid')
                st.rerun()

with tabs[2]:
    st.subheader('弹幕管理')
    danmu_raw = get_setting('danmu_list', '[]')
    try:
        danmu_list = json.loads(danmu_raw)
    except:
        danmu_list = []
    if danmu_list:
        for idx, dm in enumerate(danmu_list):
            col_dm, col_del = st.columns([4,1])
            with col_dm:
                st.text(f'{idx+1}. {dm}')
            with col_del:
                if st.button('🗑️', key=f'del_{idx}'):
                    danmu_list.pop(idx)
                    set_setting('danmu_list', json.dumps(danmu_list, ensure_ascii=False))
                    st.rerun()
    new_dm = st.text_input('输入新弹幕内容').strip()
    if st.button('📤 添加弹幕'):
        if new_dm:
            danmu_list.append(new_dm)
            set_setting('danmu_list', json.dumps(danmu_list, ensure_ascii=False))
            st.success('弹幕已添加')
            st.rerun()

with tabs[3]:
    st.subheader('自定义首页内容')
    new_text = st.text_area('欢迎文案', value=get_setting('home_custom_text', ''))
    reg_enabled = st.checkbox('允许新用户注册', value=(get_setting('registration_enabled','1')=='1'))
    if st.button('💾 保存设置'):
        set_setting('home_custom_text', new_text)
        set_setting('registration_enabled', '1' if reg_enabled else '0')
        st.success('设置已更新！')

with tabs[4]:
    st.subheader('收款二维码管理')
    uploaded_qr = st.file_uploader('选择二维码图片', type=['png','jpg','jpeg'], key='qr_upload')
    if uploaded_qr is not None:
        st.image(uploaded_qr, caption='预览', width=200)
        if st.button('💾 保存收款码'):
            img_bytes = uploaded_qr.getvalue()
            set_setting('qr_image_bytes', base64.b64encode(img_bytes).decode())
            st.success('收款码已更新！')
            st.rerun()
    qr_data = get_setting('qr_image_bytes', '')
    if qr_data:
        st.subheader('当前收款码')
        st.image(base64.b64decode(qr_data), width=200)
    else:
        st.info('尚未设置收款码')

def get_user(username):
    from utils.database import get_user as db_get_user
    return db_get_user(username)
