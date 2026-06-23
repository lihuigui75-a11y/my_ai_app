import streamlit as st
from utils.database import init_db, get_user, is_user_banned, get_setting
from utils.auth import get_user_credits
import json

st.set_page_config(page_title='AI 图像生成器', page_icon='🎨', layout='wide')
init_db()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = ''
if 'role' not in st.session_state:
    st.session_state.role = ''

st.sidebar.title('🎨 阳雯科技')

if not st.session_state.authenticated:
    st.sidebar.subheader('🔐 用户登录')
    with st.sidebar.form('login_form'):
        u = st.text_input('用户名').strip()
        p = st.text_input('密码', type='password').strip()
        login_btn = st.form_submit_button('登录')
        if login_btn:
            if not u or not p:
                st.sidebar.error('请输入用户名和密码')
            else:
                user = get_user(u)
                if user is None:
                    st.sidebar.error('用户名不存在')
                elif user['password'] != p:
                    st.sidebar.error('密码错误')
                elif is_user_banned(u):
                    st.sidebar.error('❌ 账号已被封禁')
                else:
                    st.session_state.authenticated = True
                    st.session_state.username = u
                    st.session_state.role = user.get('role', 'user')
                    st.rerun()
    st.sidebar.markdown('---')
    if get_setting('registration_enabled', '1') == '1':
        st.sidebar.page_link('pages/register.py', label='📝 注册新账号', icon='📝')
    else:
        st.sidebar.warning('⛔ 管理员已关闭注册')
    st.sidebar.warning('⚠️ 请登录以使用生成功能')
else:
    st.sidebar.success(f'👤 欢迎，**{st.session_state.username}**')
    try:
        st.sidebar.metric('💰 积分', get_user_credits(st.session_state.username))
    except:
        st.sidebar.metric('💰 积分', 0)
    st.sidebar.markdown('---')
    st.sidebar.page_link('streamlit_app.py', label='🏠 首页', icon='🏠')
    st.sidebar.page_link('pages/generate.py', label='🎨 生成图像', icon='🖼️')
    st.sidebar.page_link('pages/profile.py', label='👤 个人中心', icon='👤')
    if st.session_state.role == 'admin':
        st.sidebar.page_link('pages/admin.py', label='🛡️ 后台管理', icon='🛡️')
    st.sidebar.markdown('---')
    if st.sidebar.button('🚪 退出登录'):
        for key in ['authenticated','username','role']:
            st.session_state[key] = '' if key != 'authenticated' else False
        st.rerun()

st.sidebar.markdown('---')
st.sidebar.info(f"📞 联系管理员 QQ: {get_setting('admin_qq', '158261755')}")
st.sidebar.caption('© 2025 阳雯科技')

st.markdown(
    "<style>"
    ".fixed-title {"
    "background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);"
    "color: white; padding: 15px; border-radius: 10px;"
    "text-align: center; font-size: 2rem; font-weight: bold;"
    "margin-bottom: 20px;"
    "}"
    "</style>"
    "<div class='fixed-title'>🎨 阳雯科技 · AI 图像生成器平台</div>",
    unsafe_allow_html=True
)

# 弹幕
danmu_raw = get_setting('danmu_list', '[]')
try:
    danmu_list = json.loads(danmu_raw)
except:
    danmu_list = []
if danmu_list:
    danmu_str = '&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;'.join(danmu_list)
    st.markdown(
        f'<marquee behavior="scroll" direction="left" scrollamount="6" '
        f'style="background:#f0f2f6; color:#333; padding:8px; border-radius:8px; '
        f'font-size:1rem; margin-bottom:20px;">{danmu_str}</marquee>',
        unsafe_allow_html=True
    )
else:
    st.info('🎈 暂无弹幕，管理员快来发送第一条吧！')

st.markdown(get_setting('home_custom_text', '选择一种生成模式开始创作'))
