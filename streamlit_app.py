import streamlit as st
import pandas as pd
import random
import re
import requests
import base64
from io import BytesIO

# ==========================================
# 🌟 程式特色與功能說明 (Program Features)
# ==========================================
# 1. 【核心音訊修復】：採用 Base64 內嵌技術，確保 Chrome 與 iPhone 都能播放。
# 2. 【填空式重組介面】：答題區預顯標點符號與「口」空格，直觀掌握句構。
# 3. 【同步對齊技術】：確保「口」空格數量與下方按鈕數量絕對一致。
# 4. 【長詞保護機制】：保護「ありがとうございます」等常用語不被切碎。
# 5. 【直讀式預習模式】：內容全展開，每題配備獨立音訊播放器。
# 6. 【智慧排序與題數】：支援 1, 2, 10 排序，預設 5 題練習。
# ==========================================

st.set_page_config(page_title="🇯🇵 日文填空重組練習器", layout="wide")

# CSS 優化
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.2em; font-size: 18px !important; margin-bottom: 8px; }
    .res-box {
        font-size: 26px; color: #1e40af; background-color: #eff6ff; 
        padding: 20px; border-radius: 12px; border: 2px dashed #60a5fa; 
        min-height: 110px; margin-bottom: 15px; line-height: 2.2; letter-spacing: 2px;
        display: flex; flex-wrap: wrap; align-items: center;
    }
    .slot-empty { color: #bfdbfe; border-bottom: 2px solid #bfdbfe; margin: 0 8px; min-width: 45px; text-align: center; font-weight: bold; }
    .slot-filled { color: #1e40af; border-bottom: 2px solid #60a5fa; margin: 0 8px; padding: 0 4px; }
    .punc-fixed { color: #1e3a8a; font-weight: bold; font-size: 32px; padding: 0 8px; }
    [data-testid="stSidebar"] .stButton>button { height: 2.5em; font-size: 16px !important; }
    .preview-card { background: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 核心：Base64 音訊處理函數 ---
def get_audio_b64(text):
    """
    將 Google TTS 音訊下載並轉換為 Base64，確保跨平台相容性
    """
    try:
        tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(tts_url, headers=headers)
        if r.status_code == 200:
            return base64.b64encode(r.content).decode()
    except:
        return None
    return None

def play_audio(text, auto=False):
    """生成 HTML5 內嵌播放器"""
    b64_str = get_audio_b64(text)
    if b64_str:
        autoplay = "autoplay" if auto else ""
        html_code = f"""
            <audio controls {autoplay} style="width:100%; height:40px;">
                <source src="data:audio/mp3;base64,{b64_str}" type="audio/mp3">
            </audio>
        """
        st.components.v1.html(html_code, height=50)
    else:
        st.warning("語音加載失敗")

# --- 資料讀取與處理 ---
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
    for i, w in enumerate(protected):
        text = text.replace(w, f"TOKEN{i}PROTECT")
    particles = ['から', 'まで', 'です', 'ます', 'は', 'が', 'を', 'に', 'へ', 'と', 'も', 'で', 'の', 'か']
    punctuations = ['、', '。', '！', '？']
    pattern = f"({'|'.join(re.escape(p) for p in (particles + punctuations))})"
    raw_parts = re.split(pattern, text)
    tokens = []
    for p in raw_parts:
        if not p: continue
        is_p = False
        for i, w in enumerate(protected):
            if f"TOKEN{i}PROTECT" in p:
                tokens.append(w); is_p = True; break
        if not is_p: tokens.append(p)
    return tokens

def reset_state():
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

# --- 初始化 ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx = 0
    st.session_state.num_q = 5
    reset_state()

df, cols = load_data()

if df is not None:
    st.sidebar.header("⚙️ 練習設定")
    u_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", u_list)
    u_df = df[df[cols['unit']] == sel_unit]
    c_list = sorted(u_df[cols['ch']].unique().tolist(), key=natural_sort_key)
    sel_start_ch = st.sidebar.selectbox("2. 起始章節", c_list)
    
    start_idx = c_list.index(sel_start_ch)
    filtered_df = u_df[u_df[cols['ch']].isin(c_list[start_idx:])]
    max_q = len(filtered_df)

    st.sidebar.write(f"3. 練習題數: {st.session_state.num_q}")
    st.session_state.num_q = st.sidebar.slider("調整題數", 1, max_q, st.session_state.num_q)
    c_m, c_p = st.sidebar.columns(2)
    with c_m:
        if st.button("➖ 少一題"):
            if st.session_state.num_q > 1: st.session_state.num_q -= 1; st.rerun()
    with c_p:
        if st.button("➕ 多一題"):
            if st.session_state.num_q < max_q: st.session_state.num_q += 1; st.rerun()

    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if 'lkey' not in st.session_state or st.session_state.lkey != f"{sel_unit}-{sel_start_ch}-{st.session_state.num_q}":
        st.session_state.lkey = f"{sel_unit}-{sel_start_ch}-{st.session_state.num_q}"; st.session_state.q_idx = 0; reset_state(); st.rerun()

    if st.sidebar.checkbox("📖 預習模式"):
        st.header("📖 課文預習")
        for item in quiz_list:
            ja_text = str(item[cols['ja']]).strip()
            st.markdown(f"""
                <div class="preview-card">
                    <div style='font-size:12px; color:#94a3b8;'>章節：{item[cols['ch']]}</div>
                    <div style='font-size:16px; color:#475569;'>{item[cols['cn']]}</div>
                    <div style='font-size:20px; color:#1d4ed8; font-weight:bold;'>{ja_text}</div>
                </div>
            """, unsafe_allow_html=True)
            play_audio(ja_text)
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw = str(q[cols['ja']]).strip()
        all_t = unified_parser(ja_raw)
        puncs = ['、', '。', '！', '？']
        words = [t for t in all_t if t not in puncs]
        
        if not st.session_state.shuf:
            st.session_state.shuf = list(words); random.shuffle(st.session_state.shuf)

        st.subheader(f"Q {st.session_state.q_idx + 1} / {len(quiz_list)}")
        st.info(f"💡 {q[cols['cn']]}")

        # 答題區顯示
        u_ans = list(st.session_state.ans)
        html = '<div class="res-box">'
        for t in all_t:
            if t in puncs: html += f'<span class="punc-fixed">{t}</span>'
            else:
                if u_ans:
                    val = u_ans.pop(0)
                    html += f'<span class="slot-filled">{val}</span>'
                else: html += f'<span class="slot-empty">口</span>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        ctrl = st.columns(4)
        with ctrl[0]:
            if st.button("🔄重填"): reset_state(); st.rerun()
        with ctrl[1]:
            if st.button("⬅️退回"):
                if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        with ctrl[2]:
            if st.button("⏮️上題"):
                if st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        with ctrl[3]:
            if st.button("⏭️下題"):
                if st.session_state.q_idx + 1 < len(quiz_list): st.session_state.q_idx += 1; reset_state(); st.rerun()

        st.write("---")
        b_cols = st.columns(2) 
        for i, t in enumerate(st.session_state.shuf):
            if i not in st.session_state.used_history:
                with b_cols[i % 2]:
                    if st.button(t, key=f"btn_{i}"):
                        st.session_state.ans.append(t); st.session_state.used_history.append(i); st.rerun()

        if st.session_state.ans and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(words):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔！")

        if st.session_state.is_correct:
            st.success("🎊 正解！")
            st.markdown(f"### {ja_raw}")
            play_audio(ja_raw, auto=True)
            if st.button("下一題 ➡️", type="primary", use_container_width=True):
                st.session_state.q_idx += 1; reset_state(); st.rerun()
    else:
        st.header("🎊 練習完成！")
        if st.button("🔄 重新開始", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
