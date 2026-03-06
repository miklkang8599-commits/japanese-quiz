"""
================================================================
【技術演進與邏輯追蹤表 - v11.0 回歸簡約版】
----------------------------------------------------------------
1. 視覺回歸：
   - 移除所有複雜的 Flexbox 網格強制設定。
   - 使用最基本的 st.columns 佈局，讓按鈕回歸自然大小。
2. 標籤簡化：
   - 恢復簡單的文字與圖示組合，不再使用長標籤。
3. 核心鎖定：
   - 預設 5 題、自然排序、索引重置 (平假名對位正確)。
----------------------------------------------------------------
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 1. 頁面配置與基礎 CSS ---
st.set_page_config(page_title="🇯🇵 日文重組 v11.0", layout="wide")

st.markdown("""
    <style>
    .block-container { padding: 0.8rem 0.5rem !important; max-width: 450px !important; margin: 0 auto !important; }
    [data-testid="stHeader"] { display: none; }
    
    .res-box { 
        display: flex; flex-wrap: wrap; gap: 6px; background-color: #ffffff; padding: 10px; 
        border-radius: 10px; border: 2px solid #e5e7eb; min-height: 45px; 
        align-items: center; justify-content: center; box-shadow: 0 3px 0 #e5e7eb; margin-bottom: 10px;
    }
    .word-slot { 
        min-width: 25px; border-bottom: 2px solid #afafaf; 
        text-align: center; font-size: 16px; color: #1cb0f6; font-weight: bold; margin: 0 2px;
    }

    /* 單字按鈕樣式 */
    div.stButton > button {
        border-radius: 12px !important;
        font-weight: bold !important;
        background-color: white !important;
        border: 2px solid #e5e7eb !important;
        border-bottom: 4px solid #e5e7eb !important;
    }
    
    .stInfo { border-radius: 10px; font-size: 15px; margin-bottom: 10px; }
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
            return f'<audio controls style="width:100%; height:32px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except: pass
    return ""

# --- 3. 初始化 (預設 5 題) ---
if 'num_q' not in st.session_state: st.session_state.num_q = 5
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0
if 'ans' not in st.session_state: st.session_state.ans = []
if 'used_history' not in st.session_state: st.session_state.used_history = []
if 'is_correct' not in st.session_state: st.session_state.is_correct = False
if 'curr_q_data' not in st.session_state: st.session_state.curr_q_data = None
if 'last_config' not in st.session_state: st.session_state.last_config = ""

df, cols = load_data()

if df is not None:
    with st.expander("⚙️ 練習設定", expanded=False):
        unit_list = sorted(df[cols['unit']].astype(str).unique(), key=natural_sort_key)
        sel_unit = st.selectbox("選擇單元", unit_list)
        unit_df = df[df[cols['unit']].astype(str) == sel_unit]
        ch_list = sorted(unit_df[cols['ch']].astype(str).unique(), key=natural_sort_key)
        sel_start_ch = st.selectbox("起始章節", ch_list)
        
        st.session_state.num_q = st.number_input("練習題數", min_value=1, value=st.session_state.num_q)
        
        current_config = f"{sel_unit}_{sel_start_ch}_{st.session_state.num_q}"
        if st.session_state.last_config != current_config:
            st.session_state.last_config = current_config
            st.session_state.q_idx = 0
            reset_state(); st.rerun()

        filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch].reset_index(drop=True)
        preview_mode = st.checkbox("預習模式")

    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if preview_mode:
        for i, item in enumerate(quiz_list):
            st.write(f"**{i+1}. {item[cols['cn']]}**")
            st.write(f"{item[cols['ja']]}")
            if cols['kana'] and pd.notna(item.get(cols['kana'])):
                st.write(f"（{item[cols['kana']]}）")
            st.markdown(get_audio_html(item[cols['ja']]), unsafe_allow_html=True); st.divider()
    
    elif st.session_state.q_idx < len(quiz_list):
        if st.session_state.curr_q_data is None:
            q_raw = quiz_list[st.session_state.q_idx]
            ja_txt = str(q_raw[cols['ja']]).strip()
            struct = get_sentence_structure(ja_txt)
            tokens = [s['content'] for s in struct if s['type'] == 'word']
            shuf_list = list(tokens); random.seed(st.session_state.q_idx); random.shuffle(shuf_list)
            st.session_state.curr_q_data = {
                "ja": ja_txt, "cn": q_raw[cols['cn']],
                "kana": q_raw.get(cols['kana']) if cols['kana'] else None,
                "struct": struct, "tokens": tokens, "shuf": shuf_list
            }

        q = st.session_state.curr_q_data
        st.info(f"Q{st.session_state.q_idx + 1} | {q['cn']}")

        # A. 答案展示區
        curr_ans_copy = list(st.session_state.ans)
        ans_html = '<div class="res-box">'
        for s in q['struct']:
            if s['type'] == 'punc': ans_html += f'<span>{s["content"]}</span>'
            else:
                val = curr_ans_copy.pop(0) if curr_ans_copy else ""
                ans_html += f'<div class="word-slot">{val}</div>'
        ans_html += '</div>'
        st.markdown(ans_html, unsafe_allow_html=True)

        # B. 單字池
        st.caption("▼ 請點選單字")
        cols_words = st.columns(len(q['shuf']))
        for idx, t in enumerate(q['shuf']):
            if idx not in st.session_state.used_history:
                if cols_words[idx].button(t, key=f"w_{idx}"):
                    st.session_state.ans.append(t); st.session_state.used_history.append(idx); st.rerun()

        # C. 系統控制
        st.caption("▼ 系統操作")
        c_nav = st.columns(4)
        if c_nav[0].button("⬅ 退回"):
            if st.session_state.used_history:
                st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        if c_nav[1].button("🔄 重填"): reset_state(); st.rerun()
        if c_nav[2].button("⏮ 上一題"): 
            st.session_state.q_idx = max(0, st.session_state.q_idx-1); reset_state(); st.rerun()
        if c_nav[3].button("⏭ 下一題"): 
            st.session_state.q_idx = min(len(quiz_list)-1, st.session_state.q_idx+1); reset_state(); st.rerun()

        # D. 檢查與結果
        if len(st.session_state.ans) == len(q['tokens']) and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(q['tokens']):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔！")

        if st.session_state.is_correct:
            st.success("正解！🎉")
            if q['kana']: st.write(f"讀音：{q['kana']}")
            st.markdown(get_audio_html(q['ja']), unsafe_allow_html=True)
            if st.button("👉 下一題", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
    else:
        st.balloons(); st.success("完成！")
        if st.button("從頭開始"): st.session_state.q_idx = 0; reset_state(); st.rerun()
