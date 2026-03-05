"""
================================================================
【日文結構練習器 - 手機直立強制併排版】
版本編號：v2.8.20260306
核心修復：
1. 強制 CSS 覆蓋：解決 Streamlit 手機端自動堆疊問題，實現按鈕併排。
2. 預習模式復原：確保側邊欄功能開關邏輯正確。
3. 空間精算：針對 iPhone 直立螢幕進行組件高度微調。
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 【重點 1】極限空間優化與強制併排 CSS ---
st.set_page_config(page_title="🇯🇵 日文重組 v2.8", layout="wide")

st.markdown("""
    <style>
    /* 1. 強制讓 Streamlit 的列在手機上不堆疊 (核心修復) */
    [data-testid="column"] {
        width: calc(33% - 1rem) !important;
        flex: 1 1 calc(33% - 1rem) !important;
        min-width: calc(33% - 1rem) !important;
    }
    
    /* 2. 移除手機端頂部空白 */
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    
    /* 3. 答案顯示區：精簡版面 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 4px; 
        background-color: #f0f7ff; padding: 10px; 
        border-radius: 10px; border: 1.5px solid #bcd7ff; 
        min-height: 70px; margin-bottom: 8px; align-items: center; 
    }
    .word-slot { 
        min-width: 45px; height: 35px; border-bottom: 2px solid #93c5fd; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 18px; color: #1e40af; font-weight: bold; 
    }
    .punc-display { font-size: 20px; color: #94a3b8; font-weight: bold; }

    /* 4. 按鈕樣式優化 */
    div.stButton > button {
        border-radius: 6px !important;
        height: 2.8em !important;
        font-size: 15px !important;
        padding: 0px !important;
        margin-bottom: 2px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 【重點 2】Base64 音訊 (穩定解決灰色問題) ---
def get_audio_html(text):
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
    try:
        response = requests.get(tts_url)
        if response.status_code == 200:
            b64 = base64.b64encode(response.content).decode()
            return f'<audio controls style="width:100%; height:35px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except: pass
    return ""

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
            tokens = [t for t in re.split(r'[ 　]+', part) if t] if " " in part or "　" in part else [t for t in re.split(f"({'|'.join(['は','が','を','に','へ','と','も','で','の','から','まで'])})", part) if t]
            for token in tokens: structure.append({"type": "word", "content": token})
    return structure

def reset_state():
    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct = [], [], [], False

if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 10
    reset_state()

df, cols = load_data()

# --- 【重點 4】UI 邏輯 (預習與測驗切換) ---
if df is not None:
    st.sidebar.header("⚙️ 設定")
    unit_list = sorted(df[cols['unit']].astype(str).unique())
    sel_unit = st.sidebar.selectbox("1. 單元", unit_list)
    unit_df = df[df[cols['unit']].astype(str) == sel_unit]
    sel_start_ch = st.sidebar.selectbox("2. 章節", sorted(unit_df[cols['ch']].astype(str).unique()))
    filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
    
    # 題數按鈕
    c1, c2 = st.sidebar.columns(2)
    if c1.button("➖少題"): 
        if st.session_state.num_q > 1: st.session_state.num_q -= 1; st.rerun()
    if c2.button("➕多題"): 
        if st.session_state.num_q < len(filtered_df): st.session_state.num_q += 1; st.rerun()
    
    preview_mode = st.sidebar.checkbox("📖 開啟預習模式", value=False)
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    # 切換條件重置
    cur_key = f"{sel_unit}-{sel_start_ch}-{st.session_state.num_q}"
    if 'last_key' not in st.session_state or st.session_state.last_key != cur_key:
        st.session_state.last_key = cur_key
        st.session_state.q_idx = 0
        reset_state(); st.rerun()

    # --- 預習模式內容 ---
    if preview_mode:
        st.subheader("📖 預習清單")
        for item in quiz_list:
            with st.expander(f"{item[cols['cn']]}", expanded=False):
                st.write(item[cols['ja']])
                st.markdown(get_audio_html(item[cols['ja']]), unsafe_allow_html=True)
    
    # --- 測驗模式內容 ---
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw, cn_text = str(q[cols['ja']]).strip(), q[cols['cn']]
        sentence_struct = get_sentence_structure(ja_raw)
        word_tokens = [s['content'] for s in sentence_struct if s['type'] == 'word']
        
        if not st.session_state.shuf:
            st.session_state.shuf = list(word_tokens); random.shuffle(st.session_state.shuf)

        st.caption(f"Q{st.session_state.q_idx + 1} | {cn_text}")

        # 答案框渲染
        current_ans_list = list(st.session_state.ans)
        html_content = '<div class="res-box">'
        for item in sentence_struct:
            if item['type'] == 'punc': html_content += f'<span class="punc-display">{item["content"]}</span>'
            else:
                val = current_ans_list.pop(0) if current_ans_list else ""
                html_content += f'<div class="word-slot">{val}</div>'
        html_content += '</div>'
        st.markdown(html_content, unsafe_allow_html=True)

        # 功能鍵 (強迫 4 欄併排)
        g1, g2, g3, g4 = st.columns(4)
        if g1.button("⬅️上題"): 
            if st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        if g2.button("➡️下題"): 
            if st.session_state.q_idx < len(quiz_list)-1: st.session_state.q_idx += 1; reset_state(); st.rerun()
        if g3.button("🔄重填"): reset_state(); st.rerun()
        if g4.button("⬅️退回"): 
            if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

        st.write("---")
        # 按鈕區 (強迫 3 欄併排，節省空間)
        cols_per_row = 3
        for i in range(0, len(st.session_state.shuf), cols_per_row):
            row_btns = st.columns(cols_per_row)
            for j in range(cols_per_row):
                idx = i + j
                if idx < len(st.session_state.shuf) and idx not in st.session_state.used_history:
                    if row_btns[j].button(st.session_state.shuf[idx], key=f"btn_{idx}"):
                        st.session_state.ans.append(st.session_state.shuf[idx]); st.session_state.used_history.append(idx); st.rerun()

        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(word_tokens):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對！")

        if st.session_state.is_correct:
            st.success("正解！")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("下一題 ➡️", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
