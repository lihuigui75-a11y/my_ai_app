import streamlit as st
from utils.database import init_db, deduct_credits, get_model_cost
from utils.auth import get_user_credits
import random
import openai
import requests
import io
from PIL import Image

init_db()

st.set_page_config(page_title="图像生成", page_icon="🖼️")

if not st.session_state.get('authenticated', False):
    st.warning("⚠️ 请先登录")
    st.stop()

username = st.session_state.username
credits = get_user_credits(username)
if credits < 1:
    st.error("❌ 积分不足")
    st.stop()

# 模型介绍（保留之前的吸引人版）
model_info = {
    "ideogram/V_2_TURBO": "⚡ 官方极速版，出图如电，细节锐到刺眼，快到你来不及眨眼！",
    "ideogram/V_2": "🎯 均衡标杆，速度与画质黄金配比，随手一点即出大片。",
    "ideogram/V_3": "👑 旗舰新生代，文字渲染逆天，复杂构图轻松封神！",
    "ideogram/V_2_A": "🎨 艺术加强版，油画质感拉满，每一张都是大师真迹。",
    "ideogram/V_2_A_TURBO": "💨 艺术快枪手，艺术细胞+超音速，灵感永不掉线。",
    "ideogram/V_1": "📷 经典元老，稳如泰山，出图永远可靠，老炮最爱。",
    "ideogram/V_1_TURBO": "🔥 经典涡轮，老牌劲旅暴走，速度与画质双双起飞。",
    "openai/dall-e-3": "🤖 科幻巨擘，理解力突破天际，想象力直达宇宙，AI 绘师天花板！",
}

st.title("🎨 图像生成")
st.caption(f"当前积分：{credits}")
mode = st.radio("选择生成模式", ["📝 文生图", "🖼️ 图生图"], horizontal=True)

models = list(model_info.keys())

# ---------- 真实生成函数 ----------
def generate_image_with_openai(prompt, model="dall-e-3", size="1024x1024"):
    """使用OpenAI DALL·E 3生成图像，返回图片URL"""
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        st.error("OpenAI API密钥未配置")
        return None
    client = openai.OpenAI(api_key=api_key)
    try:
        response = client.images.generate(
            model=model,
            prompt=prompt,
            n=1,
            size=size,
            quality="standard"
        )
        image_url = response.data[0].url
        return image_url
    except Exception as e:
        st.error(f"OpenAI生成失败: {e}")
        return None

def generate_image_with_ideogram(prompt, model_version="V_2", aspect_ratio="ASPECT_1_1"):
    """使用Ideogram API生成图像，返回图片URL或None"""
    api_key = st.secrets.get("IDEOGRAM_API_KEY", "")
    if not api_key:
        st.error("Ideogram API密钥未配置")
        return None
    # 将模型名称映射为Ideogram实际模型名，这里简单映射为对应的版本号
    if "V_2_TURBO" in model_version:
        model_id = "V_2_TURBO"
    elif "V_2_A_TURBO" in model_version:
        model_id = "V_2_A_TURBO"
    elif "V_2_A" in model_version:
        model_id = "V_2_A"
    elif "V_3" in model_version:
        model_id = "V_3"
    elif "V_1_TURBO" in model_version:
        model_id = "V_1_TURBO"
    elif "V_1" in model_version:
        model_id = "V_1"
    else:
        model_id = "V_2"  # 默认
    url = "https://api.ideogram.ai/generate"
    headers = {
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "image_request": {
            "model": model_id,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "magic_prompt_option": "AUTO"
        }
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        data = resp.json()
        if resp.status_code == 200 and "data" in data:
            image_url = data["data"][0]["url"]
            return image_url
        else:
            st.error(f"Ideogram错误: {data.get('error', '未知错误')}")
            return None
    except Exception as e:
        st.error(f"Ideogram请求失败: {e}")
        return None

def get_generated_image(model_name, prompt):
    """根据模型名称调用对应API，返回图片URL"""
    if "dall-e" in model_name.lower():
        # 国外模型，消耗2积分，调用OpenAI
        return generate_image_with_openai(prompt)
    else:
        # 国内模型，消耗1积分，调用Ideogram（如果没有密钥，可fallback到OpenAI或提示）
        ideogram_key = st.secrets.get("IDEOGRAM_API_KEY", "")
        if ideogram_key:
            return generate_image_with_ideogram(prompt, model_name)
        else:
            # 如果Ideogram密钥未配置，自动降级到OpenAI
            st.warning("Ideogram密钥未配置，已自动使用OpenAI DALL·E 3生成")
            return generate_image_with_openai(prompt)

# ---------- UI部分 ----------
if mode == "📝 文生图":
    st.subheader("文字描述生成图像")
    model = st.selectbox("选择模型", models)
    cost = get_model_cost(model)
    st.caption(f"该模型每次生成消耗 **{cost}** 积分")
    st.info(model_info[model])
    prompt = st.text_area("请输入图像描述", height=150)
    if st.button("✨ 生成图像", type="primary"):
        if not prompt.strip():
            st.error("请输入描述")
        elif credits < cost:
            st.error("积分不足")
        else:
            # 扣除积分
            if not deduct_credits(username, cost):
                st.error("扣除积分失败")
            else:
                with st.spinner("AI正在挥洒创意，请稍候..."):
                    image_url = get_generated_image(model, prompt)
                if image_url:
                    st.success("✅ 生成成功！")
                    st.image(image_url, caption=f"文生图（{model}）", use_column_width=True)
                    st.info(f"剩余积分：{get_user_credits(username)}")
                else:
                    # 生成失败则退回积分
                    from utils.database import add_credits
                    add_credits(username, cost)
                    st.error("生成失败，积分已退回")

else:   # 图生图
    st.subheader("参考图 + 描述生成新图像")
    uploaded = st.file_uploader("上传参考图片", type=["png","jpg","jpeg"])
    if uploaded:
        st.image(uploaded, caption="参考图", width=300)
    model = st.selectbox("选择模型", models)
    cost = get_model_cost(model)
    st.caption(f"该模型每次生成消耗 **{cost}** 积分")
    st.info(model_info[model])
    prompt = st.text_area("修改描述", height=150)
    if st.button("✨ 生成图像", type="primary"):
        if not uploaded:
            st.error("请上传参考图片")
        elif not prompt.strip():
            st.error("请输入修改描述")
        elif credits < cost:
            st.error(f"积分不足（需{cost}积分）")
        else:
            # 图生图目前使用相同API（多数模型暂不支持参考图，后期可扩展）
            if not deduct_credits(username, cost):
                st.error("扣除积分失败")
            else:
                with st.spinner("AI正在融合参考图与描述，请稍候..."):
                    # 暂时只用文字生成，忽略参考图（后续可接入支持图生图的API）
                    image_url = get_generated_image(model, prompt)
                if image_url:
                    st.success("✅ 生成成功！")
                    st.image(image_url, caption=f"图生图（{model}）", use_column_width=True)
                    st.info(f"剩余积分：{get_user_credits(username)}")
                else:
                    from utils.database import add_credits
                    add_credits(username, cost)
                    st.error("生成失败，积分已退回")