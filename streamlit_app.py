"""
================================================================
【技術演進與邏輯追蹤表 - v4.3 物理極限版】
----------------------------------------------------------------
- v3.8~v4.1 (黑科技失敗回顧)：
  使用 HTML/JS/Iframe。
  失敗原因：手機瀏覽器對 iframe 點擊傳輸極不穩定（沒反應），且會導致側邊欄重置。

- v4.2~v4.3 (最終解法：容器解構法)：
  邏輯：回歸 st.button 是為了保證「點擊反應」與「側邊欄穩定」。
  核心突破：
  1. 針對 data-testid="stHorizontalBlock" (Streamlit 的列容器) 強制注入 
     display: flex !important 與 flex-direction: row !important。
  2. 這是從「外層容器」鎖死排版，不管 Streamlit JS 怎麼偵測手機寬度，
     都無法將這區塊轉為垂直排列。
  3. 這是目前在維持 App 功能完整下，唯一能實現手機直立併排的手段。
----------------------------------------------------------------
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 【核心】強制容器橫向 CSS ---
st.set_page_config(page_title="🇯🇵 日文重組 v4.3", layout="wide")

st.markdown("""
    <style>
    /* 強制打破 Streamlit 的手機堆疊規則：鎖定主畫面測驗區 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important; /* 禁止垂直堆疊 */
        flex-wrap: wrap !important;     /* 允許自動換行 */
        align-items: center !important;
        gap: 3px !important;            /* 極致緊湊 */
    }

    /* 讓 Column 容器寬度隨內容變化，不要佔滿一整列 */
    [data-testid="column"] {
        width: auto !important;
        flex: 0 1 auto !important;
        min-width: 0px !important;
        padding: 0px !important;
    }

    /* 仿 Duolingo 緊實按鈕樣式 */
    div.stButton > button {
        width: auto !important;
        padding: 4px 10px !important;
        border-radius: 10px !important;
        border: 1.5px solid #e5e7eb !important;
        border-bottom: 3.5px solid #e5e7eb !important;
        font-size: 16px !important;
        background-color: white !important;
        color: #4b4b4b !important;
    }

    /* 答案格位微縮化 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 4px; 
        background-color: #f9fafb; padding: 10px; 
        border-radius: 10px; border: 1.5px solid #e5e7eb; 
        min-height: 55px; align-items: center; margin-bottom: 5px;
    }
    .word-slot { 
        min-width: 35px; height: 28px; border-bottom: 2px solid #1cb0f6; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 18px; color: #1cb0f6; font-weight: bold; margin: 0 2px;
    }

    /* 移除頂部間距 */
    .block-container { padding: 0.5rem 0.3rem !important; }
    [data-testid="stHeader"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- 功能函數 (音訊 Base64) ---
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
            if " " in part or "　" in part:
                tokens = [t for t in re.split(r'[ 　]+', part) if t]
            else:
                tokens = [t for t in re.split(f"({'|'.join(['は','が','を','に','へ','と','も','で','の','から','まで'])})", part) if t]
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

# --- 核心執行區 ---
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

        # --- A. 答案格位 ---
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

        # --- B. 單字按鈕池 (強制併排核心) ---
        num_shuf = len(st.session_state.shuf)
        # 建立動態列，CSS 會保證它們在手機上橫向排列
        word_cols = st.columns(num_shuf if num_shuf > 0 else 1)
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                if word_cols[idx].button(t, key=f"btn_{idx}"):
                    st.session_state.ans.append(t); st.session_state.used_history.append(idx); st.rerun()

        # --- C. 功能鍵 (底部併排) ---
        st.write(" ")
        n1, n2, n3, n4 = st.columns(4)
        if n1.button("⏮上"): 
            st.session_state.q_idx = max(0, st.session_state.q_idx-1)
            reset_state(); st.rerun()
        if n2.button("⏭下"): 
            st.session_state.q_idx = min(len(quiz_list)-1, st.session_state.q_idx+1)
            reset_state(); st.rerun()
        if n3.button("🔄重"): reset_state(); st.rerun()
        if n4.button("⬅退"):
            if st.session_state.used_history:
                st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            if st.button("🔍 CHECK ANSWER", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(word_tokens):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔！")

        if st.session_state.is_correct:
            st.success("正解！")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("CONTINUE ➡️", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
