"""
================================================================
【日文結構練習器 - v6.3 操作介面優化版】
----------------------------------------------------------------
更新日誌：
1. 語意化按鈕：功能鍵名稱清晰化 (上一題、下一題、重填、退回)。
2. 視覺區隔：利用 CSS 強化按鈕與答案格的視覺邊界。
3. 手機優先：針對 iPhone 直立屏進行最終比例微調。
4. 側邊欄守護：不影響 Streamlit 原生側邊欄導航功能。
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
st.set_page_config(page_title="🇯🇵 日文重組 v6.3", layout="wide")

# --- 2. 精準 CSS (針對單字併排與介面壓縮) ---
st.markdown("""
    <style>
    /* 1. 答案區：扁平化格位 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 4px; 
        background-color: #ffffff; padding: 12px; 
        border-radius: 12px; border: 1.5px solid #e5e7eb; 
        min-height: 50px; align-items: center; margin-bottom: 15px;
    }
    .word-slot { 
        min-width: 32px; height: 26px; border-bottom: 2px solid #1cb0f6; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 17px; color: #1cb0f6; font-weight: bold; margin: 0 2px;
    }
    
    /* 2. 單字池容器：強制併排換行 */
    .st-emotion-cache-12w0qpk { 
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 6px !important;
    }
    
    /* 3. 按鈕樣式：實體立體感 */
    div.stButton > button {
        border-radius: 10px !important;
        border: 1px solid #e5e7eb !important;
        border-bottom: 3.5px solid #e5e7eb !important;
        padding: 6px 12px !important;
        font-size: 15px !important;
        font-weight: bold !important;
        width: auto !important;
    }
    
    /* 4. 控制區按鈕字體稍微縮小以利併排 */
    [data-testid="column"] div.stButton > button {
        font-size: 14px !important;
        padding: 4px 8px !important;
    }

    .block-container { padding-top: 1rem !important; }
    [data-testid="stHeader"] { display: none; }
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
            return f'<audio controls style="width:100%; height:38px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except: pass
    return ""

def reset_state():
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

# --- 4. 初始化 ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx = 0
if 'num_q' not in st.session_state:
    st.session_state.num_q = 10
if 'ans' not in st.session_state:
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
            st.write(f"**{i+1}. {item[cols['cn']]}**\n{item[cols['ja']]}")
            st.markdown(get_audio_html(item[cols['ja']]), unsafe_allow_html=True)
            st.divider()
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw, cn_text = str(q[cols['ja']]).strip(), q[cols['cn']]
        sentence_struct = get_sentence_structure(ja_raw)
        word_tokens = [s['content'] for s in sentence_struct if s['type'] == 'word']
        
        if not st.session_state.shuf:
            random.seed(st.session_state.q_idx)
            st.session_state.shuf = list(word_tokens)
            random.shuffle(st.session_state.shuf)

        st.caption(f"第 {st.session_state.q_idx + 1} 題 / 共 {len(quiz_list)} 題")
        st.info(f"中文意譯：{cn_text}")

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

        # B. 單字選擇池 (利用 Flexbox Wrap 併排)
        st.write("▼ 請選擇單字按鈕：")
        # 直接生成按鈕，不使用 columns 以避免手機斷行
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                if st.button(t, key=f"p_{st.session_state.q_idx}_{idx}"):
                    st.session_state.ans.append(t)
                    st.session_state.used_history.append(idx)
                    st.rerun()

        # C. 功能控制鍵 (置底且名稱清晰)
        st.write("---")
        # 這裡的 columns 僅用於功能鍵分配，CSS 已設定強制併排
        nav_cols = st.columns(4)
        if nav_cols[0].button("⏮ 上一題"): 
            st.session_state.q_idx = max(0, st.session_state.q_idx-1); reset_state(); st.rerun()
        if nav_cols[1].button("⏭ 下一題"): 
            st.session_state.q_idx = min(len(quiz_list)-1, st.session_state.q_idx+1); reset_state(); st.rerun()
        if nav_cols[2].button("🔄 重填"): 
            reset_state(); st.rerun()
        if nav_cols[3].button("⬅ 退回"):
            if st.session_state.used_history:
                st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            if st.button("🔍 檢查答案是否正確", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(word_tokens):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔，請再檢查一下！")

        if st.session_state.is_correct:
            st.success("正解！太棒了！")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("繼續挑戰下一題 ➡️", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
