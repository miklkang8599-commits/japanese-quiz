"""
================================================================
【技術演進與邏輯追蹤表 - v4.8 最終通訊方案】
----------------------------------------------------------------
- v4.7 (失敗原因)：
  JS 無法穿透 iframe 觸發 Streamlit 組件。導致按鈕排版美但點了沒反應。

- v4.8 (本次解法 - URL 錨點通訊)：
  1. 渲染：HTML <a> 標籤偽裝成按鈕 (確保手機直立併排)。
  2. 通訊：點擊後網址會帶上 ?pick=idx，Python 攔截參數後立即執行邏輯。
  3. 穩定：執行完後立即 clear 參數，確保側邊欄不跳動，功能不失效。
----------------------------------------------------------------
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 【重點 1】手機極限排版 CSS ---
st.set_page_config(page_title="🇯🇵 日文重組 v4.8", layout="wide")

st.markdown("""
    <style>
    .block-container { padding: 1rem 0.5rem !important; }
    [data-testid="stHeader"] { display: none; }
    
    /* 答案區：格位小一點 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 4px; 
        background-color: #ffffff; padding: 12px; 
        border-radius: 12px; border: 1.5px solid #e5e7eb; 
        min-height: 55px; margin-bottom: 5px; align-items: center; 
    }
    .word-slot { 
        min-width: 32px; height: 26px; border-bottom: 2px solid #3b82f6; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 16px; color: #2563eb; font-weight: bold; margin: 0 2px;
    }
    
    /* HTML 按鈕池排版 (杜林風格) */
    .btn-pool {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        justify-content: flex-start;
        padding: 10px 0;
    }
    .custom-btn {
        display: inline-block;
        background-color: white;
        border: 1px solid #e5e7eb;
        border-bottom: 3.5px solid #e5e7eb;
        border-radius: 10px;
        padding: 8px 15px;
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

# --- 【重點 2】資料與音訊函數 ---
@st.cache_data(ttl=60)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA/export?format=csv&gid=1337973082"
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(subset=["日文原文", "中文意譯"]), {"ja": "日文原文", "cn": "中文意譯", "unit": "單元", "ch": "章節"}
    except: return None, None

def get_sentence_structure(text):
    particles = ['は','が','を','に','へ','と','も','で','の','から','まで']
    raw_parts = re.split(r'([、。！？])', text.strip())
    structure = []
    for part in raw_parts:
        if not part: continue
        if part in ['、', '。', '！', '？']:
            structure.append({"type": "punc", "content": part})
        else:
            tokens = [t for t in re.split(r'[ 　]+', part) if t] if " " in part or "　" in part else [t for t in re.split(f"({'|'.join(particles)})", part) if t]
            for token in tokens: structure.append({"type": "word", "content": token})
    return structure

def get_audio_html(text):
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
    try:
        res = requests.get(tts_url)
        if res.status_code == 200:
            b64 = base64.b64encode(res.content).decode()
            return f'<audio controls style="width:100%; height:38px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except: pass
    return ""

def reset_state():
    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct = [], [], [], False

# --- 【重點 3】處理 URL 點擊通訊 (獨立解法的核心) ---
params = st.query_params
if "pick" in params:
    try:
        idx = int(params["pick"])
        if idx not in st.session_state.get('used_history', []):
            st.session_state.ans.append(st.session_state.shuf[idx])
            st.session_state.used_history.append(idx)
        # 關鍵：清除參數防止循環觸發，並確保 UI 更新
        st.query_params.clear()
        st.rerun()
    except:
        st.query_params.clear()

# --- 【重點 4】主程式邏輯 ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 10
    reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄
    st.sidebar.header("⚙️ 練習設定")
    unit_list = sorted(df[cols['unit']].astype(str).unique())
    sel_unit = st.sidebar.selectbox("單元選擇", unit_list)
    unit_df = df[df[cols['unit']].astype(str) == sel_unit]
    sel_start_ch = st.sidebar.selectbox("起始章節", sorted(unit_df[cols['ch']].astype(str).unique()))
    filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
    preview_mode = st.sidebar.checkbox("📖 開啟預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if preview_mode:
        st.subheader("📖 預習清單")
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

        # A. 答案展示區
        curr_ans = list(st.session_state.ans)
        ans_html = '<div class="res-box">'
        for s in sentence_struct:
            if s['type'] == 'punc': ans_html += f'<span style="font-size:18px; color:#94a3b8; font-weight:bold;">{s["content"]}</span>'
            else:
                val = curr_ans.pop(0) if curr_ans else ""
                ans_html += f'<div class="word-slot">{val}</div>'
        ans_html += '</div>'
        st.markdown(ans_html, unsafe_allow_html=True)

        st.write("---")

        # B. 單字併排按鈕池 (HTML 連結通訊法)
        # 不使用 iframe，直接在 Markdown 中渲染，保證 100% 併排且點擊有效
        btn_pool_html = '<div class="btn-pool">'
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                # 透過 URL 參數傳遞點擊資料，避開 JavaScript 通訊問題
                btn_pool_html += f'<a href="?pick={idx}" target="_self" class="custom-btn">{t}</a>'
        btn_pool_html += '</div>'
        st.markdown(btn_pool_html, unsafe_allow_html=True)

        # C. 功能導航 (底部)
        st.write(" ")
        n1, n2, n3, n4 = st.columns(4)
        if n1.button("⏮上"): 
            st.session_state.q_idx = max(0, st.session_state.q_idx-1); reset_state(); st.rerun()
        if n2.button("⏭下"): 
            st.session_state.q_idx = min(len(quiz_list)-1, st.session_state.q_idx+1); reset_state(); st.rerun()
        if n3.button("🔄重"): reset_state(); st.rerun()
        if n4.button("⬅退"):
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
