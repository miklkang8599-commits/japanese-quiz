"""
================================================================
【日文結構練習器 - Duolingo 風格版】
版本編號：v3.0.20260306
更新時間：2026-03-06
設計重點：
1. 仿 Duolingo 流式佈局 (Flexbox Wrap)：按鈕隨文字長度自動排列。
2. 視覺優化：圓角卡片設計、加大字體、減少手機端滑動。
3. 頂部導航守護：確保主畫面優化不干擾選單功能。
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 【重點 1】Duolingo 風格 CSS 精算 ---
st.set_page_config(page_title="🇯🇵 日文重組 v3.0", layout="wide")

st.markdown("""
    <style>
    /* 1. 核心：強制主畫面 Column 變為 Flex 容器，模擬 Duolingo 流動排列 */
    [data-testid="stMain"] [data-testid="column"] {
        flex: 0 1 auto !important;
        width: auto !important;
        min-width: 0px !important;
    }
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 8px !important;
        justify-content: flex-start !important;
    }

    /* 2. 答案區：卡片式設計 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 10px; 
        background-color: #ffffff; padding: 20px; 
        border-radius: 18px; border: 2px solid #e5e7eb; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        min-height: 110px; margin-bottom: 15px; align-items: center; 
    }
    .word-slot { 
        min-width: 55px; height: 42px; border-bottom: 3px solid #e5e7eb; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 21px; color: #1cb0f6; font-weight: bold; 
    }
    .punc-display { font-size: 24px; color: #afafaf; font-weight: bold; }

    /* 3. 按鈕視覺：仿 Duolingo 圓角與陰影 */
    div.stButton > button {
        border-radius: 12px !important;
        border: 2px solid #e5e7eb !important;
        border-bottom: 4px solid #e5e7eb !important;
        background-color: white !important;
        color: #4b4b4b !important;
        padding: 8px 16px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        transition: all 0.1s !important;
    }
    div.stButton > button:active {
        border-bottom: 2px solid #e5e7eb !important;
        transform: translateY(2px) !important;
    }
    
    /* 4. 手機端間距壓縮 */
    .block-container { padding-top: 2.5rem !important; }
    </style>
""", unsafe_allow_html=True)

# --- 【重點 2】音訊與結構邏輯 (維持 v2.9 穩定版) ---

def get_audio_html(text):
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
    try:
        response = requests.get(tts_url)
        if response.status_code == 200:
            b64 = base64.b64encode(response.content).decode()
            return f'<audio controls style="width:100%; height:45px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
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

# --- 【重點 3】程式執行邏輯 ---

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

    cur_key = f"{sel_unit}-{sel_start_ch}-{st.session_state.num_q}"
    if 'last_key' not in st.session_state or st.session_state.last_key != cur_key:
        st.session_state.last_key, st.session_state.q_idx = cur_key, 0
        reset_state(); st.rerun()

    if preview_mode:
        st.subheader("📖 預習清單")
        for item in quiz_list:
            with st.expander(f"{item[cols['cn']]}", expanded=True):
                st.write(f"### {item[cols['ja']]}")
                st.markdown(get_audio_html(item[cols['ja']]), unsafe_allow_html=True)
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw, cn_text = str(q[cols['ja']]).strip(), q[cols['cn']]
        sentence_struct = get_sentence_structure(ja_raw)
        word_tokens = [s['content'] for s in sentence_struct if s['type'] == 'word']
        
        if not st.session_state.shuf:
            st.session_state.shuf = list(word_tokens); random.shuffle(st.session_state.shuf)

        st.caption(f"Q{st.session_state.q_idx + 1} | {cn_text}")

        # --- 渲染卡片式答案框 ---
        current_ans_list = list(st.session_state.ans)
        html_content = '<div class="res-box">'
        for item in sentence_struct:
            if item['type'] == 'punc': html_content += f'<span class="punc-display">{item["content"]}</span>'
            else:
                val = current_ans_list.pop(0) if current_ans_list else ""
                html_content += f'<div class="word-slot">{val}</div>'
        html_content += '</div>'
        st.markdown(html_content, unsafe_allow_html=True)

        # 功能導航鍵 (Duolingo 風格通常較緊湊)
        g1, g2, g3, g4 = st.columns(4)
        g1.button("⬅️", on_click=lambda: (setattr(st.session_state, 'q_idx', max(0, st.session_state.q_idx-1)), reset_state()))
        g2.button("➡️", on_click=lambda: (setattr(st.session_state, 'q_idx', min(len(quiz_list)-1, st.session_state.q_idx+1)), reset_state()))
        g3.button("🔄", on_click=reset_state)
        if g4.button("⬅️"):
            if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

        st.write("---")
        # --- 按鈕區：Duolingo 風格流式排列 ---
        # 這裡不限制行數，讓它自然換行
        row_btns = st.columns(len(st.session_state.shuf))
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                if row_btns[idx].button(t, key=f"btn_{idx}"):
                    st.session_state.ans.append(t); st.session_state.used_history.append(idx); st.rerun()

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
    else:
        st.header("🎊 練習完成！")
        if st.button("RESTART 🔄", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
