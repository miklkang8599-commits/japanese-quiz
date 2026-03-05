"""
================================================================
【技術演進與邏輯追蹤表 - v7.1 操作引導強化版】
----------------------------------------------------------------
1. 引導邏輯：
   - 新增「區塊提示語」，明確區分單字選擇區與系統操作區。
   - 強化視覺層次，讓使用者一眼看出操作流程：選詞 -> 檢查 -> 導航。
2. 視覺修正：
   - 維持全域置中 (max-width: 500px) 避免偏向一邊。
   - 修正按鈕 3D 質感，提升「點擊」的視覺誘因。
3. 側邊欄策略：
   - 繼續維持 st.expander 作為「練習設定」，保證手機端 100% 可控。
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
st.set_page_config(page_title="🇯🇵 日文重組 v7.1", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }
    
    /* 置中容器與背景 */
    .block-container { padding: 1rem 0.8rem !important; max-width: 480px !important; margin: 0 auto !important; }
    [data-testid="stHeader"] { display: none; }

    /* 答案格位 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 6px; 
        background-color: #ffffff; padding: 12px; 
        border-radius: 15px; border: 2px solid #e5e7eb; 
        min-height: 50px; align-items: center; justify-content: center;
        box-shadow: 0 4px 0 #e5e7eb; margin-bottom: 10px;
    }
    .word-slot { 
        min-width: 32px; height: 28px; border-bottom: 2px solid #afafaf; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 16px; color: #1cb0f6; font-weight: bold; margin: 0 2px;
    }

    /* 單字池容器強制置中 */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
        display: flex !important; flex-wrap: wrap !important;
        flex-direction: row !important; gap: 8px !important;
        justify-content: center !important;
    }

    /* 杜林風格按鈕 */
    div.stButton > button {
        width: auto !important; min-width: 45px !important;
        padding: 6px 14px !important; border-radius: 12px !important;
        font-size: 16px !important; font-weight: bold !important;
        background-color: white !important; color: #4b4b4b !important;
        border: 2px solid #e5e7eb !important;
        border-bottom: 4px solid #e5e7eb !important;
    }
    
    /* 功能提示文字樣式 */
    .hint-text {
        font-size: 13px; color: #afafaf; font-weight: bold;
        margin: 10px 0 5px 0; text-align: center;
    }

    /* 系統操作按鈕樣式 */
    .control-btns div.stButton > button {
        padding: 4px 8px !important; font-size: 13px !important;
        color: #777 !important; border-bottom: 2px solid #e5e7eb !important;
    }

    .stInfo { border-radius: 12px; background-color: #ddf4ff; color: #1899d6; border: none; text-align: center; font-size: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心函數 ---
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

# --- 3. 執行邏輯 ---
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0
if 'num_q' not in st.session_state: st.session_state.num_q = 10
if 'ans' not in st.session_state: reset_state()

df, cols = load_data()

if df is not None:
    # 設置選單
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

        # B. 單字池 (新增區塊提示)
        st.markdown('<div class="hint-text">▼ 請點選單字按鈕</div>', unsafe_allow_html=True)
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                if st.button(t, key=f"p_{st.session_state.q_idx}_{idx}"):
                    st.session_state.ans.append(t)
                    st.session_state.used_history.append(idx)
                    st.rerun()

        # C. 系統操作 (新增區塊提示)
        st.write(" ")
        st.markdown('<div class="hint-text">▼ 系統控制</div>', unsafe_allow_html=True)
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

        # D. 檢查答案
        st.divider()
        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(word_tokens):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔！再想一想吧 💡")

        if st.session_state.is_correct:
            st.success("正解！太厲害了 🎉")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("繼續挑戰下一題 ➡️", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
