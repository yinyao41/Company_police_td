
# -*- coding: utf-8 -*-
import streamlit as st
import requests
from docx import Document
from io import BytesIO
from openai import OpenAI
import os

# =============================================================================
# 配置区
# =============================================================================
GITHUB_USERNAME = "yinyao41"
GITHUB_REPO = "Company_policy"
BRANCH = "master"

# 只读取这一个文件（其他文件已移除）
POLICY_FILE = "data/同登制度汇编202602.docx"

# 系统提示词
SYSTEM_PROMPT = """你是一位专业、严谨的企业制度咨询助手。
你的全部知识**仅来源于**下方提供的《同登制度汇编202602.docx》这份文件的**完整内容**，不得使用任何外部知识或编造内容。
回答时请尽量引用原文条款、章节编号或具体表述，保持客观中立。
如果用户问题与公司制度无关，请礼貌回复：
“抱歉，本助手仅回答与公司制度相关的问题，请提出制度相关咨询。”"""

# =============================================================================
# 阿里通义千问客户端（使用更大上下文模型）
# =============================================================================
DASHSCOPE_API_KEY = st.secrets.get("DASHSCOPE_API_KEY", os.getenv("DASHSCOPE_API_KEY"))
if not DASHSCOPE_API_KEY:
    st.error("缺少 DASHSCOPE_API_KEY！请在 Streamlit Cloud → Settings → Secrets 中添加")
    st.stop()

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

MODEL_NAME = "qwen-plus"   # 使用更大上下文模型

# =============================================================================
# 只读取同登制度汇编202602.docx（完整不截断）
# =============================================================================
@st.cache_data(show_spinner="正在从 GitHub 下载并解析《同登制度汇编202602.docx》完整内容...")
def load_policy():
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/{BRANCH}/{POLICY_FILE}"
    
    try:
        r = requests.get(raw_url, timeout=20)
        r.raise_for_status()
        
        doc = Document(BytesIO(r.content))
        text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
        
        if not text:
            st.error("文件内容为空！")
            st.stop()

        # 不再进行任何截断，保证完整读取
        display_name = "同登制度汇编202602"
        return f"【{display_name}】\n{text}\n{'─' * 80}\n"
        
    except Exception as e:
        st.error(f"读取文件失败：{str(e)}")
        st.stop()


# 执行加载（完整全文）
POLICIES_TEXT = load_policy()

# =============================================================================
# Streamlit 界面
# =============================================================================
st.set_page_config(page_title="企业制度问答助手", layout="wide")
st.title("🏢 企业制度智能问答助手")

# 提示用户文件已完整加载
st.success("✅ 已完整加载《同登制度汇编202602.docx》全部内容（无截断）")

# 初始化聊天历史
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "system",
        "content": SYSTEM_PROMPT + "\n\n以下是公司全部制度文本（请严格依据此内容回答）：\n\n" + POLICIES_TEXT
    }]

# 显示历史消息
for msg in st.session_state.messages[1:]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 用户输入
if prompt := st.chat_input("请输入关于公司制度的问题，例如：年假如何计算？"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("正在查询制度原文..."):
            try:
                stream = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=st.session_state.messages,
                    temperature=0.25,
                    max_tokens=2500,
                    stream=True
                )
                
                response_container = st.empty()
                full_response = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        response_container.markdown(full_response + "▌")
                
                response_container.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                st.error(f"模型调用失败：{str(e)}")
                if "401" in str(e):
                    st.warning("API Key 无效或未设置，请检查 Streamlit Secrets")
