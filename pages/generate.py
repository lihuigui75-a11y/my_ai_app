import streamlit as st
from utils.database import init_db, deduct_credits, get_model_cost, add_credits
from utils.auth import get_user_credits
import base64
from openai import OpenAI
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

# ---------- 模型定义 ----------
MODEL_MAP = {
    "gpt-image-1": {
        "info": "🎯 GPT 图像 1 旗舰版：高细节、高保真，支持文生图与图生图，适合商业级创作。",
        "api_type": "openai",
        "api_model": "gpt-image-1",
        "cost": 2,             # 消耗积分可根据需要调整
    },
    "gpt-image-2-free": {
        "info": "🆓 GPT 图像 2 免费版：快速出图，适合日常灵感与测试，超值之选。",
        "api_type": "openai",
        "api_model": "gpt-image-2-free",
        "cost": 1,
    },
    # 如果你还想保留 ideogram 系列，可以继续添加，但 API 调用方式不同
    # 目前统一用 OpenAI 兼容接口
}

# ---------- 图像生成函数 ----------
def get_openai_client():
    api_key = st.secrets.get("AIHUBMIX_API_KEY", "")
    if not api_key:
        st.error("AIHubMix API 密钥未配置")
        return None
    return OpenAI(
        api_key=api_key,
        base_url="https://aihubmix.com/v1"
    )

def text_to_image(prompt, api_model, size="1024x1024", quality="high"):
    """文生图"""
    client = get_openai_client()
    if not client:
        return None
    try:
        response = client.images.generate(
            model=api_model,
            prompt=prompt,
            n=1,
            size=size,
            quality=quality,
            moderation="low",        # 根据API要求添加
            background="auto",
        )
        # 解析返回的 base64 图片
        if response.data and len(response.data) > 0:
            b64_data = response.data[0].b64_json
            if b64_data:
                return base64.b64decode(b64_data)
            # 如果没有 b64_json，尝试 url
            if response.data[0].url:
                import requests
                img_resp = requests.get(response.data[0].url, timeout=30)
                return img_resp.content
        st.error("API 未返回图像数据")
        return None
    except Exception as e:
        st.error(f"文生图失败：{e}")
        return None

def image_to_image(prompt, image_file, api_model, size="1024x1024", quality="high", input_fidelity="high"):
    """图生图（使用 images.edit）"""
    client = get_openai_client()
    if not client:
        return None
    try:
        # 将上传的图片转为字节流
        if isinstance(image_file, bytes):
            image_bytes = image_file
        else:
            image_bytes = image_file.getvalue()

        # API 要求 image 参数为二进制文件对象，这里用 io.BytesIO 模拟
        response = client.images.edit(
            model=api_model,
            image=io.BytesIO(image_bytes),
            prompt=prompt,
            n=1,
            size=size,
            quality=quality,
            input_fidelity=input_fidelity,
            # moderation 在图生图中不支持，忽略
        )
        if response.data and len(response.data) > 0:
            b64_data = response.data[0].b64_json
            if b64_data:
                return base64.b64decode(b64_data)
            if response.data[0].url:
                import requests
                img_resp = requests.get(response.data[0].url, timeout=30)
                return img_resp.content
        st.error("API 未返回图像数据")
        return None
    except Exception as e:
        st.error(f"图生图失败：{e}")
        return None

# ---------- UI ----------
st.title("🎨 图像生成")
st.caption(f"当前积分：{credits}")
mode = st.radio("选择生成模式", ["📝 文生图", "🖼️ 图生图"], horizontal=True)

models = list(MODEL_MAP.keys())

if mode == "📝 文生图":
    st.subheader("文字描述生成图像")
    model = st.selectbox("选择模型", models)
    cfg = MODEL_MAP[model]
    cost = cfg["cost"]
    st.caption(f"该模型每次生成消耗 **{cost}** 积分")
    st.info(cfg["info"])
    prompt = st.text_area("请输入图像描述", height=150)
    if st.button("✨ 生成图像", type="primary"):
        if not prompt.strip():
            st.error("请输入描述")
        elif credits < cost:
            st.error("积分不足")
        else:
            if deduct_credits(username, cost):
                with st.spinner("AI 正在挥洒创意，请稍候..."):
                    img_bytes = text_to_image(prompt, cfg["api_model"])
                if img_bytes:
                    st.success("✅ 生成成功！")
                    st.image(img_bytes, caption=f"文生图（{model}）", use_column_width=True)
                    st.info(f"剩余积分：{get_user_credits(username)}")
                else:
                    add_credits(username, cost)
                    st.error("生成失败，积分已退回")
            else:
                st.error("扣除积分失败")

else:   # 图生图
    st.subheader("参考图 + 描述生成新图像")
    uploaded_file = st.file_uploader("上传参考图片", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        st.image(uploaded_file, caption="参考图预览", width=300)
    model = st.selectbox("选择模型", models)
    cfg = MODEL_MAP[model]
    cost = cfg["cost"]
    st.caption(f"该模型每次生成消耗 **{cost}** 积分")
    st.info(cfg["info"])
    prompt = st.text_area("修改描述（可选）", height=100, placeholder="例如：保留主体，将背景改为星空...")
    if st.button("✨ 生成图像", type="primary"):
        if not uploaded_file:
            st.error("请先上传参考图片")
        elif credits < cost:
            st.error("积分不足")
        else:
            # 图生图可以不强制写描述，但最好有提示
            if deduct_credits(username, cost):
                with st.spinner("AI 正在融合创意，请稍候..."):
                    img_bytes = image_to_image(
                        prompt=prompt,
                        image_file=uploaded_file,
                        api_model=cfg["api_model"]
                    )
                if img_bytes:
                    st.success("✅ 生成成功！")
                    st.image(img_bytes, caption=f"图生图（{model}）", use_column_width=True)
                    st.info(f"剩余积分：{get_user_credits(username)}")
                else:
                    add_credits(username, cost)
                    st.error("生成失败，积分已退回")
            else:
                st.error("扣除积分失败")
