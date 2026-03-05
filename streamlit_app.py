import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# ==========================================
# 🌟 程式特色與功能說明 (Program Features)
# ==========================================
# 1. 【核心音訊修復】：採用 Base64 內嵌技術，確保 Chrome 與 iPhone 都能播放。
# 2. 【手機直立流佈局】：使用 HTML/CSS 直接渲染，按鈕會自動橫向流動並換行，極省空間。
# 3. 【填空式重組】：答題區預顯標點與「口」，同步對齊下方按鈕數量。
# 4. 【智慧排序與保護】：支援 1, 2, 10 智慧排序，並保護常用長詞（如：ありがとうございます）。
# ==========================================

st.set_page_config(page_title="🇯🇵 日文填空重組", layout="wide")

# 強力手機版 CSS
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    
    /* 答題區 */
    .res-box {
        font-size: 18px; color: #1e40af; background-color: #ffffff; 
        padding: 10px; border-radius: 10px; border: 1px solid #e2e8f0; 
        min-height: 50px; margin-bottom: 10px; line-height: 1.6;
        display: flex; flex-wrap: wrap; align-items: center;
    }
    .slot-empty { color: #cbd5e1; border-bottom: 2px solid #cbd5e1; margin: 0 3px; min-width: 25px; text-align: center; }
    .slot-filled { color: #1e40af; border-bottom: 2px solid #3b82f6; margin: 0 3px; padding: 0 2px; font-weight: bold; }
    .punc-fixed { color: #64748b; font-weight: bold; font-size: 20px; padding: 0 2px; }

    /* 流動按鈕樣式 */
    .word-btn {
        display: inline-block;
        background-color: #ffffff;
        color: #1e293b;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 6px 12px;
        margin: 4px;
        font-size: 16px;
        cursor: pointer;
        text-decoration: none;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# --- 核心：Base64 音訊處理 ---
def get_audio_b64(text):
    try:
        tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(tts_url, headers=headers, timeout=5)
        if r.status_code == 200:
            return base64.b64encode(r.content).decode()
    except: return None
    return None

def play_audio(text, auto=False):
    b64_str = get_audio_b64(text)
    if b64_str:
        autoplay = "autoplay" if auto else ""
        html_code = f'<audio controls {autoplay} style="width:100%; height:30px;"><source src="data:audio/mp3;base64,{b64_str}" type="audio/mp3"></audio>'
        st.components.v1.html(html_code, height=40)

# --- 資料讀取 ---
SHEET_ID = "12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA"
GID = "1337973082"
url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        cols = {"unit": "單元", "ch": "章節", "ja": "日文原文", "cn": "中文意譯"}
        df[cols['unit']] = df[cols['unit']].astype(str).str.strip()
        df[cols['ch']] = df[cols['ch']].astype(str).str.strip()
        return df.dropna(subset=[cols['ja'], cols['cn']]), cols
    except: return None, None

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def unified_parser(text):
    text = re.sub(r'[\s\u3000]', '', text)
    protected = ['ありがとうございます', 'ありがとうございました', 'すみません', 'どのくらい', 'どのぐらい', 'どの出口', 'ございます']
    for i, w in enumerate(protected): text = text.replace(w, f"TOKEN{i}PROTECT")
    particles = ['から', 'まで', 'です', 'ます', 'は', 'が', 'を', 'に', 'へ', 'と', 'も', 'で', 'の', 'か']
    punctuations = ['、', '。', '！', '？']
    pattern = f"({'|'.join(re.escape(p) for p in (particles + punctuations))})"
    raw_parts = re.split(pattern, text)
    tokens = [p for p in raw_parts if p]
    final_tokens = []
    for p in tokens:
        is_p = False
        for i, w in enumerate(protected):
            if f"TOKEN{i}PROTECT" in p: final_tokens.append(w); is_p = True; break
        if not is_p: final_tokens.append(p)
    return final_tokens

def reset_state():
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 5
    reset_state()

df, cols = load_data()

if df is not None:
    u_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("單元", u_list)
    u_df = df[df[cols['unit']] == sel_unit]
    c_list = sorted(u_df[cols['ch']].unique().tolist(), key=natural_sort_key)
    sel_start_ch = st.sidebar.selectbox("章節", c_list)
    
    start_idx = c_list.index(sel_start_ch)
    filtered_df = u_df[u_df[cols['ch']].isin(c_list[start_idx:])]
    max_q = len(filtered_df)

    st.sidebar.write(f"題數: {st.session_state.num_q}")
    st.session_state.num_q = st.sidebar.slider("調整", 1, max_q, st.session_state.num_q)
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if 'lkey' not in st.session_state or st.session_state.lkey != f"{sel_unit}-{sel_start_ch}-{st.session_state.num_q}":
        st.session_state.lkey = f"{sel_unit}-{sel_start_ch}-{st.session_state.num_q}"
        st.session_state.q_idx = 0; reset_state(); st.rerun()

    # 主畫面
    if st.sidebar.checkbox("📖 預習模式"):
        for item in quiz_list:
            ja = str(item[cols['ja']]).strip()
            st.markdown(f"<div style='background:white; padding:8px; border-radius:8px; margin-bottom:5px; border-left:3px solid #3b82f6; font-size:14px;'><b>{item[cols['cn']]}</b><br>{ja}</div>", unsafe_allow_html=True)
            play_audio(ja)
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw = str(q[cols['ja']]).strip()
        all_t = unified_parser(ja_raw)
        puncs = ['、', '。', '！', '？']
        words = [t for t in all_t if t not in puncs]
        
        if not st.session_state.shuf:
            st.session_state.shuf = list(words); random.shuffle(st.session_state.shuf)

        st.markdown(f"**Q{st.session_state.q_idx + 1}** | {q[cols['cn']]}")

        # 答題區
        u_ans = list(st.session_state.ans)
        html = '<div class="res-box">'
        for t in all_t:
            if t in puncs: html += f'<span class="punc-fixed">{t}</span>'
            else:
                if u_ans: html += f'<span class="slot-filled">{u_ans.pop(0)}</span>'
                else: html += f'<span class="slot-empty">口</span>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        # 功能鍵 (使用兩列，節省直向空間)
        c1, c2, c3, c4 = st.columns(4)
        with c1: 
            if st.button("🔄"): reset_state(); st.rerun()
        with c2:
            if st.button("⬅️"):
                if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        with c3:
            if st.button("⏮️"):
                if st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        with c4:
            if st.button("⏭️"):
                if st.session_state.q_idx + 1 < len(quiz_list): st.session_state.q_idx += 1; reset_state(); st.rerun()

        st.write("---")
        
        # --- 核心優化：流動式按鈕渲染 ---
        # 使用 Streamlit 原生 button 但放置在「列」中會導致佔滿寬度。
        # 我們改用「一列多個按鈕」的排法來模擬流動效果。
        
        # 建立動態列數 (每行最多 3 個)
        rows = [st.session_state.shuf[i:i+3] for i in range(0, len(st.session_state.shuf), 3)]
        orig_indices = [list(range(i, i+3)) for i in range(0, len(st.session_state.shuf), 3)]

        for r_idx, row_words in enumerate(rows):
            cols = st.columns(len(row_words))
            for i, word in enumerate(row_words):
                real_idx = orig_indices[r_idx][i]
                if real_idx not in st.session_state.used_history:
                    with cols[i]:
                        if st.button(word, key=f"btn_{real_idx}", use_container_width=True):
                            st.session_state.ans.append(word)
                            st.session_state.used_history.append(real_idx)
                            st.rerun()

        st.write("")
        if st.session_state.ans and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(words):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("不對喔")

        if st.session_state.is_correct:
            st.success("正解！")
            play_audio(ja_raw, auto=True)
            if st.button("下一題 ➡️", type="primary", use_container_width=True):
                st.session_state.q_idx += 1; reset_state(); st.rerun()
    else:
        st.header("練習完成！")
        if st.button("🔄 重新開始", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
