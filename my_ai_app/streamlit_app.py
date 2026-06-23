import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from utils.db import init_db, get_user_credits, is_user_banned

# 初始化数据库
init_db()

# 加载认证配置
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = None

# 登录界面
if st.session_state["authentication_status"] is None:
    authenticator.login(fields={'username': '用户名', 'password': '密码', 'login': '登录'})
    st.markdown("还没有账号？[点击这里注册](register)")
    st.stop()
elif st.session_state["authentication_status"] is False:
    st.error("用户名或密码错误")
    st.stop()
else:
    username = st.session_state["username"]
    user_roles = config['credentials']['usernames'][username].get('roles', ['user'])
    st.session_state["role"] = "admin" if "admin" in user_roles else "user"
    st.session_state["membership_type"] = "free"
    
    # 检查封禁
    if is_user_banned(username):
        st.error("⚠️ 您的账号已被封禁，请联系管理员。")
        authenticator.logout("登出")
        st.stop()
    
    credits = get_user_credits(username)
    st.session_state["credits"] = credits
    
    # 侧边栏
    with st.sidebar:
        st.write(f"👤 用户: {username}")
        st.write(f"💎 积分: {credits}")
        authenticator.logout("登出", "sidebar")
    
    # 页面导航
    base_pages = [
        st.Page("pages/home.py", title="AI图像生成器", icon=":material/auto_awesome:"),
        st.Page("pages/generate.py", title="多模态生成", icon=":material/photo_library:"),
        st.Page("pages/profile.py", title="个人中心", icon=":material/person:"),
    ]
    admin_pages = [
        st.Page("pages/admin.py", title="管理员面板", icon=":material/admin_panel_settings:"),
    ]
    if st.session_state["role"] == "admin":
        nav_pages = base_pages + admin_pages
    else:
        nav_pages = base_pages
    
    pg = st.navigation(nav_pages)
    pg.run()