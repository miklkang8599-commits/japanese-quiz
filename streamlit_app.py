"""
================================================================
【技術演進與解決邏輯追蹤表】
----------------------------------------------------------------
版本歷史與邏輯變更：
- v1.0~v3.7 (舊方法)：
  邏輯：使用 st.columns()。手機直立時會因框架限制強制「一列一個」。
- v3.8~v3.9.1 (最終獨立解法 - 目前版本)：
  邏輯：完全捨棄 st.columns 排列單字池。
  1. 渲染：使用純 HTML <a> 標籤。
  2. 排版：利用瀏覽器對標準 HTML <flex-wrap> 的原生支援實現併排。
  3. 通訊：點擊 HTML 連結觸發 URL query_params。
  4. 修復(v3.9.1)：調整執行順序，確保 SessionState 初始化後才讀取參數。
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

# --- 【重點 1】手機環境極致 CSS ---
st.set_page_config(page_title="🇯🇵 日文重組 v3.9.1", layout="wide")

st.markdown("""
    <style>
    .block-container { padding: 1rem 0.5rem !important; }
    [data-testid="stHeader"] { display: none; }
    
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 6px; 
        background-color: #f9fafb; padding: 12px; 
        border-radius: 10px; border: 1.5px solid #e5e7eb; 
        min-height: 65px; margin-bottom: 8px; align-items: center; 
    }
    .word-slot { 
        min-width: 32px; height: 30px; border-bottom: 2px solid #cbd5e1; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 17px; color: #1cb0f6; font-weight: bold; margin: 0 2px;
    }
    .punc-display { font-size: 20px; color: #94a3b8; font-weight: bold; }

    .btn-pool {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        justify-content: flex-start;
        padding: 10px 0;
    }
    .custom-btn {
        display: inline-block;
        background-color: white;
        border: 1px solid #e5e7eb;
        border-bottom: 3px solid #e5e7eb;
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 16px;
        font-weight: bold;
        color: #4b4b4b;
        cursor: pointer;
        text-decoration: none;
        transition: transform 0.1s;
    }
    .custom-btn:active {
        transform: translateY(2px);
        border-bottom-width: 1px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 【重點 2】功能函數定義 ---

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

# --- 【重點 3】執行邏輯順序修正 ---

# 1. 優先初始化 Session State (修復 AttributeError)
if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 10
    reset_state()

# 2. 接著處理來自 HTML 的 URL 點擊事件
params = st.query_params
if "q_click" in params:
    idx_str = params["q_click"]
    if idx_str.isdigit():
        idx = int(idx_str)
        # 確保 shuf 已經存在且索引有效
        if 'shuf' in st.session_state and st.session_state.shuf:
            if idx not in st.session_state.used_history:
                st.session_state.ans.append(st.session_state.shuf[idx])
                st.session_state.used_history.append(idx)
                st.query_params.clear()
                st.rerun()

# 3. 讀取資料
df, cols = load_data()

# --- 【重點 4】主程式介面 ---

if df is not None:
    # 側邊欄設定
    unit_list = sorted(df[cols['unit']].astype(str).unique())
    sel_unit = st.sidebar.selectbox("單元", unit_list)
    unit_df = df[df[cols['unit']].astype(str) == sel_unit]
    sel_start_ch = st.sidebar.selectbox("章節", sorted(unit_df[cols['ch']].astype(str).unique()))
    filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
    
    cs1, cs2 = st.sidebar.columns(2)
    if cs1.button("➖ 少題"): st.session_state.num_q = max(1, st.session_state.num_q-1); st.rerun()
    if cs2.button("➕ 多題"): st.session_state.num_q = min(len(filtered_df), st.session_state.num_q+1); st.rerun()
    
    preview_mode = st.sidebar.checkbox("📖 預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    # 狀態守衛：條件變動即重置
    cur_key = f"{sel_unit}-{sel_start_ch}-{st.session_state.num_q}"
    if 'last_key' not in st.session_state or st.session_state.last_key != cur_key:
        st.session_state.last_key, st.session_state.q_idx = cur_key, 0
        reset_state(); st.rerun()

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
        
        # 確保 shuf 在渲染按鈕前已經生成
        if not st.session_state.shuf:
            st.session_state.shuf = list(word_tokens); random.shuffle(st.session_state.shuf)

        st.caption(f"Q{st.session_state.q_idx + 1} | {cn_text}")

        # 答案展示區
        current_ans_list = list(st.session_state.ans)
        html_ans = '<div class="res-box">'
        for item in sentence_struct:
            if item['type'] == 'punc': html_ans += f'<span class="punc-display">{item["content"]}</span>'
            else:
                val = current_ans_list.pop(0) if current_ans_list else ""
                html_ans += f'<div class="word-slot">{val}</div>'
        html_ans += '</div>'
        st.markdown(html_ans, unsafe_allow_html=True)

        st.write("---")

        # --- HTML 併排按鈕池 ---
        btn_html = '<div class="btn-pool">'
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                btn_html += f'<a href="?q_click={idx}" target="_self" class="custom-btn">{t}</a>'
        btn_html += '</div>'
        st.markdown(btn_html, unsafe_allow_html=True)

        st.write(" ")

        # --- 功能導航鍵 (置底) ---
        n1, n2, n3, n4 = st.columns(4)
        if n1.button("⏮上"): 
            if st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        if n2.button("⏭下"): 
            if st.session_state.q_idx < len(quiz_list)-1: st.session_state.q_idx += 1; reset_state(); st.rerun()
        if n3.button("🔄重"): reset_state(); st.rerun()
        if n4.button("⬅退"):
            if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

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
