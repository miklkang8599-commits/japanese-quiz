"""
================================================================
【技術演進與邏輯追蹤表 - v12.2.3 章節輸入優化】
----------------------------------------------------------------
1. 交互優化 (針對章節選擇不便)：
   - 將「起始章節」由 Selectbox 改為 Number Input，支援手動輸入三位數編號。
   - 自動偵測該單元的最小與最大章節編號，防止輸入無效範圍。
2. 邏輯穩定性：
   - 維持 v12.2.2 的數值化過濾，確保三位數章節抓題 100% 正確。
3. 核心功能維持：
   - 平假名優先發音、版本標註、流式按鈕佈局。
----------------------------------------------------------------
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 版本編號 ---
VERSION = "v12.2.20260311.INPUT_FIX"

# --- 1. 頁面配置 ---
st.set_page_config(page_title=f"🇯🇵 日文重組 {VERSION}", layout="wide")

st.markdown(f"""
    <style>
    .block-container {{ padding: 0.8rem 0.5rem !important; max-width: 450px !important; margin: 0 auto !important; }}
    [data-testid="stHeader"] {{ display: none; }}
    .res-box {{ 
        display: flex; flex-wrap: wrap; gap: 6px; background-color: #ffffff; padding: 10px; 
        border-radius: 10px; border: 2px solid #e5e7eb; min-height: 45px; 
        align-items: center; justify-content: center; box-shadow: 0 3px 0 #e5e7eb; margin-bottom: 10px;
    }}
    .word-slot {{ 
        min-width: 25px; border-bottom: 2px solid #afafaf; 
        text-align: center; font-size: 16px; color: #1cb0f6; font-weight: bold; margin: 0 2px;
    }}
    div.stButton > button {{
        width: auto !important; min-width: 45px !important; white-space: nowrap !important;
        border-radius: 12px !important; font-weight: bold !important;
        background-color: white !important; border: 2px solid #e5e7eb !important;
        border-bottom: 4px solid #e5e7eb !important; margin: 4px 2px !important;
    }}
    .version-tag {{ font-size: 10px; color: #ccc; text-align: right; margin-bottom: 10px; }}
    .range-info {{ font-size: 12px; color: #666; background: #f0f7ff; padding: 5px 10px; border-radius: 5px; margin-bottom: 10px; }}
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

def get_audio_html(text, kana=None):
    audio_input = kana if kana and pd.notna(kana) else text
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={audio_input}"
    try:
        res = requests.get(tts_url)
        if res.status_code == 200:
            b64 = base64.b64encode(res.content).decode()
            return f'<audio controls style="width:100%; height:32px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except: pass
    return ""

# --- 3. 初始化 ---
if 'num_q' not in st.session_state: st.session_state.num_q = 5
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0
if 'ans' not in st.session_state: st.session_state.ans = []
if 'used_history' not in st.session_state: st.session_state.used_history = []
if 'is_correct' not in st.session_state: st.session_state.is_correct = False
if 'curr_q_data' not in st.session_state: st.session_state.curr_q_data = None
if 'last_config' not in st.session_state: st.session_state.last_config = ""

st.markdown(f'<div class="version-tag">Version: {VERSION}</div>', unsafe_allow_html=True)

df, cols = load_data()

if df is not None:
    # 確保章節列為數值型
    df[cols['ch']] = pd.to_numeric(df[cols['ch']], errors='coerce').fillna(0).astype(int)

    with st.expander("⚙️ 練習範圍設定", expanded=True):
        # 1. 選擇單元
        unit_names = sorted(df[cols['unit']].astype(str).unique())
        sel_unit = st.selectbox("1. 選擇單元", unit_names)
        unit_df = df[df[cols['unit']].astype(str) == sel_unit]
        
        # 取得該單元的章節極值
        min_ch = int(unit_df[cols['ch']].min())
        max_ch = int(unit_df[cols['ch']].max())
        
        # 【核心修正】將 Selectbox 改為 Number Input
        sel_start_ch = st.number_input(
            f"2. 起始章節編號 (範圍: {min_ch} ~ {max_ch})", 
            min_value=min_ch, 
            max_value=max_ch, 
            value=min_ch,
            step=1
        )
        
        # 3. 設定題數
        st.session_state.num_q = st.number_input("3. 練習總題數", min_value=1, value=st.session_state.num_q)
        
        # 偵測配置變更
        current_config = f"{sel_unit}_{sel_start_ch}_{st.session_state.num_q}"
        if st.session_state.last_config != current_config:
            st.session_state.last_config = current_config
            st.session_state.q_idx = 0
            reset_state(); st.rerun()

        filtered_df = unit_df[unit_df[cols['ch']] >= int(sel_start_ch)].reset_index(drop=True)
        preview_mode = st.checkbox("開啟預習模式")
        
        st.markdown(f'<div class="range-info">📍 練習：{sel_unit} / 第 {sel_start_ch} 章起 / 剩餘可用題數: {len(filtered_df)}</div>', unsafe_allow_html=True)

    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    # ... 後續答題邏輯與 v12.2.2 完全一致
    if preview_mode:
        for i, item in enumerate(quiz_list):
            st.write(f"**[{item[cols['ch']]}] {i+1}. {item[cols['cn']]}**")
            st.write(f"原文：{item[cols['ja']]}")
            kana_val = item[cols['kana']] if cols['kana'] and pd.notna(item.get(cols['kana'])) else None
            st.markdown(get_audio_html(item[cols['ja']], kana_val), unsafe_allow_html=True); st.divider()
    
    elif st.session_state.q_idx < len(quiz_list):
        if st.session_state.curr_q_data is None:
            q_raw = quiz_list[st.session_state.q_idx]
            ja_txt = str(q_raw[cols['ja']]).strip()
            kana_txt = q_raw.get(cols['kana']) if cols['kana'] else None
            struct = get_sentence_structure(ja_txt)
            tokens = [s['content'] for s in struct if s['type'] == 'word']
            shuf_list = list(tokens); random.seed(st.session_state.q_idx); random.shuffle(shuf_list)
            st.session_state.curr_q_data = {
                "ja": ja_txt, "cn": q_raw[cols['cn']], "ch": q_raw[cols['ch']],
                "kana": kana_txt, "struct": struct, "tokens": tokens, "shuf": shuf_list
            }

        q = st.session_state.curr_q_data
        st.info(f"第 {q['ch']} 章 | Q{st.session_state.q_idx + 1} | {q['cn']}")

        # 答題介面繪製...
        curr_ans_copy = list(st.session_state.ans)
        ans_html = '<div class="res-box">'
        for s in q['struct']:
            if s['type'] == 'punc': ans_html += f'<span>{s["content"]}</span>'
            else:
                val = curr_ans_copy.pop(0) if curr_ans_copy else ""
                ans_html += f'<div class="word-slot">{val}</div>'
        ans_html += '</div>'
        st.markdown(ans_html, unsafe_allow_html=True)

        st.caption("▼ 請點選單字按鈕")
        for idx, t in enumerate(q['shuf']):
            if idx not in st.session_state.used_history:
                if st.button(t, key=f"w_{idx}"):
                    st.session_state.ans.append(t); st.session_state.used_history.append(idx); st.rerun()

        st.write(" ")
        c_nav = st.columns(4)
        if c_nav[0].button("⬅ 退回"):
            if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        if c_nav[1].button("🔄 重填"): reset_state(); st.rerun()
        if c_nav[2].button("⏮ 上一題"): st.session_state.q_idx = max(0, st.session_state.q_idx-1); reset_state(); st.rerun()
        if c_nav[3].button("⏭ 下一題"): st.session_state.q_idx = min(len(quiz_list)-1, st.session_state.q_idx+1); reset_state(); st.rerun()

        if len(st.session_state.ans) == len(q['tokens']) and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(q['tokens']):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔！💡")

        if st.session_state.is_correct:
            st.success("正解！🎉")
            if q['kana']: st.write(f"讀音：{q['kana']}")
            st.markdown(get_audio_html(q['ja'], q['kana']), unsafe_allow_html=True)
            if st.button("👉 下一題", type="primary", use_container_width=True): 
                st.session_state.q_idx += 1; reset_state(); st.rerun()
    else:
        st.balloons(); st.success("範圍練習完成！")
        if st.button("🔄 重新開始此範圍練習"): st.session_state.q_idx = 0; reset_state(); st.rerun()
