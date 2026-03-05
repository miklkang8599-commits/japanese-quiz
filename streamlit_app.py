"""
================================================================
【日文結構練習器 - v3.3 App 體驗強化版】
版本編號：v3.3.20260306
更新時間：2026-03-06
設計重點：
1. 突破網頁限制：極限壓縮 UI 組件間距，模擬原生 App 的沉浸感。
2. 流動式按鈕 (Inline-Flex)：模仿 Duolingo，按鈕不再死板併排。
3. 預習清單極簡化：移除所有多餘裝飾，僅保留文字與音訊。
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 【重點 1】App 級別空間壓縮 CSS ---
st.set_page_config(page_title="🇯🇵 日文重組 v3.3", layout="wide")

st.markdown("""
    <style>
    /* 1. 移除 Streamlit 所有預設邊距，把空間還給作答區 */
    .block-container { padding: 1rem 0.5rem !important; }
    [data-testid="stHeader"] { display: none; } /* 隱藏頂部空白欄 */
    
    /* 2. 測驗按鈕區：模仿 App 的流動排列 */
    .quiz-zone [data-testid="column"] {
        flex: 0 1 auto !important; width: auto !important; min-width: 0px !important;
    }
    .quiz-zone [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important; gap: 6px !important; justify-content: flex-start !important;
    }

    /* 3. 答案卡片設計：扁平化以節省高度 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 6px; 
        background-color: #ffffff; padding: 12px; 
        border-radius: 12px; border: 2px solid #e5e7eb; 
        min-height: 80px; margin-bottom: 8px; align-items: center; 
    }
    .word-slot { 
        min-width: 45px; height: 35px; border-bottom: 2px solid #e5e7eb; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 19px; color: #1cb0f6; font-weight: bold; 
    }
    .punc-display { font-size: 20px; color: #afafaf; font-weight: bold; }

    /* 4. 仿 Duolingo 按鈕：微調大小以適應手機直立 */
    div.stButton > button {
        border-radius: 10px !important;
        border: 2px solid #e5e7eb !important;
        border-bottom: 3px solid #e5e7eb !important;
        background-color: white !important;
        padding: 6px 12px !important;
        font-size: 16px !important;
        font-weight: bold !important;
    }
    
    /* 5. 預習清單極簡化 */
    .preview-line { margin: 5px 0; padding-bottom: 10px; border-bottom: 1px solid #f0f0f0; }
    </style>
""", unsafe_allow_html=True)

# --- 【重點 2】Base64 音訊嵌入 ---
def get_audio_html(text):
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
    try:
        response = requests.get(tts_url)
        if response.status_code == 200:
            b64 = base64.b64encode(response.content).decode()
            return f'<audio controls style="width:100%; height:35px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except: pass
    return ""

# --- 【重點 3】結構拆解與資料讀取 ---
def get_sentence_structure(text):
    raw_parts = re.split(r'([、。！？])', text.strip())
    structure = []
    for part in raw_parts:
        if not part: continue
        if part in ['、', '。', '！', '？']:
            structure.append({"type": "punc", "content": part})
        else:
            tokens = [t for t in re.split(r'[ 　]+', part) if t] if " " in part or "　" in part else [t for t in re.split(f"({'|'.join(['は','が','を','に','へ','と','訓練','も','で','の','から','まで'])})", part) if t]
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

# --- 【重點 4】主程式 ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 10
    reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄簡化
    unit_list = sorted(df[cols['unit']].astype(str).unique())
    sel_unit = st.sidebar.selectbox("單元", unit_list)
    unit_df = df[df[cols['unit']].astype(str) == sel_unit]
    sel_start_ch = st.sidebar.selectbox("章節", sorted(unit_df[cols['ch']].astype(str).unique()))
    filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
    
    c_s1, c_s2 = st.sidebar.columns(2)
    if c_s1.button("➖ 少"): st.session_state.num_q = max(1, st.session_state.num_q-1); st.rerun()
    if c_s2.button("➕ 多"): st.session_state.num_q = min(len(filtered_df), st.session_state.num_q+1); st.rerun()
    
    preview_mode = st.sidebar.checkbox("📖 預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if preview_mode:
        st.subheader("📖 預習")
        for i, item in enumerate(quiz_list):
            st.markdown(f"**{i+1}. {item[cols['cn']]}**")
            st.caption(item[cols['ja']])
            st.markdown(get_audio_html(item[cols['ja']]), unsafe_allow_html=True)
            st.markdown('<div class="preview-line"></div>', unsafe_allow_html=True)
    
    elif st.session_state.q_idx < len(quiz_list):
        st.markdown('<div class="quiz-zone">', unsafe_allow_html=True)
        q = quiz_list[st.session_state.q_idx]
        ja_raw, cn_text = str(q[cols['ja']]).strip(), q[cols['cn']]
        sentence_struct = get_sentence_structure(ja_raw)
        word_tokens = [s['content'] for s in sentence_struct if s['type'] == 'word']
        
        if not st.session_state.shuf:
            st.session_state.shuf = list(word_tokens); random.shuffle(st.session_state.shuf)

        st.caption(f"Q{st.session_state.q_idx + 1} | {cn_text}")

        # 答案框
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
        if n1.button("⏮上一題"): 
            if st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        if n2.button("⏭下一題"): 
            if st.session_state.q_idx < len(quiz_list)-1: st.session_state.q_idx += 1; reset_state(); st.rerun()
        if n3.button("🔄重填"): reset_state(); st.rerun()
        if n4.button("⬅退回"):
            if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

        st.write("---")
        # Duolingo 風格流動按鈕
        btn_cols = st.columns(len(st.session_state.shuf))
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                if btn_cols[idx].button(t, key=f"btn_{idx}"):
                    st.session_state.ans.append(t); st.session_state.used_history.append(idx); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            if st.button("🔍 CHECK", type="primary", use_container_width=True):
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
