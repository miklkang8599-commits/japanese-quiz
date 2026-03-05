"""
================================================================
【技術演進與邏輯追蹤表 - v6.0 原生暴力破解版】
----------------------------------------------------------------
- v4.8~v5.0 (黑科技失敗分析)：
  URL 參數重整在手機端會導致 Session 斷裂，造成點擊無效、格位不更新。

- v6.0 (本次解法 - 核心容器重寫)：
  1. 穩定通訊：改回原生 st.button，點擊事件直接與 Python 勾連，保證 100% 成功。
  2. 暴力併排：利用 CSS 穿透技術，強行將原本垂直堆疊的 Column 容器 
     轉化為 inline-flex 或 grid。
  3. 完美細節：答案格位縮小，按鈕緊貼（間距 2px），位置對調（按鈕在中，功能在底）。
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
st.set_page_config(page_title="🇯🇵 日文重組 v6.0", layout="wide")

# --- 2. 深度 CSS 滲透 (真正解決手機直立斷行) ---
st.markdown("""
    <style>
    /* 核心：強制讓所有 HorizontalBlock (st.columns 的父層) 在手機端不准斷行 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 2px !important;
        align-items: flex-start !important;
    }

    /* 核心：讓每個 Column 寬度歸零，隨內容展開 */
    [data-testid="column"] {
        flex: 0 1 auto !important;
        width: auto !important;
        min-width: 0px !important;
        padding: 0px !important;
    }

    /* 核心：原生按鈕視覺壓縮，確保緊貼 */
    div.stButton > button {
        width: auto !important;
        padding: 6px 12px !important;
        border-radius: 8px !important;
        border: 1px solid #e5e7eb !important;
        border-bottom: 3.5px solid #e5e7eb !important;
        font-size: 16px !important;
        font-weight: bold !important;
        margin: 0px !important;
    }

    /* 答案格位微縮化 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 4px; 
        background-color: #f9fafb; padding: 10px; 
        border-radius: 10px; border: 1.5px solid #e5e7eb; 
        min-height: 55px; align-items: center; margin-bottom: 15px;
    }
    .word-slot { 
        min-width: 32px; height: 26px; border-bottom: 2px solid #1cb0f6; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 18px; color: #1cb0f6; font-weight: bold; margin: 0 2px;
    }

    .block-container { padding: 0.5rem 0.3rem !important; }
    [data-testid="stHeader"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 功能函數 ---
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

def get_audio_html(text):
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
    try:
        res = requests.get(tts_url)
        if res.status_code == 200:
            b64 = base64.b64encode(res.content).decode()
            return f'<audio controls style="width:100%; height:38px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except: pass
    return ""

def reset_state():
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

# --- 4. 初始化 ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx = 0
if 'num_q' not in st.session_state:
    st.session_state.num_q = 10
if 'ans' not in st.session_state:
    reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄
    st.sidebar.header("⚙️ 練習設定")
    unit_list = sorted(df[cols['unit']].astype(str).unique())
    sel_unit = st.sidebar.selectbox("單元選擇", unit_list)
    unit_df = df[df[cols['unit']].astype(str) == sel_unit]
    sel_start_ch = st.sidebar.selectbox("起始章節", sorted(unit_df[cols['ch']].astype(str).unique()))
    filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
    preview_mode = st.sidebar.checkbox("📖 開啟預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if preview_mode:
        for i, item in enumerate(quiz_list):
            st.markdown(f"**{i+1}. {item[cols['cn']]}**")
            st.write(item[cols['ja']])
            st.markdown(get_audio_html(item[cols['ja']]), unsafe_allow_html=True)
            st.divider()
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw, cn_text = str(q[cols['ja']]).strip(), q[cols['cn']]
        sentence_struct = get_sentence_structure(ja_raw)
        word_tokens = [s['content'] for s in sentence_struct if s['type'] == 'word']
        
        if not st.session_state.shuf:
            st.session_state.shuf = list(word_tokens)
            random.seed(st.session_state.q_idx)
            random.shuffle(st.session_state.shuf)

        st.caption(f"Q{st.session_state.q_idx + 1} | {cn_text}")

        # A. 答案區
        curr_ans_copy = list(st.session_state.ans)
        ans_html = '<div class="res-box">'
        for s in sentence_struct:
            if s['type'] == 'punc': 
                ans_html += f'<span style="font-size:18px; color:#94a3b8; font-weight:bold;">{s["content"]}</span>'
            else:
                val = curr_ans_copy.pop(0) if curr_ans_copy else ""
                ans_html += f'<div class="word-slot">{val}</div>'
        ans_html += '</div>'
        st.markdown(ans_html, unsafe_allow_html=True)

        st.write("---")

        # B. 單字池 (原生按鈕，暴力併排)
        num_shuf = len(st.session_state.shuf)
        word_cols = st.columns(num_shuf if num_shuf > 0 else 1)
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                if word_cols[idx].button(t, key=f"p_{st.session_state.q_idx}_{idx}"):
                    st.session_state.ans.append(t)
                    st.session_state.used_history.append(idx)
                    st.rerun()

        # C. 功能鍵 (底部)
        st.write(" ")
        n1, n2, n3, n4 = st.columns(4)
        if n1.button("⏮上"): 
            st.session_state.q_idx = max(0, st.session_state.q_idx-1); reset_state(); st.rerun()
        if n2.button("⏭下"): 
            st.session_state.q_idx = min(len(quiz_list)-1, st.session_state.q_idx+1); reset_state(); st.rerun()
        if n3.button("🔄重"): reset_state(); st.rerun()
        if n4.button("⬅退"):
            if st.session_state.used_history:
                st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            if st.button("🔍 CHECK", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(word_tokens):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔！")

        if st.session_state.is_correct:
            st.success("正解！")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("CONTINUE ➡️", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
