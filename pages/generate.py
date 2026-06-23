import streamlit as st
from utils.database import init_db, deduct_credits, get_model_cost, add_credits
from utils.auth import get_user_credits
import openai

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

# 模型介绍（吸引眼球版）
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

# ---------- 真实生成函数 (AIHubMix) ----------
def generate_image_with_openai(prompt, model="dall-e-3", size="1024x1024"):
    """通过 AIHubMix (兼容 OpenAI) 生成图像，返回图片URL"""
    api_key = st.secrets.get("AIHUBMIX_API_KEY", "")
    if not api_key:
        st.error("AIHubMix API 密钥未配置，请在 Secrets 中设置 AIHUBMIX_API_KEY")
        return None

    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://aihubmix.com/v1"   # AIHubMix 固定地址
    )
    try:
        response = client.images.generate(
            model=model,
            prompt=prompt,
            n=1,
            size=size,
            quality="auto"
        )
        image_url = response.data[0].url
        return image_url
    except Exception as e:
        st.error(f"图像生成失败：{e}")
        return None

def get_generated_image(model_name, prompt):
    """
    统一调用 AIHubMix 接口生成图像。
    当前所有模型均使用同一个生成接口，后期可根据 model_name 做不同处理。
    """
    return generate_image_with_openai(prompt)

# ---------- UI 与生成逻辑 ----------
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
            if deduct_credits(username, cost):
                with st.spinner("AI正在挥洒创意，请稍候..."):
                    image_url = get_generated_image(model, prompt)
                if image_url:
                    st.success("✅ 生成成功！")
                    st.image(image_url, caption=f"文生图（{model}）", use_column_width=True)
                    st.info(f"剩余积分：{get_user_credits(username)}")
                else:
                    # 生成失败，退回积分
                    add_credits(username, cost)
                    st.error("生成失败，积分已退回")
            else:
                st.error("扣除积分失败")

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
            if deduct_credits(username, cost):
                with st.spinner("AI正在融合创意，请稍候..."):
                    # 图生图当前仅用文本描述生成，可后期扩展
                    image_url = get_generated_image(model, prompt)
                if image_url:
                    st.success("✅ 生成成功！")
                    st.image(image_url, caption=f"图生图（{model}）", use_column_width=True)
                    st.info(f"剩余积分：{get_user_credits(username)}")
                else:
                    add_credits(username, cost)
                    st.error("生成失败，积分已退回")
            else:
                st.error("扣除积分失败")
