"""
================================================================
【技術演進與解決邏輯追蹤表】
----------------------------------------------------------------
版本歷史與邏輯變更：
- v3.8~v3.9 (URL 通訊法)：
  邏輯：HTML <a> 標籤 + query_params。
  失敗原因：手機瀏覽器對 URL 變動的反應速度不一，導致「點擊沒反應」。

- v3.9.2 (CSS 強制併排法 - 目前版本)：
  邏輯：回歸 st.button()，但使用「深度選擇器」覆蓋框架行為。
  1. 解決點擊：使用原生組件，確保點擊 100% 反應。
  2. 解決併排：透過 CSS [data-testid="column"] { width: auto !important } 
     強行拆解 Streamlit 的手機端 100% 寬度鎖定。
  3. 解決緊貼：將 gap 設為 2px，實現 Duolingo 緊湊排版。
----------------------------------------------------------------
更新時間：2026-03-06
設計重點：1.單字池置中 2.格位縮小 3.功能鍵置底 4.預習模式全展開
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 【重點 1】深度選擇器 CSS (強制手機併排且緊貼) ---
st.set_page_config(page_title="🇯🇵 日文重組 v3.9.2", layout="wide")

st.markdown("""
    <style>
    /* 1. 強制讓所有欄位在手機上不換行，且寬度自適應文字 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 3px !important; /* 按鈕間的極小間距 */
        align-items: flex-start !important;
    }
    [data-testid="column"] {
        width: auto !important;
        flex: 0 1 auto !important;
        min-width: 0px !important;
        padding: 0px !important;
    }

    /* 2. 移除手機端多餘邊距 */
    .block-container { padding: 1rem 0.5rem !important; }
    [data-testid="stHeader"] { display: none; }
    
    /* 3. 答案區：極致扁平化 (格位縮小) */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 4px; 
        background-color: #f9fafb; padding: 10px; 
        border-radius: 10px; border: 1.5px solid #e5e7eb; 
        min-height: 60px; margin-bottom: 5px; align-items: center; 
    }
    .word-slot { 
        min-width: 32px; height: 30px; border-bottom: 2px solid #cbd5e1; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 17px; color: #1cb0f6; font-weight: bold; margin: 0 2px;
    }

    /* 4. 仿 Duolingo 按鈕：確保在手機上也是小而美 */
    div.stButton > button {
        border-radius: 8px !important;
        border: 1px solid #e5e7eb !important;
        border-bottom: 3px solid #e5e7eb !important;
        background-color: white !important;
        padding: 4px 10px !important;
        font-size: 15px !important;
        font-weight: bold !important;
        width: auto !important; /* 核心：不佔滿寬度 */
    }
    </style>
""", unsafe_allow_html=True)

# --- 【重點 2】音訊與結構處理 ---
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
        return df.dropna(subset=["日文原文", "中文意譯"]), {"unit": "單元", "ch": "章節", "ja": "日文原文", "cn": "中文意譯"}
    except: return None, None

def reset_state():
    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct = [], [], [], False

# --- 【重點 3】主程式邏輯 ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 10
    reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄
    unit_list = sorted(df[cols['unit']].astype(str).unique())
    sel_unit = st.sidebar.selectbox("單元", unit_list)
    unit_df = df[df[cols['unit']].astype(str) == sel_unit]
    sel_start_ch = st.sidebar.selectbox("章節", sorted(unit_df[cols['ch']].astype(str).unique()))
    filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
    
    cs1, cs2 = st.sidebar.columns(2)
    if cs1.button("➖ 少"): st.session_state.num_q = max(1, st.session_state.num_q-1); st.rerun()
    if cs2.button("➕ 多"): st.session_state.num_q = min(len(filtered_df), st.session_state.num_q+1); st.rerun()
    
    preview_mode = st.sidebar.checkbox("📖 預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if preview_mode:
        st.subheader("📖 預習清單")
        for i, item in enumerate(quiz_list):
            st.markdown(f"**{i+1}. {item[cols['cn']]}**")
            st.write(item[cols['ja']])
            st.markdown(get_audio_html(item[cols['ja']]), unsafe_allow_html=True)
            st.write("---")
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw, cn_text = str(q[cols['ja']]).strip(), q[cols['cn']]
        sentence_struct = get_sentence_structure(ja_raw)
        word_tokens = [s['content'] for s in sentence_struct if s['type'] == 'word']
        
        if not st.session_state.shuf:
            st.session_state.shuf = list(word_tokens); random.shuffle(st.session_state.shuf)

        st.caption(f"Q{st.session_state.q_idx + 1} | {cn_text}")

        # --- A. 答案展示區 ---
        current_ans_list = list(st.session_state.ans)
        html_ans = '<div class="res-box">'
        for item in sentence_struct:
            if item['type'] == 'punc': html_ans += f'<span style="font-size:18px; color:#94a3b8; font-weight:bold;">{item["content"]}</span>'
            else:
                val = current_ans_list.pop(0) if current_ans_list else ""
                html_ans += f'<div class="word-slot">{val}</div>'
        html_ans += '</div>'
        st.markdown(html_ans, unsafe_allow_html=True)

        st.write("---")

        # --- B. 單字按鈕池 (位置對調：上移) ---
        # 使用 st.columns(len) 但配合重點 1 的 CSS 強制併排
        n_btns = len(st.session_state.shuf)
        btn_cols = st.columns(n_btns if n_btns > 0 else 1)
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                if btn_cols[idx].button(t, key=f"btn_{idx}"):
                    st.session_state.ans.append(t)
                    st.session_state.used_history.append(idx)
                    st.rerun()

        st.write(" ")

        # --- C. 功能導航鍵 (位置對調：下移) ---
        nav_cols = st.columns(4)
        if nav_cols[0].button("⏮上"): 
            if st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        if nav_cols[1].button("⏭下"): 
            if st.session_state.q_idx < len(quiz_list)-1: st.session_state.q_idx += 1; reset_state(); st.rerun()
        if nav_cols[2].button("🔄重"): reset_state(); st.rerun()
        if nav_cols[3].button("⬅退"):
            if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

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
