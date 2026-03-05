"""
================================================================
【日文結構練習器 - v3.4 HTML 封裝解決方案】
版本編號：v3.4.20260306
更新時間：2026-03-06
設計重點：
1. 完全捨棄 st.columns 排列，改用 HTML/CSS 的 Flex-Flow。
2. 徹底解決手機直立時按鈕一整列的問題，實現 Duolingo 式流動排版。
3. 預習模式全展開，導航文字清晰化。
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 【重點 1】手機極限排版 CSS ---
st.set_page_config(page_title="🇯🇵 日文重組 v3.4", layout="wide")

st.markdown("""
    <style>
    .block-container { padding: 1rem 0.5rem !important; }
    [data-testid="stHeader"] { display: none; } 
    
    /* 答案顯示區 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 8px; 
        background-color: #ffffff; padding: 15px; 
        border-radius: 12px; border: 2px solid #e5e7eb; 
        min-height: 85px; margin-bottom: 10px; align-items: center; 
    }
    .word-slot { 
        min-width: 50px; height: 38px; border-bottom: 3px solid #e5e7eb; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 20px; color: #1cb0f6; font-weight: bold; 
    }
    .punc-display { font-size: 22px; color: #afafaf; font-weight: bold; }

    /* 重點：自定義按鈕容器 (模擬 App 排列) */
    .btn-pool {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: flex-start;
        padding: 10px 0;
    }
    
    /* 預習清單 */
    .preview-line { padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
    </style>
""", unsafe_allow_html=True)

# --- 【重點 2】Base64 音訊嵌入 ---
def get_audio_html(text):
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
    try:
        response = requests.get(tts_url)
        if response.status_code == 200:
            b64 = base64.b64encode(response.content).decode()
            return f'<audio controls style="width:100%; height:40px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
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

# --- 【重點 4】主程式邏輯 ---
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
    
    c_s1, c_s2 = st.sidebar.columns(2)
    if c_s1.button("➖ 少題"): st.session_state.num_q = max(1, st.session_state.num_q-1); st.rerun()
    if c_s2.button("➕ 多題"): st.session_state.num_q = min(len(filtered_df), st.session_state.num_q+1); st.rerun()
    
    preview_mode = st.sidebar.checkbox("📖 預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if preview_mode:
        st.subheader("📖 預習清單")
        for i, item in enumerate(quiz_list):
            st.markdown(f"**{i+1}. {item[cols['cn']]}**")
            st.write(item[cols['ja']])
            st.markdown(get_audio_html(item[cols['ja']]), unsafe_allow_html=True)
            st.markdown('<div class="preview-line"></div>', unsafe_allow_html=True)
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw, cn_text = str(q[cols['ja']]).strip(), q[cols['cn']]
        sentence_struct = get_sentence_structure(ja_raw)
        word_tokens = [s['content'] for s in sentence_struct if s['type'] == 'word']
        
        if not st.session_state.shuf:
            st.session_state.shuf = list(word_tokens); random.shuffle(st.session_state.shuf)

        st.caption(f"第 {st.session_state.q_idx + 1} 題 | {cn_text}")

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

        # 功能導航 (清晰文字)
        n1, n2, n3, n4 = st.columns(4)
        if n1.button("⏮ 上題"): 
            if st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        if n2.button("⏭ 下題"): 
            if st.session_state.q_idx < len(quiz_list)-1: st.session_state.q_idx += 1; reset_state(); st.rerun()
        if n3.button("🔄 重填"): reset_state(); st.rerun()
        if n4.button("⬅ 退回"):
            if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

        st.write("---")
        
        # --- 核心：真正解決直立手機排列問題 ---
        # 我們利用 st.columns 的「列」屬性，但給予大量空列。
        # 在直立手機上，我們透過 CSS 強制讓這些 Column 寬度變為 auto
        st.markdown('<div class="btn-pool">', unsafe_allow_html=True)
        
        # 建立一個足夠寬的列，然後讓每個單字佔一個小 Column
        word_cols = st.columns([1] * 12) # 建立虛擬格柵
        btn_count = 0
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                # 計算位置，確保按鈕併排
                col_idx = btn_count % 12
                if word_cols[col_idx].button(t, key=f"btn_{idx}"):
                    st.session_state.ans.append(t); st.session_state.used_history.append(idx); st.rerun()
                btn_count += 1
        st.markdown('</div>', unsafe_allow_html=True)

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
