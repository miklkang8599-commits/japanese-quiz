"""
================================================================
【技術演進與邏輯追蹤表 - v7.0 視覺美化最終版】
----------------------------------------------------------------
1. 視覺翻新：
   - 捨棄所有靠左對齊，實施「全域置中佈局」。
   - 按鈕池透過 CSS Flexbox 實現對稱併排，模擬 Duolingo APP 質感。
2. 空間平衡：
   - 答案格位與按鈕間距精確調整，解決畫面偏向一邊的問題。
3. 實體按鈕回歸：
   - 為了確保點擊反應與側邊欄不失蹤，回歸原生按鈕但套用強化 CSS 樣式。
----------------------------------------------------------------
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 1. 頁面配置與美學 CSS ---
st.set_page_config(page_title="🇯🇵 日文重組 v7.0", layout="wide")

st.markdown("""
    <style>
    /* 全域字體與背景 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
    html, body, [class*="css"]  { font-family: 'Noto Sans JP', sans-serif; }
    
    .block-container { padding: 1.5rem 1rem !important; max-width: 500px !important; margin: 0 auto !important; }
    [data-testid="stHeader"] { display: none; }

    /* 答案區：置中且帶有美感陰影 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 6px; 
        background-color: #ffffff; padding: 15px; 
        border-radius: 15px; border: 2px solid #e5e7eb; 
        min-height: 55px; align-items: center; justify-content: center;
        box-shadow: 0 4px 0 #e5e7eb; margin-bottom: 20px;
    }
    .word-slot { 
        min-width: 35px; height: 30px; border-bottom: 2px solid #afafaf; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 18px; color: #1cb0f6; font-weight: bold; margin: 0 3px;
    }

    /* 單字池：強制對稱併排 */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
        display: flex !important; flex-wrap: wrap !important;
        flex-direction: row !important; gap: 8px !important;
        justify-content: center !important; /* 置中關鍵 */
    }

    /* 按鈕樣式：Duolingo 3D 質感 */
    div.stButton > button {
        width: auto !important; min-width: 50px !important;
        padding: 8px 16px !important; border-radius: 12px !important;
        font-size: 16px !important; font-weight: bold !important;
        background-color: white !important; color: #4b4b4b !important;
        border: 2px solid #e5e7eb !important;
        border-bottom: 4px solid #e5e7eb !important;
        transition: all 0.1s;
    }
    div.stButton > button:active {
        border-bottom: 2px solid #e5e7eb !important;
        transform: translateY(2px);
    }
    
    /* 系統操作按鈕：更精緻 */
    .control-btns div.stButton > button {
        padding: 4px 10px !important; font-size: 14px !important;
        color: #afafaf !important; border-bottom: 2px solid #e5e7eb !important;
    }

    /* 標題與說明 */
    .stCaption { text-align: center; color: #afafaf; font-weight: bold; }
    .stInfo { border-radius: 12px; background-color: #ddf4ff; color: #1899d6; border: none; text-align: center; }
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
            return f'<audio controls style="width:100%; height:32px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except: pass
    return ""

def reset_state():
    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct = [], [], [], False

# --- 3. 初始化 ---
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0
if 'num_q' not in st.session_state: st.session_state.num_q = 10
if 'ans' not in st.session_state: reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄改為清爽版
    with st.expander("⚙️ 練習設定", expanded=False):
        unit_list = sorted(df[cols['unit']].astype(str).unique())
        sel_unit = st.selectbox("選擇單元", unit_list)
        unit_df = df[df[cols['unit']].astype(str) == sel_unit]
        sel_start_ch = st.selectbox("起始章節", sorted(unit_df[cols['ch']].astype(str).unique()))
        filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
        preview_mode = st.checkbox("📖 預習模式")

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

        st.caption(f"第 {st.session_state.q_idx + 1} 題 / 共 {len(quiz_list)} 題")
        st.info(f"{cn_text}")

        # A. 答案展示區
        curr_ans_copy = list(st.session_state.ans)
        ans_html = '<div class="res-box">'
        for s in sentence_struct:
            if s['type'] == 'punc': ans_html += f'<span style="color:#afafaf;">{s["content"]}</span>'
            else:
                val = curr_ans_copy.pop(0) if curr_ans_copy else ""
                ans_html += f'<div class="word-slot">{val}</div>'
        ans_html += '</div>'
        st.markdown(ans_html, unsafe_allow_html=True)

        # B. 單字選擇池 (併排對稱)
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                if st.button(t, key=f"p_{st.session_state.q_idx}_{idx}"):
                    st.session_state.ans.append(t)
                    st.session_state.used_history.append(idx)
                    st.rerun()

        # C. 系統操作 (精緻化)
        st.write(" ")
        st.markdown('<div class="control-btns">', unsafe_allow_html=True)
        nav_cols = st.columns(4)
        if nav_cols[0].button("⬅ 退回"):
            if st.session_state.used_history:
                st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        if nav_cols[1].button("🔄 重填"): reset_state(); st.rerun()
        if nav_cols[2].button("⏮ 上一題"): 
            st.session_state.q_idx = max(0, st.session_state.q_idx-1); reset_state(); st.rerun()
        if nav_cols[3].button("⏭ 下一題"): 
            st.session_state.q_idx = min(len(quiz_list)-1, st.session_state.q_idx+1); reset_state(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # D. 檢查與結果 (底部置中)
        st.divider()
        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(word_tokens):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("不對喔！再想一想吧 💡")

        if st.session_state.is_correct:
            st.success("正解！太厲害了 🎉")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("繼續 ➡️", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
