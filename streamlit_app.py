"""
================================================================
【技術演進與邏輯追蹤表 - v5.0 種子鎖定版】
----------------------------------------------------------------
- v4.8~v4.9 (失敗原因)：
  Streamlit Cloud 在處理 URL 參數重整時，會重新執行腳本。
  如果沒有鎖定隨機種子，st.session_state.shuf 會被重新洗牌，
  導致點擊的 index 失效，單字進不了框，按鈕也不會減少。

- v5.0 (本次解法 - 絕對種子鎖定)：
  1. 隨機種子：使用題目 index (q_idx) 作為 random.seed，
     保證在同一題內，無論頁面重整幾次，單字池順序絕對固定。
  2. 狀態保全：確保 used_history 與 ans 優先於 UI 渲染處理。
  3. 穩定通訊：維持 URL 參數法，這是目前唯一能保證手機併排的方案。
----------------------------------------------------------------
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 1. 頁面配置 ---
st.set_page_config(page_title="🇯🇵 日文重組 v5.0", layout="wide")

# --- 2. 狀態初始化 (必須在最前面) ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx = 0
if 'num_q' not in st.session_state:
    st.session_state.num_q = 10
if 'ans' not in st.session_state:
    st.session_state.ans = []
if 'used_history' not in st.session_state:
    st.session_state.used_history = []
if 'shuf' not in st.session_state:
    st.session_state.shuf = []
if 'is_correct' not in st.session_state:
    st.session_state.is_correct = False

# --- 3. 核心：處理 URL 點擊 (必須在單字池生成前) ---
params = st.query_params
if "pick" in params:
    try:
        idx = int(params["pick"])
        # 只有在 index 有效且未被使用過時才處理
        if "shuf" in st.session_state and len(st.session_state.shuf) > idx:
            if idx not in st.session_state.used_history:
                st.session_state.ans.append(st.session_state.shuf[idx])
                st.session_state.used_history.append(idx)
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.query_params.clear()

# --- 4. CSS 樣式 ---
st.markdown("""
    <style>
    .block-container { padding: 1rem 0.5rem !important; }
    [data-testid="stHeader"] { display: none; }
    .res-box { 
        display:flex; flex-wrap:wrap; gap:4px; background:#fff; padding:10px; 
        border-radius:10px; border:1.5px solid #e5e7eb; min-height:55px; align-items:center; 
    }
    .word-slot { 
        min-width:32px; height:26px; border-bottom:2px solid #3b82f6; 
        display:flex; align-items:center; justify-content:center; 
        font-size:16px; color:#2563eb; font-weight:bold; margin:0 2px;
    }
    .btn-pool { display:flex; flex-wrap:wrap; gap:6px; padding:10px 0; }
    .custom-btn {
        display:inline-block; background:white; border:1px solid #e5e7eb; 
        border-bottom:3.5px solid #e5e7eb; border-radius:10px; padding:8px 15px; 
        font-size:16px; font-weight:bold; color:#4b4b4b; text-decoration:none;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. 功能函數 ---
@st.cache_data(ttl=60)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA/export?format=csv&gid=1337973082"
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(subset=["日文原文", "中文意譯"]), {"ja": "日文原文", "cn": "中文意譯", "unit": "單元", "ch": "章節"}
    except: return None, None

def get_sentence_structure(text):
    pts = ['は','が','を','に','へ','と','も','で','の','から','まで']
    raw = re.split(r'([、。！？])', text.strip())
    struct = []
    for p in raw:
        if not p: continue
        if p in ['、', '。', '！', '？']: struct.append({"type": "punc", "content": p})
        else:
            tokens = [t for t in re.split(r'[ 　]+', p) if t] if " " in p or "　" in p else [t for t in re.split(f"({'|'.join(pts)})", p) if t]
            for t in tokens: struct.append({"type": "word", "content": t})
    return struct

def reset_state():
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

# --- 6. 主程式 ---
df, cols = load_data()
if df is not None:
    unit_list = sorted(df[cols['unit']].astype(str).unique())
    sel_unit = st.sidebar.selectbox("單元", unit_list)
    unit_df = df[df[cols['unit']].astype(str) == sel_unit]
    sel_start_ch = st.sidebar.selectbox("章節", sorted(unit_df[cols['ch']].astype(str).unique()))
    filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
    preview_mode = st.sidebar.checkbox("預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if not preview_mode and st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw, cn_text = str(q[cols['ja']]).strip(), q[cols['cn']]
        sentence_struct = get_sentence_structure(ja_raw)
        word_tokens = [s['content'] for s in sentence_struct if s['type'] == 'word']
        
        # 【核心關鍵】使用題目索引作為種子，確保重整後單字順序不變
        if not st.session_state.shuf:
            random.seed(st.session_state.q_idx) 
            st.session_state.shuf = list(word_tokens)
            random.shuffle(st.session_state.shuf)

        st.caption(f"Q{st.session_state.q_idx + 1} | {cn_text}")

        # 答案展示
        ans_copy = list(st.session_state.ans)
        ans_html = '<div class="res-box">'
        for s in sentence_struct:
            if s['type'] == 'punc': ans_html += f'<span style="color:#94a3b8;">{s["content"]}</span>'
            else:
                val = ans_copy.pop(0) if ans_copy else ""
                ans_html += f'<div class="word-slot">{val}</div>'
        ans_html += '</div>'
        st.markdown(ans_html, unsafe_allow_html=True)

        st.write("---")

        # 按鈕池
        btn_html = '<div class="btn-pool">'
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                btn_html += f'<a href="?pick={idx}" target="_self" class="custom-btn">{t}</a>'
        btn_html += '</div>'
        st.markdown(btn_pool_html if 'btn_pool_html' in locals() else btn_html, unsafe_allow_html=True)

        # 功能鍵
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("⏮上"): 
            st.session_state.q_idx = max(0, st.session_state.q_idx-1); reset_state(); st.rerun()
        if c2.button("⏭下"): 
            st.session_state.q_idx = min(len(quiz_list)-1, st.session_state.q_idx+1); reset_state(); st.rerun()
        if c3.button("🔄重"): reset_state(); st.rerun()
        if c4.button("⬅退"):
            if st.session_state.used_history:
                st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            if st.button("🔍 CHECK", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(word_tokens):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對！")

        if st.session_state.is_correct:
            st.success("正解！")
            if st.button("CONTINUE ➡️", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
    elif preview_mode:
        st.subheader("預習清單")
        for i, item in enumerate(quiz_list):
            st.write(f"{i+1}. {item[cols['cn']]}\n{item[cols['ja']]}")
            st.divider()
