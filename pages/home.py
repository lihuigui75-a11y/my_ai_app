import streamlit as st
from utils.database import init_db, get_setting

init_db()
st.set_page_config(page_title='首页', page_icon='🏠')
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

custom_text = get_setting('home_custom_text', '选择一种生成模式开始创作')
st.markdown(f'### {custom_text}')
col1, col2 = st.columns(2)
with col1:
    st.subheader('📝 文生图')
    st.write('输入文字描述，AI 将为您生成对应的图片。')
    st.markdown('**国内模型1积分/次，国外模型2积分/次**')
    if st.button('立即体验 · 文生图', key='txt2img_home'):
        if st.session_state.authenticated:
            st.switch_page('pages/generate.py')
        else:
            st.warning('⚠️ 请先登录')
with col2:
    st.subheader('🖼️ 图生图')
    st.write('上传参考图片并补充描述，生成风格化新图像。')
    st.markdown('**国内模型1积分/次，国外模型2积分/次**')
    if st.button('立即体验 · 图生图', key='img2img_home'):
        if st.session_state.authenticated:
            st.switch_page('pages/generate.py')
        else:
            st.warning('⚠️ 请先登录')
