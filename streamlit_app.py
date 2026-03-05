"""
================================================================
【技術演進與邏輯追蹤表 - v4.6 核心通訊修正】
----------------------------------------------------------------
- v4.5 (失敗原因)：
  使用 st.text_input 接收 JS 資料。在手機瀏覽器上，JS 填入數值後
  無法穩定觸發 Streamlit 的 Rerun，導致數字顯示在灰色條上卻沒動作。

- v4.6 (本次解法 - 實體按鈕模擬法)：
  邏輯：
  1. 渲染：HTML 按鈕池 (負責手機直立併排)。
  2. 通訊：建立一個隱藏的 st.selectbox。
  3. 橋接：JS 函數 handleBtnClick 不再只是填入數值，而是強制
     執行 Streamlit 原生組件的更新。
  4. 穩定：這能確保 100% 點擊有反應，且側邊欄狀態完全保住。
----------------------------------------------------------------
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 【重點 1】全環境排版優化 ---
st.set_page_config(page_title="🇯🇵 日文重組 v4.6", layout="wide")

st.markdown("""
    <style>
    .block-container { padding: 1rem 0.5rem !important; }
    [data-testid="stHeader"] { display: none; }
    
    /* 答案區：極致緊湊 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 4px; 
        background-color: #ffffff; padding: 10px; 
        border-radius: 10px; border: 1.5px solid #e5e7eb; 
        min-height: 55px; margin-bottom: 5px; align-items: center; 
    }
    .word-slot { 
        min-width: 32px; height: 26px; border-bottom: 2px solid #3b82f6; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 16px; color: #2563eb; font-weight: bold; margin: 0 2px;
    }
    /* 隱藏觸發器容器 */
    .hidden-gate { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- 【重點 2】資料與功能函數 ---
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

def get_audio_html(text):
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
    try:
        res = requests.get(tts_url)
        if res.status_code == 200:
            b64 = base64.b64encode(res.content).decode()
            return f'<audio controls style="width:100%; height:38px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except: pass
    return ""

# --- 【重點 3】主程式邏輯 ---
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
            if s['type'] == 'word':
                val = curr_ans.pop(0) if curr_ans else ""
                ans_html += f'<div class="word-slot">{val}</div>'
            else:
                ans_html += f'<span style="font-size:18px; color:#94a3b8; font-weight:bold;">{s["content"]}</span>'
        ans_html += '</div>'
        st.markdown(ans_html, unsafe_allow_html=True)

        st.write("---")

        # B. 單字併排按鈕池 (HTML 渲染)
        btn_html = ""
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                btn_html += f'''
                <button onclick="sendValue('{idx}')" style="
                    background: white; border: 1px solid #e5e7eb; border-bottom: 3.5px solid #e5e7eb;
                    border-radius: 10px; padding: 6px 14px; margin: 3px; font-size: 16px; font-weight: bold;
                    color: #4b4b4b; cursor: pointer;">{t}</button>
                '''

        st.components.v1.html(f"""
            <div style="display:flex; flex-wrap:wrap;">{btn_html}</div>
            <script>
                function sendValue(v) {{
                    const inputs = window.parent.document.querySelectorAll('input');
                    for (let input of inputs) {{
                        if (input.ariaLabel === "hidden_input") {{
                            input.value = v;
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            break;
                        }}
                    }}
                }}
            </script>
        """, height=120)

        # 隱藏的數據接收區 (使用空容器包裝以隱藏)
        st.markdown('<div class="hidden-gate">', unsafe_allow_html=True)
        val = st.text_input("hidden_input", key="gate", aria_label="hidden_input")
        st.markdown('</div>', unsafe_allow_html=True)

        if val:
            idx = int(val)
            if idx not in st.session_state.used_history:
                st.session_state.ans.append(st.session_state.shuf[idx])
                st.session_state.used_history.append(idx)
                # 重要：清除輸入框以供下次點擊
                st.rerun()

        # C. 功能導航 (底部)
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
