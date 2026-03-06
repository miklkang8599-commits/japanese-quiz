"""
================================================================
【技術演進與邏輯追蹤表 - v8.7 按鈕文字與邏輯修復】
----------------------------------------------------------------
1. 標籤與邏輯同步：
   - 確保「🔍 檢查答案」與「👉 進入下一題練習」文字 100% 顯示。
   - 修正按鈕 Key 值，避免 Streamlit 因元件變動導致點擊失效。
2. 空間管理：
   - 壓縮系統控制區高度，確保「檢查答案」結果在 iPhone 上不需捲動即可看見。
3. 核心功能維持：
   - 預設 5 題、自然排序、平假名精準對位 (v8.5 索引修正)。
----------------------------------------------------------------
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 1. 頁面配置與 CSS ---
st.set_page_config(page_title="🇯🇵 日文重組 v8.7", layout="wide")

st.markdown("""
    <style>
    .block-container { padding: 0.8rem 0.5rem !important; max-width: 450px !important; margin: 0 auto !important; }
    [data-testid="stHeader"] { display: none; }
    
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

    [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
        display: flex !important; flex-wrap: wrap !important;
        flex-direction: row !important; gap: 6px !important; justify-content: center !important;
    }

    div.stButton > button {
        width: auto !important; min-width: 45px !important;
        padding: 6px 12px !important; border-radius: 12px !important;
        font-size: 15px !important; font-weight: bold !important;
        background-color: white !important; border: 2px solid #e5e7eb !important;
        border-bottom: 3.5px solid #e5e7eb !important;
    }
    
    /* 系統操作按鈕標籤微調 */
    .control-row div.stButton > button {
        padding: 4px 6px !important; font-size: 12px !important;
        color: #777 !important; border-radius: 8px !important;
    }

    .num-display { text-align: center; font-size: 18px; font-weight: bold; color: #1cb0f6; line-height: 35px; }
    .hint-text { font-size: 11px; color: #ccc; text-align: center; margin-bottom: 2px; }
    .stInfo { padding: 8px !important; border-radius: 10px; font-size: 14px; margin-bottom: 8px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心函數 ---
def reset_state():
    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct = [], [], [], False
    st.session_state.curr_q_data = None

@st.cache_data(ttl=60)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA/export?format=csv&gid=1337973082"
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        mapping = {
            "ja": "日文原文", "cn": "中文意譯", 
            "kana": "平假名" if "平假名" in df.columns else ("假名" if "假名" in df.columns else None),
            "unit": "單元", "ch": "章節"
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

# --- 3. 初始化 ---
if 'num_q' not in st.session_state: st.session_state.num_q = 5
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0
if 'ans' not in st.session_state: reset_state()
if 'last_config' not in st.session_state: st.session_state.last_config = ""
if 'curr_q_data' not in st.session_state: st.session_state.curr_q_data = None

df, cols = load_data()

if df is not None:
    with st.expander("⚙️ 練習設定", expanded=False):
        unit_list = sorted(df[cols['unit']].astype(str).unique(), key=natural_sort_key)
        sel_unit = st.selectbox("單元選擇", unit_list)
        unit_df = df[df[cols['unit']].astype(str) == sel_unit]
        ch_list = sorted(unit_df[cols['ch']].astype(str).unique(), key=natural_sort_key)
        sel_start_ch = st.selectbox("起始章節", ch_list)
        
        st.write("題數調整：")
        c1, c2, c3 = st.columns([1, 1, 1])
        if c1.button("➖"): st.session_state.num_q = max(1, st.session_state.num_q - 1)
        with c2: st.markdown(f'<div class="num-display">{st.session_state.num_q}</div>', unsafe_allow_html=True)
        if c3.button("➕"): st.session_state.num_q = min(50, st.session_state.num_q + 1)
        
        current_config = f"{sel_unit}_{sel_start_ch}_{st.session_state.num_q}"
        if st.session_state.last_config != current_config:
            st.session_state.last_config = current_config
            st.session_state.q_idx = 0
            reset_state()
            st.rerun()

        filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch].reset_index(drop=True)
        preview_mode = st.checkbox("預習模式")

    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if preview_mode:
        for i, item in enumerate(quiz_list):
            st.subheader(f"No. {i+1}")
            st.write(f"**中文：** {item[cols['cn']]}")
            st.write(f"**日文：** {item[cols['ja']]}")
            if cols['kana'] and pd.notna(item.get(cols['kana'])):
                st.write(f"**平假名：** {item[cols['kana']]}")
            st.markdown(get_audio_html(item[cols['ja']]), unsafe_allow_html=True)
            st.divider()
    
    elif st.session_state.q_idx < len(quiz_list):
        if st.session_state.curr_q_data is None:
            q_raw = quiz_list[st.session_state.q_idx]
            ja_txt = str(q_raw[cols['ja']]).strip()
            struct = get_sentence_structure(ja_txt)
            tokens = [s['content'] for s in struct if s['type'] == 'word']
            shuf_list = list(tokens)
            random.seed(st.session_state.q_idx)
            random.shuffle(shuf_list)
            st.session_state.curr_q_data = {
                "ja": ja_txt, "cn": q_raw[cols['cn']],
                "kana": q_raw.get(cols['kana']) if cols['kana'] else None,
                "struct": struct, "tokens": tokens, "shuf": shuf_list
            }

        q = st.session_state.curr_q_data
        st.info(f"Q{st.session_state.q_idx + 1}/{len(quiz_list)} | {q['cn']}")

        ans_html = '<div class="res-box">'
        curr_ans_copy = list(st.session_state.ans)
        for s in q['struct']:
            if s['type'] == 'punc': ans_html += f'<span style="color:#ccc;">{s["content"]}</span>'
            else:
                val = curr_ans_copy.pop(0) if curr_ans_copy else ""
                ans_html += f'<div class="word-slot">{val}</div>'
        ans_html += '</div>'
        st.markdown(ans_html, unsafe_allow_html=True)

        st.markdown('<div class="hint-text">▼ 點選單字按鈕</div>', unsafe_allow_html=True)
        for idx, t in enumerate(q['shuf']):
            if idx not in st.session_state.used_history:
                if st.button(t, key=f"p_{st.session_state.q_idx}_{idx}"):
                    st.session_state.ans.append(t); st.session_state.used_history.append(idx); st.rerun()

        # 系統控制
        st.markdown('<div class="hint-text">▼ 系統控制</div>', unsafe_allow_html=True)
        st.markdown('<div class="control-row">', unsafe_allow_html=True)
        nav_cols = st.columns(4)
        if nav_cols[0].button("⬅ 退回一格"):
            if st.session_state.used_history:
                st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        if nav_cols[1].button("🔄 全部重填"): reset_state(); st.rerun()
        if nav_cols[2].button("⏮ 上一題"): 
            st.session_state.q_idx = max(0, st.session_state.q_idx-1); reset_state(); st.rerun()
        if nav_cols[3].button("⏭ 下一題"): 
            st.session_state.q_idx = min(len(quiz_list)-1, st.session_state.q_idx+1); reset_state(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # 【修復重點】檢查與導航邏輯
        st.write(" ")
        if len(st.session_state.ans) == len(q['tokens']) and not st.session_state.is_correct:
            # 修改按鈕文字與 Key
            if st.button("🔍 檢查答案", type="primary", use_container_width=True, key="check_btn"):
                if "".join(st.session_state.ans) == "".join(q['tokens']):
                    st.session_state.is_correct = True
                    st.rerun()
                else: st.error("順序不對喔！💡")

        if st.session_state.is_correct:
            st.success("正解！🎉")
            if q['kana'] and pd.notna(q['kana']):
                st.markdown(f"**平假名：** {q['kana']}")
            st.markdown(get_audio_html(q['ja']), unsafe_allow_html=True)
            # 修改按鈕文字與 Key
            if st.button("👉 進入下一題練習", type="primary", use_container_width=True, key="next_btn"): 
                st.session_state.q_idx += 1
                reset_state()
                st.rerun()
    else:
        st.balloons()
        st.success("全部題數練習完成！")
        if st.button("🔄 重新開始練習"): st.session_state.q_idx = 0; reset_state(); st.rerun()
