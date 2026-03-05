"""
================================================================
【技術演進與邏輯追蹤表 - v4.2 最終穩定版】
----------------------------------------------------------------
- v4.1 (舊方法回顧)：使用 HTML Component。
  失敗原因：手機瀏覽器的沙盒機制導致點擊通訊中斷（無反應），且 iframe 載入會干擾側邊欄顯示。

- v4.2 (本次解法 - 強制 Flex 佈局)：
  邏輯：回歸原生 st.button，但透過 CSS 強行修改其渲染行為。
  1. 容器解鎖：針對 data-testid="stHorizontalBlock" 強制注入 flex-flow: row wrap。
  2. 按鈕縮減：強迫 st.button 拋棄 100% 寬度，改為內容寬度 (width: auto)。
  3. 側邊欄保全：不使用任何 iframe 或 URL 參數，保證側邊欄與頁面狀態 100% 同步。
----------------------------------------------------------------
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 【核心】手機併排絕對解決 CSS ---
st.set_page_config(page_title="🇯🇵 日文重組 v4.2", layout="wide")

st.markdown("""
    <style>
    /* 1. 強制讓手機版的欄位「併排」而非「堆疊」 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important; 
        flex-wrap: wrap !important;
        align-items: flex-start !important;
        gap: 4px !important;
    }

    /* 2. 讓每個按鈕欄位不要佔據整行 */
    [data-testid="column"] {
        width: auto !important;
        flex: 0 1 auto !important;
        min-width: 0px !important;
    }

    /* 3. 強制按鈕寬度縮小，不要撐滿欄位 */
    div.stButton > button {
        width: auto !important;
        min-width: 40px !important;
        padding: 4px 12px !important;
        border-radius: 8px !important;
        border-bottom: 3px solid #e5e7eb !important;
        font-weight: bold !important;
    }

    /* 4. 答案格位縮小 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 4px; 
        background-color: #f8fafc; padding: 10px; 
        border-radius: 8px; border: 1.5px solid #e2e8f0; 
        min-height: 55px; align-items: center; 
    }
    .word-slot { 
        min-width: 30px; height: 26px; border-bottom: 2px solid #3b82f6; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 16px; color: #2563eb; font-weight: bold; margin: 0 2px;
    }

    /* 介面壓縮 */
    .block-container { padding: 1rem 0.5rem !important; }
    [data-testid="stHeader"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- 功能函數 ---
def get_audio_html(text):
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
    try:
        res = requests.get(tts_url)
        if res.status_code == 200:
            b64 = base64.b64encode(res.content).decode()
            return f'<audio controls style="width:100%; height:35px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
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

# --- 邏輯開始 ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 10
    reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄 (這版絕對正常)
    st.sidebar.header("⚙️ 練習設定")
    unit_list = sorted(df[cols['unit']].astype(str).unique())
    sel_unit = st.sidebar.selectbox("單元選擇", unit_list)
    unit_df = df[df[cols['unit']].astype(str) == sel_unit]
    sel_start_ch = st.sidebar.selectbox("起始章節", sorted(unit_df[cols['ch']].astype(str).unique()))
    filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
    
    preview_mode = st.sidebar.checkbox("📖 預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if preview_mode:
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

        # --- A. 答案區 ---
        curr_ans = list(st.session_state.ans)
        ans_html = '<div class="res-box">'
        for s in sentence_struct:
            if s['type'] == 'word':
                val = curr_ans.pop(0) if curr_ans else ""
                ans_html += f'<div class="word-slot">{val}</div>'
            else:
                ans_html += f'<span style="font-size:18px; color:#94a3b8; font-weight:bold;">{s["content"]}</span>'
        ans_html += '</div>'
        st.markdown(ans_html, unsafe_allow_html=True)

        st.write("---")

        # --- B. 單字按鈕池 (核心修復) ---
        num_shuf = len(st.session_state.shuf)
        word_cols = st.columns(num_shuf if num_shuf > 0 else 1)
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                if word_cols[idx].button(t, key=f"btn_{idx}"):
                    st.session_state.ans.append(t)
                    st.session_state.used_history.append(idx)
                    st.rerun()

        # --- C. 功能鍵 (置底) ---
        st.write(" ")
        n1, n2, n3, n4 = st.columns(4)
        n1.button("⏮上", on_click=lambda: (st.session_state.update({"q_idx": max(0, st.session_state.q_idx-1)}), reset_state()))
        n2.button("⏭下", on_click=lambda: (st.session_state.update({"q_idx": min(len(quiz_list)-1, st.session_state.q_idx+1)}), reset_state()))
        n3.button("🔄重", on_click=reset_state)
        if n4.button("⬅退"):
            if st.session_state.used_history:
                st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

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
