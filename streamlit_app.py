"""
================================================================
【日文結構練習器 - v3.6 極致緊湊版】
版本編號：v3.6.20260306
設計重點：
1. 消除間隙：強制 CSS 覆蓋 st.columns 的 gap，實現按鈕緊貼。
2. 空間精算：縮減所有組件高度，專為手機直立螢幕優化。
3. 預習模式：全展開清單，Base64 穩定音訊。
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 【重點 1】強制緊貼 CSS (無視環境間距) ---
st.set_page_config(page_title="🇯🇵 日文重組 v3.6", layout="wide")

st.markdown("""
    <style>
    /* 1. 核心：強制移除 Column 之間的所有間距 */
    [data-testid="stHorizontalBlock"] {
        gap: 4px !important; /* 縮小到極致 */
        display: flex !important;
        flex-wrap: wrap !important;
    }
    [data-testid="column"] {
        padding: 0px !important;
        margin: 0px !important;
        flex: 0 1 auto !important;
        width: auto !important;
        min-width: 0px !important;
    }

    /* 2. 移除所有預設內邊距 */
    .block-container { padding: 0.5rem 0.3rem !important; }
    [data-testid="stHeader"] { display: none; }
    
    /* 3. 答案區：扁平化卡片 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 4px; 
        background-color: #ffffff; padding: 10px; 
        border-radius: 10px; border: 2px solid #e5e7eb; 
        min-height: 75px; margin-bottom: 8px; align-items: center; 
    }
    .word-slot { 
        min-width: 40px; height: 32px; border-bottom: 2px solid #e5e7eb; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 18px; color: #1cb0f6; font-weight: bold; 
    }
    .punc-display { font-size: 20px; color: #afafaf; font-weight: bold; }

    /* 4. 仿 Duolingo 緊湊按鈕 */
    div.stButton > button {
        border-radius: 8px !important;
        border: 2px solid #e5e7eb !important;
        border-bottom: 3px solid #e5e7eb !important;
        padding: 4px 10px !important;
        font-size: 15px !important;
        font-weight: bold !important;
        height: auto !important;
        width: auto !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 【重點 2】功能函數 ---

def get_audio_html(text):
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
    try:
        response = requests.get(tts_url)
        if response.status_code == 200:
            b64 = base64.b64encode(response.content).decode()
            return f'<audio controls style="width:100%; height:38px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except: pass
    return ""

def get_sentence_structure(text):
    raw_parts = re.split(r'([、。！？])', text.strip())
    structure = []
    for part in raw_parts:
        if not part: continue
        if part in ['、', '。', '！', '？']:
            structure.append({"type": "punc", "content": part})
        else:
            tokens = [t for t in re.split(r'[ 　]+', part) if t] if " " in part or "　" in part else [t for t in re.split(f"({'|'.join(['は','が','を','に','へ','と','も','で','の','から','まで'])})", part) if t]
            for token in tokens: structure.append({"type": "word", "content": token})
    return structure

@st.cache_data(ttl=60)
def load_data():
    SHEET_ID = "12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA"
    GID = "1337973082"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(subset=["日文原文", "中文意譯"]), {"unit": "單元", "ch": "章節", "ja": "日文原文", "cn": "中文意譯"}
    except: return None, None

def reset_state():
    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct = [], [], [], False

# --- 【重點 3】執行邏輯 ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 10
    reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄與資料篩選
    unit_list = sorted(df[cols['unit']].astype(str).unique())
    sel_unit = st.sidebar.selectbox("單元", unit_list)
    unit_df = df[df[cols['unit']].astype(str) == sel_unit]
    sel_start_ch = st.sidebar.selectbox("章節", sorted(unit_df[cols['ch']].astype(str).unique()))
    filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
    
    # 題數控制
    cs1, cs2 = st.sidebar.columns(2)
    if cs1.button("➖ 少"): st.session_state.num_q = max(1, st.session_state.num_q-1); st.rerun()
    if cs2.button("➕ 多"): st.session_state.num_q = min(len(filtered_df), st.session_state.num_q+1); st.rerun()
    
    preview_mode = st.sidebar.checkbox("📖 預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if preview_mode:
        st.subheader("📖 預習清單")
        for i, item in enumerate(quiz_list):
            st.markdown(f"**{i+1}. {item[cols['cn']]}**")
            st.caption(item[cols['ja']])
            st.markdown(get_audio_html(item[cols['ja']]), unsafe_allow_html=True)
            st.write("---")
    
    elif st.session_state.q_idx < len(quiz_list):
        # 測驗主畫面
        q = quiz_list[st.session_state.q_idx]
        ja_raw, cn_text = str(q[cols['ja']]).strip(), q[cols['cn']]
        sentence_struct = get_sentence_structure(ja_raw)
        word_tokens = [s['content'] for s in sentence_struct if s['type'] == 'word']
        
        if not st.session_state.shuf:
            st.session_state.shuf = list(word_tokens); random.shuffle(st.session_state.shuf)

        st.caption(f"Q{st.session_state.q_idx + 1} | {cn_text}")

        # 答案填充框
        current_ans_list = list(st.session_state.ans)
        html_content = '<div class="res-box">'
        for item in sentence_struct:
            if item['type'] == 'punc': html_content += f'<span class="punc-display">{item["content"]}</span>'
            else:
                val = current_ans_list.pop(0) if current_ans_list else ""
                html_content += f'<div class="word-slot">{val}</div>'
        html_content += '</div>'
        st.markdown(html_content, unsafe_allow_html=True)

        # 導航鍵
        n1, n2, n3, n4 = st.columns(4)
        if n1.button("⏮上題"): 
            if st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        if n2.button("⏭下題"): 
            if st.session_state.q_idx < len(quiz_list)-1: st.session_state.q_idx += 1; reset_state(); st.rerun()
        if n3.button("🔄重填"): reset_state(); st.rerun()
        if n4.button("⬅退回"):
            if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

        st.write("---")
        
        # --- 核心優化：零間隔流式按鈕 ---
        num_shuf = len(st.session_state.shuf)
        word_cols = st.columns(num_shuf if num_shuf > 0 else 1)
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                if word_cols[idx].button(t, key=f"btn_{idx}"):
                    st.session_state.ans.append(t); st.session_state.used_history.append(idx); st.rerun()

        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            if st.button("🔍 CHECK ANSWER", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(word_tokens):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("不對喔！")

        if st.session_state.is_correct:
            st.success("正解！")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("CONTINUE ➡️", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
    else:
        st.header("🎊 練習完成！")
        if st.button("RESTART 🔄", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
