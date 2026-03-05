"""
================================================================
【日文結構練習器 - v4.5 核心結構解法】
----------------------------------------------------------------
技術演進邏輯：
- 棄用 CSS 鎖定：因為框架 JS 會在手機端強行重寫。
- 棄用 query_params：因為會重整網頁導致側邊欄消失。
- 採用：【JavaScript 橋接技術】
  1. 在網頁底部放一個隱藏的 st.selectbox 作為資料通道。
  2. 使用 HTML 渲染按鈕，點擊時透過 JS 修改 selectbox 的值。
  3. 這能保證：手機直立 100% 併排、點擊 100% 有反應、側邊欄 100% 存在。
----------------------------------------------------------------
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

st.set_page_config(page_title="🇯🇵 日文重組 v4.5", layout="wide")

# 基礎 UI 壓縮
st.markdown("""
    <style>
    .block-container { padding: 1rem 0.5rem !important; }
    [data-testid="stHeader"] { display: none; }
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 4px; background-color: #f9fafb; 
        padding: 10px; border-radius: 10px; border: 1.5px solid #e5e7eb; 
        min-height: 50px; align-items: center; 
    }
    .word-slot { 
        min-width: 32px; height: 26px; border-bottom: 2px solid #1cb0f6; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 16px; color: #1cb0f6; font-weight: bold; margin: 0 2px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 資料處理與函數 ---
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

def reset_state():
    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct = [], [], [], False

# --- 初始化 ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 10
    reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄控制
    st.sidebar.header("⚙️ 練習設定")
    unit_list = sorted(df[cols['unit']].astype(str).unique())
    sel_unit = st.sidebar.selectbox("單元選擇", unit_list)
    unit_df = df[df[cols['unit']].astype(str) == sel_unit]
    sel_start_ch = st.sidebar.selectbox("起始章節", sorted(unit_df[cols['ch']].astype(str).unique()))
    filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
    preview_mode = st.sidebar.checkbox("📖 開啟預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if not preview_mode and st.session_state.q_idx < len(quiz_list):
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

        # --- B. 核心：自定義 HTML 按鈕併排池 (杜林格式) ---
        # 建立按鈕 HTML
        btn_html = ""
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                # 這裡的 onclick 透過 JS 模擬點擊下方隱藏的 Streamlit Selectbox
                btn_html += f'''
                <button onclick="handleBtnClick({idx})" style="
                    background: white; border: 1px solid #e5e7eb; border-bottom: 3.5px solid #e5e7eb;
                    border-radius: 10px; padding: 6px 14px; margin: 3px; font-size: 16px; font-weight: bold;
                    color: #4b4b4b; cursor: pointer;">{t}</button>
                '''

        # JS 橋接腳本：讓 HTML 按鈕可以跟 Python 通訊
        # 利用 Streamlit 的元件選擇器找到 selectbox
        st.components.v1.html(f"""
            <div id="pool" style="display:flex; flex-wrap:wrap;">{btn_html}</div>
            <script>
                function handleBtnClick(idx) {{
                    const selector = window.parent.document.querySelector('input[aria-label="hidden_trigger"]');
                    if (selector) {{
                        selector.value = idx;
                        selector.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        selector.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }}
            </script>
        """, height=130)

        # 這裡是一個「看不見」的輸入框，接收 JS 傳來的索引
        trigger = st.text_input("hidden_trigger", label_visibility="collapsed", key="hidden_trigger")
        if trigger:
            idx = int(trigger)
            if idx not in st.session_state.used_history:
                st.session_state.ans.append(st.session_state.shuf[idx])
                st.session_state.used_history.append(idx)
                st.rerun()

        # --- C. 功能鍵 (併排確保) ---
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
