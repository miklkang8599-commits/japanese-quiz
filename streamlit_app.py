"""
================================================================
【技術演進與邏輯追蹤表 - v7.9 功能鎖定與預習擴充】
----------------------------------------------------------------
1. 核心承諾：
   - 絕不改動已修復的功能：預設 5 題、自然排序、按鈕尺寸、功能鍵順序。
2. 預習模式 (Preview Mode) 升級：
   - 依照要求，在預習清單中列出：中文 -> 日文 -> 平假名 -> 聲音播放。
3. 資料欄位：
   - 自動對應 Google Sheets 中的「平假名」欄位並顯示。
----------------------------------------------------------------
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 1. 頁面配置與美學 CSS (維持 v7.7~v7.8 穩定版) ---
st.set_page_config(page_title="🇯🇵 日文重組 v7.9", layout="wide")

st.markdown("""
    <style>
    .block-container { padding: 0.8rem 0.5rem !important; max-width: 450px !important; margin: 0 auto !important; }
    [data-testid="stHeader"] { display: none; }

    /* 答案區 */
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 4px; background-color: #ffffff; padding: 10px; 
        border-radius: 10px; border: 1.5px solid #e5e7eb; min-height: 42px; 
        align-items: center; justify-content: center; box-shadow: 0 3px 0 #e5e7eb; margin-bottom: 5px;
    }
    .word-slot { 
        min-width: 25px; height: 22px; border-bottom: 2px solid #afafaf; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 15px; color: #1cb0f6; font-weight: bold; margin: 0 2px;
    }

    /* 單字池置中 */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
        display: flex !important; flex-wrap: wrap !important;
        flex-direction: row !important; gap: 8px !important; justify-content: center !important;
    }

    /* 主按鈕樣式 */
    div.stButton > button {
        width: auto !important; min-width: 45px !important;
        padding: 6px 14px !important; border-radius: 12px !important;
        font-size: 16px !important; font-weight: bold !important;
        background-color: white !important; border: 2px solid #e5e7eb !important;
        border-bottom: 3.5px solid #e5e7eb !important;
    }
    
    /* 系統操作按鈕標籤 */
    .control-row div.stButton > button {
        padding: 4px 10px !important; font-size: 13px !important;
        color: #777 !important; border-radius: 8px !important;
    }

    /* 設定區精緻加減按鈕 */
    .setting-area div.stButton > button {
        min-width: 35px !important; height: 35px !important;
        font-size: 14px !important; padding: 0px !important;
    }

    .num-display { 
        text-align: center; font-size: 18px; font-weight: bold; 
        color: #1cb0f6; line-height: 35px;
    }

    .hint-text { font-size: 12px; color: #ccc; text-align: center; margin-bottom: 2px; }
    .stInfo { padding: 8px !important; border-radius: 10px; font-size: 14px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心函數 ---
@st.cache_data(ttl=60)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA/export?format=csv&gid=1337973082"
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        mapping = {
            "ja": "日文原文", 
            "cn": "中文意譯", 
            "kana": "平假名" if "平假名" in df.columns else ("假名" if "假名" in df.columns else None),
            "unit": "單元", 
            "ch": "章節"
        }
        return df.dropna(subset=["日文原文", "中文意譯"]), mapping
    except: return None, None

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', str(s))]

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
            return f'<audio controls style="width:100%; height:30px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except: pass
    return ""

def reset_state():
    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct = [], [], [], False

# --- 3. 初始化 (維持預設 5 題) ---
if 'num_q' not in st.session_state: st.session_state.num_q = 5
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0
if 'ans' not in st.session_state: reset_state()

df, cols = load_data()

if df is not None:
    with st.expander("⚙️ 練習設定", expanded=False):
        unit_list = sorted(df[cols['unit']].astype(str).unique(), key=natural_sort_key)
        sel_unit = st.selectbox("單元選擇", unit_list)
        unit_df = df[df[cols['unit']].astype(str) == sel_unit]
        
        ch_list = sorted(unit_df[cols['ch']].astype(str).unique(), key=natural_sort_key)
        sel_start_ch = st.selectbox("起始章節", ch_list)
        
        st.write("題數調整：")
        st.markdown('<div class="setting-area">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1, 1])
        if c1.button("➖"):
            st.session_state.num_q = max(1, st.session_state.num_q - 1)
        with c2:
            st.markdown(f'<div class="num-display">{st.session_state.num_q}</div>', unsafe_allow_html=True)
        if c3.button("➕"):
            st.session_state.num_q = min(50, st.session_state.num_q + 1)
        st.markdown('</div>', unsafe_allow_html=True)
        
        filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
        preview_mode = st.checkbox("預習模式")

    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    # --- 預習模式 (依照要求排序) ---
    if preview_mode:
        for i, item in enumerate(quiz_list):
            st.subheader(f"No. {i+1}")
            st.write(f"**中文：** {item[cols['cn']]}")
            st.write(f"**日文：** {item[cols['ja']]}")
            if cols['kana'] and pd.notna(item[cols['kana']]):
                st.write(f"**平假名：** {item[cols['kana']]}")
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

        st.info(f"Q{st.session_state.q_idx + 1}/{len(quiz_list)} | {cn_text}")

        ans_html = '<div class="res-box">'
        curr_ans_copy = list(st.session_state.ans)
        for s in sentence_struct:
            if s['type'] == 'punc': ans_html += f'<span style="color:#ccc;">{s["content"]}</span>'
            else:
                val = curr_ans_copy.pop(0) if curr_ans_copy else ""
                ans_html += f'<div class="word-slot">{val}</div>'
        ans_html += '</div>'
        st.markdown(ans_html, unsafe_allow_html=True)

        st.markdown('<div class="hint-text">▼ 點選單字按鈕</div>', unsafe_allow_html=True)
        for idx, t in enumerate(st.session_state.shuf):
            if idx not in st.session_state.used_history:
                if st.button(t, key=f"p_{st.session_state.q_idx}_{idx}"):
                    st.session_state.ans.append(t); st.session_state.used_history.append(idx); st.rerun()

        st.markdown('<div class="hint-text">▼ 系統控制</div>', unsafe_allow_html=True)
        st.markdown('<div class="control-row">', unsafe_allow_html=True)
        nav_cols = st.columns(4)
        if nav_cols[0].button("⬅ 退回"):
            if st.session_state.used_history:
                st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        if nav_cols[1].button("🔄 重填"): reset_state(); st.rerun()
        if nav_cols[2].button("⏮ 上題"): 
            st.session_state.q_idx = max(0, st.session_state.q_idx-1); reset_state(); st.rerun()
        if nav_cols[3].button("⏭ 下題"): 
            st.session_state.q_idx = min(len(quiz_list)-1, st.session_state.q_idx+1); reset_state(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            st.write(" ")
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(word_tokens):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔！💡")

        if st.session_state.is_correct:
            st.success("正解！🎉")
            if cols['kana'] and pd.notna(q[cols['kana']]):
                st.markdown(f"**平假名：** {q[cols['kana']]}")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("繼續挑戰下一題 ➡️", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
