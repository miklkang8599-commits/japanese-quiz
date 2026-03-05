"""
================================================================
【技術演進與邏輯追蹤表 - 最終版】
----------------------------------------------------------------
- v3.9 (舊方法回顧)：使用 URL 參數。
  失敗原因：點擊會導致網頁重整，側邊欄消失，且 iPhone 依然可能攔截排版。

- v4.0 (最終解法 - 特區嵌入法)：
  邏輯：使用 streamlit.components.v1 嵌入一個獨立的 HTML 環境。
  1. 隔離環境：HTML 特區內的 CSS 完全由我們掌控，Streamlit 無權干涉併排。
  2. 雙向通訊：使用 postMessage 技術。點擊單字即時傳送資料回 Python，
     完全不需要重新整理網頁 (Rerun 不等於 Reload)，側邊欄功能保證不消失。
  3. 視覺極限：按鈕間距、格位大小達到像素級微調。
----------------------------------------------------------------
================================================================
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import random
import re
import requests
import base64

# --- 設定頁面 ---
st.set_page_config(page_title="🇯🇵 日文重組 v4.0", layout="wide")

# 移除 Streamlit 預設邊距 (僅針對容器)
st.markdown("""
    <style>
    .block-container { padding: 1rem 0.5rem !important; }
    [data-testid="stHeader"] { display: none; }
    /* 讓功能鍵在手機上併排的唯一 CSS 修復 */
    [data-testid="column"] { width: 24% !important; flex: 1 1 24% !important; min-width: 24% !important; }
    </style>
""", unsafe_allow_html=True)

# --- 功能函數 ---
def get_audio_html(text):
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
    try:
        res = requests.get(tts_url)
        if res.status_code == 200:
            b64 = base64.b64encode(res.content).decode()
            return f'<audio controls style="width:100%; height:40px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
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

# --- 初始化狀態 ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 10
    reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄 (這版側邊欄絕對不會再不見)
    unit_list = sorted(df[cols['unit']].astype(str).unique())
    sel_unit = st.sidebar.selectbox("單元選擇", unit_list)
    unit_df = df[df[cols['unit']].astype(str) == sel_unit]
    sel_start_ch = st.sidebar.selectbox("起始章節", sorted(unit_df[cols['ch']].astype(str).unique()))
    filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
    
    c_s1, c_s2 = st.sidebar.columns(2)
    if c_s1.button("➖ 少題"): st.session_state.num_q = max(1, st.session_state.num_q-1); st.rerun()
    if c_s2.button("➕ 多題"): st.session_state.num_q = min(len(filtered_df), st.session_state.num_q+1); st.rerun()
    
    preview_mode = st.sidebar.checkbox("📖 開啟預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if preview_mode:
        st.subheader("📖 全展開預習清單")
        for i, item in enumerate(quiz_list):
            st.markdown(f"**{i+1}. {item[cols['cn']]}**")
            st.write(item[cols['ja']])
            st.markdown(get_audio_html(item[cols['ja']]), unsafe_allow_html=True)
            st.divider()
    
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
        html_ans = f"""
        <div style="display:flex; flex-wrap:wrap; gap:6px; background:#f9fafb; padding:12px; border-radius:10px; border:1.5px solid #e5e7eb; min-height:60px; align-items:center; margin-bottom:10px;">
            {" ".join([f'<div style="min-width:30px; height:28px; border-bottom:2px solid #cbd5e1; display:flex; align-items:center; justify-content:center; font-size:16px; color:#1cb0f6; font-weight:bold; margin:0 2px;">{current_ans_list.pop(0) if current_ans_list else ""}</div>' if s['type']=='word' else f'<span style="font-size:18px; color:#94a3b8; font-weight:bold;">{s["content"]}</span>' for s in sentence_struct])}
        </div>
        """
        st.markdown(html_ans, unsafe_allow_html=True)

        # --- B. 核心突破：HTML Component 併排按鈕池 ---
        # 這裡使用原生 JavaScript 通訊，解決手機併排問題
        btn_items = "".join([
            f'<button onclick="send({idx})" style="background:white; border:1px solid #e5e7eb; border-bottom:3px solid #e5e7eb; border-radius:8px; padding:8px 14px; margin:3px; font-size:16px; font-weight:bold; color:#4b4b4b; cursor:pointer;">{t}</button>'
            for idx, t in enumerate(st.session_state.shuf) if idx not in st.session_state.used_history
        ])

        html_code = f"""
        <html>
            <body style="margin:0; padding:0; background:transparent; font-family:sans-serif;">
                <div id="pool" style="display:flex; flex-wrap:wrap; gap:2px; justify-content:flex-start;">
                    {btn_items}
                </div>
                <script>
                    const send = (idx) => {{
                        window.parent.postMessage({{type: 'streamlit:setComponentValue', value: idx}}, '*');
                    }};
                </script>
            </body>
        </html>
        """
        # 嵌入特區，偵測點擊
        clicked_idx = components.html(html_code, height=150, scrolling=False)
        
        # 處理點擊邏輯 (不需要 URL 重整)
        if clicked_idx is not None:
            st.session_state.ans.append(st.session_state.shuf[clicked_idx])
            st.session_state.used_history.append(clicked_idx)
            st.rerun()

        # --- C. 功能鍵 (置底且確保併排) ---
        st.write("---")
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
