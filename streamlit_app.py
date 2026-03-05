"""
================================================================
【日文結構練習器 - v3.1 穩定修正版】
版本編號：v3.1.20260306
核心修復：
1. 修正預習模式：精確限定 CSS 範圍，避免干擾展開元件與導航。
2. 保持 Duolingo 排列：測驗單字按鈕維持流式併排，節省手機空間。
3. 語音補強：維持 Base64 技術解決 iPhone 灰色按鈕。
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 【重點 1】精確範圍 CSS (僅作用於測驗按鈕) ---
st.set_page_config(page_title="🇯🇵 日文重組 v3.1", layout="wide")

st.markdown("""
    <style>
    /* 1. 只在『測驗區』啟用 Flexbox 併排，不干擾預習模式與側欄 */
    .quiz-zone [data-testid="column"] {
        flex: 0 1 auto !important;
        width: auto !important;
        min-width: 0px !important;
    }
    .quiz-zone [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 8px !important;
        justify-content: flex-start !important;
    }

    /* 2. 答案區：卡片式設計 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 8px; 
        background-color: #ffffff; padding: 18px; 
        border-radius: 16px; border: 2px solid #e5e7eb; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        min-height: 90px; margin-bottom: 15px; align-items: center; 
    }
    .word-slot { 
        min-width: 50px; height: 40px; border-bottom: 3px solid #e5e7eb; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 20px; color: #1cb0f6; font-weight: bold; 
    }
    .punc-display { font-size: 22px; color: #afafaf; font-weight: bold; }

    /* 3. 仿 Duolingo 立體按鈕 */
    div.stButton > button {
        border-radius: 12px !important;
        border: 2px solid #e5e7eb !important;
        border-bottom: 4px solid #e5e7eb !important;
        background-color: white !important;
        color: #4b4b4b !important;
        padding: 8px 16px !important;
        font-size: 17px !important;
        font-weight: bold !important;
    }
    div.stButton > button:active {
        border-bottom: 2px solid #e5e7eb !important;
        transform: translateY(2px) !important;
    }
    
    /* 修正頂部空白 */
    .block-container { padding-top: 2rem !important; }
    </style>
""", unsafe_allow_html=True)

# --- 【重點 2】功能函數 (音訊與結構) ---

def get_audio_html(text):
    """Base64 音訊解決 iPhone 灰色按鈕問題"""
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
    try:
        response = requests.get(tts_url)
        if response.status_code == 200:
            b64 = base64.b64encode(response.content).decode()
            return f'<audio controls style="width:100%; height:42px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
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
            if " " in part or "　" in part:
                tokens = [t for t in re.split(r'[ 　]+', part) if t]
            else:
                particles = ['は', 'が', 'を', 'に', 'へ', 'と', 'も', 'で', 'の', 'から', 'まで']
                pattern = f"({'|'.join(particles)})"
                tokens = [t for t in re.split(pattern, part) if t]
            for token in tokens:
                structure.append({"type": "word", "content": token})
    return structure

@st.cache_data(ttl=60)
def load_data():
    SHEET_ID = "12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA"
    GID = "1337973082"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        COL_UNIT, COL_CH, COL_JA, COL_CN = "單元", "章節", "日文原文", "中文意譯"
        df = df.dropna(subset=[COL_JA, COL_CN])
        return df, {"unit": COL_UNIT, "ch": COL_CH, "ja": COL_JA, "cn": COL_CN}
    except: return None, None

def reset_state():
    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct = [], [], [], False

# --- 【重點 3】主程式執行邏輯 ---

if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 10
    reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄
    st.sidebar.header("⚙️ 練習設定")
    unit_list = sorted(df[cols['unit']].astype(str).unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", unit_list)
    unit_df = df[df[cols['unit']].astype(str) == sel_unit]
    sel_start_ch = st.sidebar.selectbox("2. 起始章節", sorted(unit_df[cols['ch']].astype(str).unique()))
    filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
    
    c_side1, c_side2 = st.sidebar.columns(2)
    if c_side1.button("➖ 少題"):
        if st.session_state.num_q > 1: st.session_state.num_q -= 1; st.rerun()
    if c_side2.button("➕ 多題"):
        if st.session_state.num_q < len(filtered_df): st.session_state.num_q += 1; st.rerun()
    
    preview_mode = st.sidebar.checkbox("📖 開啟預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    # 切換條件重置
    cur_key = f"{sel_unit}-{sel_start_ch}-{st.session_state.num_q}"
    if 'last_key' not in st.session_state or st.session_state.last_key != cur_key:
        st.session_state.last_key, st.session_state.q_idx = cur_key, 0
        reset_state(); st.rerun()

    if preview_mode:
        st.subheader("📖 預習清單")
        # 預習模式不使用 quiz-zone 樣式，確保顯示正常
        for item in quiz_list:
            with st.expander(f"{item[cols['cn']]}", expanded=False):
                st.write(f"### {item[cols['ja']]}")
                st.markdown(get_audio_html(item[cols['ja']]), unsafe_allow_html=True)
    
    elif st.session_state.q_idx < len(quiz_list):
        # 進入測驗模式，包裝在 quiz-zone 內
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

        # 功能導航
        g1, g2, g3, g4 = st.columns(4)
        if g1.button("⬅️"): 
            if st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        if g2.button("➡️"): 
            if st.session_state.q_idx < len(quiz_list)-1: st.session_state.q_idx += 1; reset_state(); st.rerun()
        if g3.button("🔄"): reset_state(); st.rerun()
        if g4.button("退回"):
            if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

        st.write("---")
        # Duolingo 風格按鈕區
        row_btns = st.columns(len(st.session_state.shuf))
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                if row_btns[idx].button(t, key=f"btn_{idx}"):
                    st.session_state.ans.append(t); st.session_state.used_history.append(idx); st.rerun()

        st.markdown('</div>', unsafe_allow_html=True) # 結束 quiz-zone

        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            if st.button("CHECK 🔍", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(word_tokens):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("不對喔，再檢查一下！")

        if st.session_state.is_correct:
            st.success("正解！")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("CONTINUE ➡️", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
