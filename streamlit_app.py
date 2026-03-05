"""
================================================================
【技術演進與邏輯追蹤表 - v6.1 穩定併排版】
----------------------------------------------------------------
- 為什麼回歸原生：
  實測證明 URL 參數（?pick=x）在手機瀏覽器點擊時會觸發全頁面 Reload，
  這會導致「側邊欄自動收合」且 Session 狀態不穩定（按鈕沒反應）。
  
- v6.1 解決邏輯：
  1. 穩定性：使用原生 st.button，保證側邊欄與資料狀態 100% 穩定。
  2. 併排：透過 CSS 選取器 [data-testid="column"]，強行取消手機端的 
     width: 100% 限制，實現真正的併排。
  3. 佈局：按鈕池在中，功能鍵在底。
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
st.set_page_config(page_title="🇯🇵 日文重組 v6.1", layout="wide")

# --- 2. 核心 CSS 深度覆蓋 (針對手機端 Column 併排) ---
st.markdown("""
    <style>
    /* 強制側邊欄不被重置後的空白擠壓 */
    .block-container { padding: 1rem 0.3rem !important; }
    [data-testid="stHeader"] { display: none; }

    /* 解決手機直立「一按鈕一列」的核心代碼 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important; /* 強制橫向 */
        flex-wrap: wrap !important;     /* 允許換行 */
        gap: 3px !important;
    }
    [data-testid="column"] {
        width: auto !important;         /* 關鍵：取消手機端 100% 寬度 */
        flex: 0 1 auto !important;      /* 讓寬度隨內容收縮 */
        min-width: 0px !important;
    }

    /* 按鈕樣式：緊湊且立體 */
    div.stButton > button {
        width: auto !important;
        padding: 5px 12px !important;
        border-radius: 8px !important;
        border: 1px solid #e5e7eb !important;
        border-bottom: 3px solid #e5e7eb !important;
        font-size: 16px !important;
        font-weight: bold !important;
    }

    /* 答案格位縮小 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 4px; 
        background-color: #f8fafc; padding: 8px; 
        border-radius: 10px; border: 1.5px solid #e5e7eb; 
        min-height: 50px; align-items: center; margin-bottom: 10px;
    }
    .word-slot { 
        min-width: 32px; height: 26px; border-bottom: 2px solid #1cb0f6; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 17px; color: #1cb0f6; font-weight: bold; margin: 0 2px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 功能函數 ---
@st.cache_data(ttl=60)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA/export?format=csv&gid=1337973082"
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(subset=["日文原文", "中文意譯"]), {"ja": "日文原文", "cn": "中文意譯", "unit": "單元", "ch": "章節"}
    except: return None, None

def get_sentence_structure(text):
    pts = ['は','が','を','に','へ','と','も','進','で','の','から','まで']
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
            return f'<audio controls style="width:100%; height:38px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except: pass
    return ""

def reset_state():
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

# --- 4. 邏輯初始化 ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx = 0
if 'num_q' not in st.session_state:
    st.session_state.num_q = 10
if 'ans' not in st.session_state:
    reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄 (絕對不會失蹤，因為沒有全頁重整)
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
            st.session_state.shuf = list(word_tokens)
            random.seed(st.session_state.q_idx)
            random.shuffle(st.session_state.shuf)

        st.caption(f"Q{st.session_state.q_idx + 1} | {cn_text}")

        # A. 答案展示區
        curr_ans_copy = list(st.session_state.ans)
        ans_html = '<div class="res-box">'
        for s in sentence_struct:
            if s['type'] == 'punc': 
                ans_html += f'<span style="font-size:18px; color:#94a3b8; font-weight:bold;">{s["content"]}</span>'
            else:
                val = curr_ans_copy.pop(0) if curr_ans_copy else ""
                ans_html += f'<div class="word-slot">{val}</div>'
        ans_html += '</div>'
        st.markdown(ans_html, unsafe_allow_html=True)

        st.write("---")

        # B. 單字池 (實體按鈕併排)
        num_shuf = len(st.session_state.shuf)
        word_cols = st.columns(num_shuf if num_shuf > 0 else 1)
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                if word_cols[idx].button(t, key=f"p_{st.session_state.q_idx}_{idx}"):
                    st.session_state.ans.append(t)
                    st.session_state.used_history.append(idx)
                    st.rerun()

        # C. 功能鍵 (置底併排)
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
                else: st.error("順序不對喔！")

        if st.session_state.is_correct:
            st.success("正解！")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("CONTINUE ➡️", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
              
