"""
================================================================
【日文結構練習器 - 排版修正版】
版本編號：v2.9.20260306
更新時間：2026-03-06
重點標註：精確化 CSS 作用範圍，修復頂部消失問題，保持手機直立按鈕併排。
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 【重點 1】精確範圍 CSS 優化 ---
st.set_page_config(page_title="🇯🇵 日文重組 v2.9", layout="wide")

st.markdown("""
    <style>
    /* 1. 只針對『主內容區』的列進行強制併排，不影響頂部與側邊欄 */
    [data-testid="stMain"] [data-testid="column"] {
        width: calc(33% - 0.5rem) !important;
        flex: 1 1 calc(33% - 0.5rem) !important;
        min-width: calc(33% - 0.5rem) !important;
    }
    
    /* 2. 修正頂部空白，確保不遮擋 */
    .block-container { padding-top: 2rem !important; }

    /* 3. 答案顯示區優化 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 5px; 
        background-color: #f0f7ff; padding: 12px; 
        border-radius: 12px; border: 1.5px solid #bcd7ff; 
        min-height: 80px; margin-bottom: 10px; align-items: center; 
    }
    .word-slot { 
        min-width: 48px; height: 38px; border-bottom: 2.5px solid #93c5fd; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 20px; color: #1e40af; font-weight: bold; 
    }
    .punc-display { font-size: 22px; color: #94a3b8; font-weight: bold; }

    /* 4. 按鈕視覺精修 */
    div.stButton > button {
        border-radius: 6px !important;
        height: 2.8em !important;
        font-size: 15px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 【重點 2】Base64 音訊 (修復灰色播放器) ---
def get_audio_html(text):
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
    try:
        response = requests.get(tts_url)
        if response.status_code == 200:
            b64 = base64.b64encode(response.content).decode()
            return f'<audio controls style="width:100%; height:40px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except: pass
    return ""

# --- 【重點 3】結構化拆解邏輯 ---
def get_sentence_structure(text):
    raw_parts = re.split(r'([、。！？])', text.strip())
    structure = []
    for part in raw_parts:
        if not part: continue
        if part in ['、', '。', '！', '？']:
            structure.append({"type": "punc", "content": part})
        else:
            # 支援空格拆分
            tokens = [t for t in re.split(r'[ 　]+', part) if t] if " " in part or "　" in part else [t for t in re.split(f"({'|'.join(['は','が','を','に','へ','と','も','引','で','の','から','まで'])})", part) if t]
            for token in tokens: structure.append({"type": "word", "content": token})
    return structure

def reset_state():
    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct = [], [], [], False

if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 10
    reset_state()

df, cols = load_data()

# --- 【重點 4】主程式頁面邏輯 ---
if df is not None:
    # 側邊欄控制
    st.sidebar.header("⚙️ 練習設定")
    unit_list = sorted(df[cols['unit']].astype(str).unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", unit_list)
    unit_df = df[df[cols['unit']].astype(str) == sel_unit]
    sel_start_ch = st.sidebar.selectbox("2. 起始章節", sorted(unit_df[cols['ch']].astype(str).unique()))
    filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
    
    # 題數控制
    c1, c2 = st.sidebar.columns(2)
    if c1.button("➖ 少一題"):
        if st.session_state.num_q > 1: st.session_state.num_q -= 1; st.rerun()
    if c2.button("➕ 多一題"):
        if st.session_state.num_q < len(filtered_df): st.session_state.num_q += 1; st.rerun()
    
    preview_mode = st.sidebar.checkbox("📖 開啟預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    # 狀態守衛：條件變動即重置
    cur_key = f"{sel_unit}-{sel_start_ch}-{st.session_state.num_q}"
    if 'last_key' not in st.session_state or st.session_state.last_key != cur_key:
        st.session_state.last_key = cur_key
        st.session_state.q_idx = 0
        reset_state(); st.rerun()

    # --- 畫面渲染 ---
    if preview_mode:
        st.subheader("📖 課文預習模式")
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

        st.caption(f"Q{st.session_state.q_idx + 1} | {cn_text}")

        # 答案框顯示
        current_ans_list = list(st.session_state.ans)
        html_content = '<div class="res-box">'
        for item in sentence_struct:
            if item['type'] == 'punc': html_content += f'<span class="punc-display">{item["content"]}</span>'
            else:
                val = current_ans_list.pop(0) if current_ans_list else ""
                html_content += f'<div class="word-slot">{val}</div>'
        html_content += '</div>'
        st.markdown(html_content, unsafe_allow_html=True)

        # 導航鍵 (4 欄)
        g1, g2, g3, g4 = st.columns(4)
        if g1.button("⬅️上題"): 
            if st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        if g2.button("➡️下題"): 
            if st.session_state.q_idx < len(quiz_list)-1: st.session_state.q_idx += 1; reset_state(); st.rerun()
        if g3.button("🔄重填"): reset_state(); st.rerun()
        if g4.button("⬅️退回"): 
            if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

        st.write("---")
        # 按鈕區 (手機強制 3 欄併排)
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
                else: st.error("順序不對喔！")

        if st.session_state.is_correct:
            st.success("正解！")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("下一題 ➡️", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
    else:
        st.header("🎊 練習完成！")
        if st.button("🔄 重新開始", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
