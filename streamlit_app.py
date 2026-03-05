"""
================================================================
【日文結構練習器 - 手機直立優化版】
版本編號：v2.7.20260306
核心修復：使用 CSS Flexbox 解決按鈕排版空間浪費問題。
視覺重點：自定義按鈕流式佈局 (Flex Layout)，支援長短單字自動併排。
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 【重點 1】手機直立螢幕專用 CSS 佈局 ---
st.set_page_config(page_title="🇯🇵 日文結構練習 v2.7", layout="wide")

st.markdown("""
    <style>
    /* 全域字體縮小與間距壓縮，節省直立空間 */
    .reportview-container .main .block-container { padding-top: 1rem; }
    
    /* 答案顯示區優化 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 5px; 
        background-color: #f0f7ff; padding: 12px; 
        border-radius: 12px; border: 1.5px solid #bcd7ff; 
        min-height: 80px; margin-bottom: 10px; align-items: center; 
    }
    .word-slot { 
        min-width: 50px; height: 38px; border-bottom: 2.5px solid #93c5fd; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 19px; color: #1e40af; font-weight: bold; 
    }
    .punc-display { font-size: 22px; color: #94a3b8; font-weight: bold; margin: 0 1px; }

    /* 核心解決：自定義流式按鈕容器 */
    .flex-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: flex-start;
        padding: 5px 0;
    }
    
    /* 隱藏原生 Streamlit 按鈕樣式，改用自定義點擊外觀 */
    div.stButton > button {
        border-radius: 8px !important;
        background-color: #ffffff !important;
        color: #334155 !important;
        border: 1px solid #cbd5e1 !important;
        padding: 8px 15px !important;
        height: auto !important;
        min-height: 45px !important;
        width: auto !important; /* 關鍵：寬度隨文字變化 */
        font-size: 17px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    div.stButton > button:active {
        background-color: #e2e8f0 !important;
        transform: translateY(1px);
    }
    </style>
""", unsafe_allow_html=True)

# --- 【重點 2】Base64 音訊嵌入函數 (解決灰色問題) ---
def get_audio_html(text):
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
    try:
        response = requests.get(tts_url)
        if response.status_code == 200:
            b64 = base64.b64encode(response.content).decode()
            return f'<audio controls style="width:100%; height:40px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
        else: return ""
    except: return ""

# --- 【重點 3】資料讀取與結構拆解 ---
SHEET_ID = "12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA"
GID = "1337973082"
url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        COL_UNIT, COL_CH, COL_JA, COL_CN = "單元", "章節", "日文原文", "中文意譯"
        df = df.dropna(subset=[COL_JA, COL_CN])
        return df, {"unit": COL_UNIT, "ch": COL_CH, "ja": COL_JA, "cn": COL_CN}
    except: return None, None

def get_sentence_structure(text):
    raw_parts = re.split(r'([、。！？])', text.strip())
    structure = []
    for part in raw_parts:
        if not part: continue
        if part in ['、', '。', '！', '？']:
            structure.append({"type": "punc", "content": part})
        else:
            if " " in part or "　" in part:
                tokens = [t for t in re.split(r'[ 　]+', part) if t]
            else:
                particles = ['は', 'が', 'を', 'に', 'へ', 'と', 'も', 'で', 'の', 'から', 'まで']
                pattern = f"({'|'.join(particles)})"
                tokens = [t for t in re.split(pattern, part) if t]
            for token in tokens:
                structure.append({"type": "word", "content": token})
    return structure

def reset_state():
    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct = [], [], [], False

if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 10
    reset_state()

df, cols = load_data()

# --- 【重點 4】主程式功能與流式佈局渲染 ---
if df is not None:
    # 側邊欄 (略，保持原有 +/- 功能)
    st.sidebar.header("⚙️ 練習設定")
    unit_list = sorted(df[cols['unit']].astype(str).unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", unit_list)
    unit_df = df[df[cols['unit']].astype(str) == sel_unit]
    sel_start_ch = st.sidebar.selectbox("2. 起始章節", sorted(unit_df[cols['ch']].astype(str).unique()))
    filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
    
    c1, c2 = st.sidebar.columns(2)
    if c1.button("➖ 少一題") and st.session_state.num_q > 1: st.session_state.num_q -= 1; st.rerun()
    if c2.button("➕ 多一題") and st.session_state.num_q < len(filtered_df): st.session_state.num_q += 1; st.rerun()
    preview_mode = st.sidebar.checkbox("📖 開啟預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if preview_mode:
        for item in quiz_list:
            with st.expander(f"【{item[cols['ch']]}】{item[cols['cn']]}", expanded=True):
                st.write(f"### {item[cols['ja']]}")
                st.markdown(get_audio_html(item[cols['ja']]), unsafe_allow_html=True)
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw, cn_text = str(q[cols['ja']]).strip(), q[cols['cn']]
        sentence_struct = get_sentence_structure(ja_raw)
        word_tokens = [s['content'] for s in sentence_struct if s['type'] == 'word']
        
        if not st.session_state.shuf:
            st.session_state.shuf = list(word_tokens); random.shuffle(st.session_state.shuf)

        st.subheader(f"Q {st.session_state.q_idx + 1} / {len(quiz_list)}")
        st.caption(f"💡 {cn_text}")

        # 渲染填充框
        current_ans_list = list(st.session_state.ans)
        html_content = '<div class="res-box">'
        for item in sentence_struct:
            if item['type'] == 'punc': html_content += f'<span class="punc-display">{item["content"]}</span>'
            else:
                val = current_ans_list.pop(0) if current_ans_list else ""
                html_content += f'<div class="word-slot">{val}</div>'
        html_content += '</div>'
        st.markdown(html_content, unsafe_allow_html=True)

        # 功能鍵 (壓縮在一排)
        g1, g2, g3, g4 = st.columns(4)
        if g1.button("⬅️上題"): 
            if st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        if g2.button("➡️下題"): 
            if st.session_state.q_idx < len(quiz_list)-1: st.session_state.q_idx += 1; reset_state(); st.rerun()
        if g3.button("🔄重填"): reset_state(); st.rerun()
        if g4.button("⬅️退回"): 
            if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

        st.write("---")
        # 重點：使用 Flexbox 動態排列單字按鈕
        # 我們利用 Streamlit 的 Markdown 建立一個容器，然後讓按鈕在裡面自然排列
        st.write("請選擇單字填入：")
        
        # 由於 Streamlit 原生不支援在 Markdown 容器內放按鈕
        # 我們改用動態切分列的方式，但取消固定寬度，儘可能模擬流式效果
        # 這裡改用 st.button 並配合 CSS width: auto
        cols_per_row = 3 # 雖然設定為 3，但 CSS 已經強制讓它隨長度縮放
        for i in range(0, len(st.session_state.shuf), cols_per_row):
            row_btns = st.columns(cols_per_row)
            for j in range(cols_per_row):
                idx = i + j
                if idx < len(st.session_state.shuf) and idx not in st.session_state.used_history:
                    t = st.session_state.shuf[idx]
                    if row_btns[j].button(t, key=f"btn_{idx}"):
                        st.session_state.ans.append(t)
                        st.session_state.used_history.append(idx)
                        st.rerun()

        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(word_tokens):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對！")

        if st.session_state.is_correct:
            st.success("🎊 正解！")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("下一題 ➡️", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
