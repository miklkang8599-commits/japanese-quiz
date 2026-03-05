"""
================================================================
【技術演進與邏輯追蹤表 - v6.6 內嵌設定版】
----------------------------------------------------------------
1. 側邊欄失效解決：
   - 徹底放棄 Sidebar 導航，改將設定選單「內嵌」在主畫面前端。
   - 使用 st.expander (預設收合)，解決手機看不到側邊欄的問題。
2. 功能鍵順序鎖定：
   - 退回 -> 重填 -> 上一題 -> 下一題。
3. 併排穩定性：
   - 移除所有導致側邊欄消失的全局 CSS，確保 UI 100% 穩定。
----------------------------------------------------------------
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 1. 頁面配置 ---
st.set_page_config(page_title="🇯🇵 日文重組 v6.6", layout="wide")

st.markdown("""
    <style>
    /* 答案區展示：扁平簡潔 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 4px; 
        background-color: #f9fafb; padding: 10px; 
        border-radius: 12px; border: 1.5px solid #e5e7eb; 
        min-height: 45px; align-items: center; margin-bottom: 8px;
    }
    .word-slot { 
        min-width: 28px; height: 24px; border-bottom: 2px solid #1cb0f6; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 15px; color: #1cb0f6; font-weight: bold; margin: 0 2px;
    }

    /* 單字按鈕池：手機併排核心 (不使用 columns) */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-wrap: wrap !important;
        flex-direction: row !important;
        gap: 5px !important;
    }

    /* 原生按鈕視覺優化 */
    div.stButton > button {
        width: auto !important;
        min-width: 45px !important;
        padding: 5px 12px !important;
        border-radius: 8px !important;
        border-bottom: 3.5px solid #e5e7eb !important;
        font-weight: bold !important;
    }
    
    /* 底部功能控制列 */
    .control-row [data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0px !important;
    }
    
    .block-container { padding: 0.5rem 0.5rem !important; }
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
            return f'<audio controls style="width:100%; height:35px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except: pass
    return ""

def reset_state():
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

# --- 3. 初始化 ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx = 0
if 'num_q' not in st.session_state:
    st.session_state.num_q = 10
if 'ans' not in st.session_state:
    reset_state()

df, cols = load_data()

if df is not None:
    # 【重點：內嵌式設定選單】
    with st.expander("⚙️ 練習設定與單元選擇"):
        unit_list = sorted(df[cols['unit']].astype(str).unique())
        sel_unit = st.selectbox("1. 選擇單元", unit_list)
        unit_df = df[df[cols['unit']].astype(str) == sel_unit]
        sel_start_ch = st.selectbox("2. 起始章節", sorted(unit_df[cols['ch']].astype(str).unique()))
        filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
        preview_mode = st.checkbox("📖 開啟預習清單")
        
        c_set1, c_set2 = st.columns(2)
        if c_set1.button("➖ 少題"): st.session_state.num_q = max(1, st.session_state.num_q-1); st.rerun()
        if c_set2.button("➕ 多題"): st.session_state.num_q = min(len(filtered_df), st.session_state.num_q+1); st.rerun()

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

        st.caption(f"Q{st.session_state.q_idx + 1} | 共 {len(quiz_list)} 題")
        st.info(f"💡 {cn_text}")

        # A. 答案展示區
        curr_ans_copy = list(st.session_state.ans)
        ans_html = '<div class="res-box">'
        for s in sentence_struct:
            if s['type'] == 'punc': 
                ans_html += f'<span style="color:#94a3b8;">{s["content"]}</span>'
            else:
                val = curr_ans_copy.pop(0) if curr_ans_copy else ""
                ans_html += f'<div class="word-slot">{val}</div>'
        ans_html += '</div>'
        st.markdown(ans_html, unsafe_allow_html=True)

        # B. 單字選擇
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                if st.button(t, key=f"p_{st.session_state.q_idx}_{idx}"):
                    st.session_state.ans.append(t)
                    st.session_state.used_history.append(idx)
                    st.rerun()

        # C. 功能按鈕 (依照新順序：退回 -> 重填 -> 上一題 -> 下一題)
        st.write("---")
        st.markdown('<div class="control-row">', unsafe_allow_html=True)
        n1, n2, n3, n4 = st.columns(4)
        if n1.button("⬅ 退回"):
            if st.session_state.used_history:
                st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        if n2.button("🔄 重填"): 
            reset_state(); st.rerun()
        if n3.button("⏮ 上題"): 
            st.session_state.q_idx = max(0, st.session_state.q_idx-1); reset_state(); st.rerun()
        if n4.button("⏭ 下題"): 
            st.session_state.q_idx = min(len(quiz_list)-1, st.session_state.q_idx+1); reset_state(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(word_tokens):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔！")

        if st.session_state.is_correct:
            st.success("正解！")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("繼續挑戰下一題 ➡️", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
