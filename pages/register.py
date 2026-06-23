import streamlit as st
from utils.database import init_db, create_user, get_user, get_setting
import random, time

init_db()
st.set_page_config(page_title='注册', page_icon='📝')
if get_setting('registration_enabled', '1') != '1':
    st.error('⛔ 管理员已关闭新用户注册，请稍后再试。')
    st.stop()

st.title('📝 用户注册')
if 'register_count' not in st.session_state:
    st.session_state.register_count = 0
if 'register_times' not in st.session_state:
    st.session_state.register_times = []
MAX_REG_PER_HOUR = 3
now = time.time()
st.session_state.register_times = [t for t in st.session_state.register_times if now - t < 3600]
recent_regs = len(st.session_state.register_times)
if recent_regs >= MAX_REG_PER_HOUR:
    st.error('⏳ 注册过于频繁，请稍后再试（同一设备每小时最多注册3次）')
    st.stop()

if 'captcha_a' not in st.session_state or 'captcha_b' not in st.session_state:
    st.session_state.captcha_a = random.randint(1, 20)
    st.session_state.captcha_b = random.randint(1, 20)

with st.form('reg_form'):
    uname = st.text_input('用户名').strip()
    pwd = st.text_input('密码', type='password').strip()
    cpwd = st.text_input('确认密码', type='password').strip()
    captcha_input = st.text_input(f'验证码：{st.session_state.captcha_a} + {st.session_state.captcha_b} = ?').strip()
    submitted = st.form_submit_button('注册')
    if submitted:
        try:
            user_answer = int(captcha_input)
        except:
            user_answer = None
        correct = st.session_state.captcha_a + st.session_state.captcha_b
        if user_answer != correct:
            st.error('验证码错误，请重新输入（题目不变）')
        elif not uname or not pwd or not cpwd:
            st.error('所有字段必填')
        elif pwd != cpwd:
            st.error('两次密码不一致')
        elif get_user(uname):
            st.error('用户名已存在')
        else:
            if create_user(uname, pwd):
                st.session_state.register_count += 1
                st.session_state.register_times.append(time.time())
                st.success(f'🎉 注册成功！用户名：{uname}，初始积分 3。请点击下方按钮返回主页登录。')
                st.balloons()
                st.session_state.captcha_a = random.randint(1, 20)
                st.session_state.captcha_b = random.randint(1, 20)
            else:
                st.error('注册失败，请稍后再试')

st.page_link('streamlit_app.py', label='🏠 返回主页登录', icon='🏠')
