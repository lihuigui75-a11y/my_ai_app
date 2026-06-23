import streamlit as st
from utils.database import init_db, deduct_credits, add_credits
from utils.auth import get_user_credits
import requests
import base64
from openai import OpenAI

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
# 分为两类：ideogram（使用 /models/{model}/predictions 端点）和 openai（使用 images.generate 端点）
MODEL_MAP = {
    # Ideogram 系列
    "ideogram/V_2_TURBO": {
        "info": "⚡ V2 极速版：细节锐利，出图如电，快到你来不及眨眼！",
        "api_type": "ideogram",
        "api_model": "V_2_TURBO",
        "cost": 1,
    },
    "ideogram/V_2": {
        "info": "🎯 V2 均衡王：速度与画质黄金配比，随手一点即出大片。",
        "api_type": "ideogram",
        "api_model": "V_2",
        "cost": 1,
    },
    "ideogram/V_3": {
        "info": "👑 V3 旗舰：文字渲染逆天，复杂构图轻松封神！",
        "api_type": "ideogram",
        "api_model": "V_3",
        "cost": 1,
    },
    "ideogram/V_2_A": {
        "info": "🎨 V2 艺术加冕：油画质感拉满，每一张都是大师真迹。",
        "api_type": "ideogram",
        "api_model": "V_2_A",
        "cost": 1,
    },
    "ideogram/V_2_A_TURBO": {
        "info": "💨 V2 艺术闪电：艺术细胞 + 超音速，灵感零等待！",
        "api_type": "ideogram",
        "api_model": "V_2_A_TURBO",
        "cost": 1,
    },
    "ideogram/V_1": {
        "info": "📷 V1 经典元老：稳如泰山，老炮最爱。",
        "api_type": "ideogram",
        "api_model": "V_1",
        "cost": 1,
    },
    "ideogram/V_1_TURBO": {
        "info": "🔥 V1 涡轮版：经典配方 + 狂暴加速，老司机的新座驾。",
        "api_type": "ideogram",
        "api_model": "V_1_TURBO",
        "cost": 1,
    },
    # GPT 图像系列
    "gpt-image-1": {
        "info": "🎯 GPT 图像 1 旗舰版：高细节、高保真，文生图与图生图皆可，商业级创作首选。",
        "api_type": "openai",
        "api_model": "gpt-image-1",
        "cost": 2,
    },
    "gpt-image-2-free": {
        "info": "🆓 GPT 图像 2 免费版：快速出图，适合日常灵感与测试，超值之选。",
        "api_type": "openai",
        "api_model": "gpt-image-2-free",
        "cost": 1,
    },
}

# ---------- AIHubMix 客户端 ----------
def get_aihubmix_key():
    key = st.secrets.get("AIHUBMIX_API_KEY", "")
    if not key:
        st.error("AIHubMix API 密钥未配置")
    return key

# ---------- Ideogram 专用生成函数 ----------
def ideogram_generate(prompt, api_model, aspect_ratio="1x1"):
    api_key = get_aihubmix_key()
    if not api_key:
        return None
    url = f"https://aihubmix.com/v1/models/{api_model}/predictions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "input": {
            "prompt": prompt,
            "rendering_speed": "QUALITY",
            "aspect_ratio": aspect_ratio,
        }
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        data = resp.json()
        if resp.status_code == 200:
            output = data.get("output") or data.get("data", {}).get("output")
            if output and "url" in output:
                img_resp = requests.get(output["url"], timeout=30)
                return img_resp.content
            elif output and "image" in output:
                return base64.b64decode(output["image"])
            # 备用解析：data.data[0].url
            if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
                item = data["data"][0]
                if "url" in item:
                    img_resp = requests.get(item["url"], timeout=30)
                    return img_resp.content
            st.error("Ideogram 返回数据无法解析，请检查 API 返回格式")
            return None
        else:
            st.error(f"Ideogram 生成失败：{resp.status_code} - {data.get('error', data)}")
            return None
    except Exception as e:
        st.error(f"Ideogram 请求异常：{e}")
        return None

# ---------- GPT 图像生成函数 ----------
def gpt_image_generate(prompt, api_model, size="1024x1024", quality="high", reference_image=None):
    api_key = get_aihubmix_key()
    if not api_key:
        return None
    client = OpenAI(
        api_key=api_key,
        base_url="https://aihubmix.com/v1",
    )
    try:
        if reference_image:
            # 图生图：使用 images.edit
            response = client.images.edit(
                model=api_model,
                image=reference_image,
                prompt=prompt,
                n=1,
                size=size,
                quality=quality,
                input_fidelity="high",
            )
        else:
            # 文生图：使用 images.generate
            response = client.images.generate(
                model=api_model,
                prompt=prompt,
                n=1,
                size=size,
                quality=quality,
                moderation="low",
                background="auto",
            )
        if response.data and len(response.data) > 0:
            b64_data = response.data[0].b64_json
            if b64_data:
                return base64.b64decode(b64_data)
            if response.data[0].url:
                img_resp = requests.get(response.data[0].url, timeout=30)
                return img_resp.content
        st.error("GPT 图像 API 未返回有效图片数据")
        return None
    except Exception as e:
        st.error(f"GPT 图像生成失败：{e}")
        return None

# ---------- 统一生成入口 ----------
def generate_image(model_display_name, prompt, reference_image=None):
    cfg = MODEL_MAP.get(model_display_name)
    if not cfg:
        st.error("不支持的模型")
        return None
    if cfg["api_type"] == "ideogram":
        return ideogram_generate(prompt, cfg["api_model"])
    elif cfg["api_type"] == "openai":
        return gpt_image_generate(prompt, cfg["api_model"], reference_image=reference_image)
    else:
        st.error("未知模型类型")
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
                with st.spinner("AI 正在创作..."):
                    img_bytes = generate_image(model, prompt)
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
    # 图生图暂时只支持 GPT 图像系列模型
    available_models = [m for m in models if MODEL_MAP[m]["api_type"] == "openai"]
    if not available_models:
        st.error("当前没有支持图生图的模型，请使用文生图")
        st.stop()
    model = st.selectbox("选择模型（仅 GPT 系列支持图生图）", available_models)
    cfg = MODEL_MAP[model]
    cost = cfg["cost"]
    st.caption(f"该模型每次生成消耗 **{cost}** 积分")
    st.info(cfg["info"])
    prompt = st.text_area("修改描述（可选）", height=100, placeholder="例如：保留主体，将背景改为星空...")
    if st.button("✨ 生成图像", type="primary"):
        if not uploaded_file:
            st.error("请上传参考图片")
        elif credits < cost:
            st.error("积分不足")
        else:
            if deduct_credits(username, cost):
                with st.spinner("AI 正在融合创意..."):
                    # 将上传文件转为字节流
                    img_bytes = generate_image(model, prompt, reference_image=uploaded_file)
                if img_bytes:
                    st.success("✅ 生成成功！")
                    st.image(img_bytes, caption=f"图生图（{model}）", use_column_width=True)
                    st.info(f"剩余积分：{get_user_credits(username)}")
                else:
                    add_credits(username, cost)
                    st.error("生成失败，积分已退回")
            else:
                st.error("扣除积分失败")import streamlit as st
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
