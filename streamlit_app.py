"""
================================================================
【技術演進與邏輯追蹤表 - v6.7 標示強化版】
----------------------------------------------------------------
1. 標示優化：
   - 功能鍵改為全文字標註，解決「縮寫看不懂」的問題。
   - 順序維持：退回 -> 重填 -> 上題 -> 下題。
2. 佈局安全：
   - 功能鍵置於單字池上方，確保檢查結果在螢幕底部不被遮擋。
3. 側邊欄替代：
   - 持續使用頂部 st.expander 作為設定區，保證手機 100% 可見。
----------------------------------------------------------------
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 1. 頁面配置與極致壓縮 CSS ---
st.set_page_config(page_title="🇯🇵 日文重組 v6.7", layout="wide")

st.markdown("""
    <style>
    /* 1. 答案格位：縮小高度以騰出空間 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 4px; 
        background-color: #ffffff; padding: 8px; 
        border-radius: 10px; border: 1.5px solid #e2e8f0; 
        min-height: 42px; align-items: center; margin-bottom: 5px;
    }
    .word-slot { 
        min-width: 25px; height: 24px; border-bottom: 2px solid #3b82f6; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 15px; color: #2563eb; font-weight: bold; margin: 0 1px;
    }

    /* 2. 強制按鈕池與功能鍵併排 */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
        display: flex !important; flex-wrap: wrap !important;
        flex-direction: row !important; gap: 3px !important;
    }

    /* 3. 按鈕細節：扁平化以節省垂直像素 */
    div.stButton > button {
        width: auto !important; min-width: 30px !important;
        padding: 3px 8px !important; border-radius: 6px !important;
        font-size: 13px !important; font-weight: bold !important;
        border-bottom: 2px solid #e5e7eb !important;
    }
    
    /* 4. 強調功能鍵區塊 */
    .nav-label { font-size: 12px; color: #64748b; margin-bottom: 2px; }
    
    /* 隱藏原生 Header 並壓縮邊距 */
    .block-container { padding: 0.4rem 0.3rem !important; }
    [data-testid="stHeader"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 功能函數 ---
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
            return f'<audio controls style="width:100%; height:30px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except: pass
    return ""

def reset_state():
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

# --- 3. 初始化 ---
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0
if 'num_q' not in st.session_state: st.session_state.num_q = 10
if 'ans' not in st.session_state: reset_state()

df, cols = load_data()

if df is not None:
    # --- 頂部設定區 ---
    with st.expander("⚙️ 練習設定 (單元與預習)", expanded=False):
        unit_list = sorted(df[cols['unit']].astype(str).unique())
        sel_unit = st.selectbox("單元選擇", unit_list)
        unit_df = df[df[cols['unit']].astype(str) == sel_unit]
        sel_start_ch = st.selectbox("起始章節", sorted(unit_df[cols['ch']].astype(str).unique()))
        filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
        preview_mode = st.checkbox("📖 開啟預習模式")

    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if preview_mode:
        for i, item in enumerate(quiz_list):
            st.write(f"**{i+1}. {item[cols['cn']]}**\n{item[cols['ja']]}")
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

        # A. 答案區
        st.markdown(f"**💡 {cn_text}**")
        curr_ans_copy = list(st.session_state.ans)
        ans_html = '<div class="res-box">'
        for s in sentence_struct:
            if s['type'] == 'punc': ans_html += f'<span style="color:#94a3b8; font-weight:bold;">{s["content"]}</span>'
            else:
                val = curr_ans_copy.pop(0) if curr_ans_copy else ""
                ans_html += f'<div class="word-slot">{val}</div>'
        ans_html += '</div>'
        st.markdown(ans_html, unsafe_allow_html=True)

        # B. 功能控制鍵 (標示清楚化)
        st.markdown('<p class="nav-label">系統操作：</p>', unsafe_allow_html=True)
        nav_cols = st.columns(4)
        if nav_cols[0].button("⬅退回"):
            if st.session_state.used_history:
                st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        if nav_cols[1].button("🔄重填"): reset_state(); st.rerun()
        if nav_cols[2].button("⏮上題"): 
            st.session_state.q_idx = max(0, st.session_state.q_idx-1); reset_state(); st.rerun()
        if nav_cols[3].button("⏭下題"): 
            st.session_state.q_idx = min(len(quiz_list)-1, st.session_state.q_idx+1); reset_state(); st.rerun()

        # C. 單字池
        st.markdown('<p class="nav-label">選擇單字：</p>', unsafe_allow_html=True)
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                if st.button(t, key=f"p_{st.session_state.q_idx}_{idx}"):
                    st.session_state.ans.append(t)
                    st.session_state.used_history.append(idx)
                    st.rerun()

        # D. 檢查與結果 (置底)
        st.write(" ")
        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            if st.button("🔍 點擊檢查結果", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(word_tokens):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔！")

        if st.session_state.is_correct:
            st.success("正解！")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("繼續下一題 ➡️", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
