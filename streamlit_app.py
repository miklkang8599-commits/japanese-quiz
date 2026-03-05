import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# ==========================================
# 🌟 程式特色與功能說明 (Program Features)
# ==========================================
# 1. 【流式按鈕佈局】：單字按鈕自動橫向排列，極大節省空間，減少手機捲動。
# 2. 【核心音訊修復】：採用 Base64 內嵌技術，確保 Chrome 與 iPhone 都能播放。
# 3. 【手機介面優化】：縮小答題區與按鈕高度，將控制鍵圖示化並橫向併排。
# 4. 【填空式重組】：答題區預顯標點與「口」，同步對齊下方按鈕數量。
# 5. 【預覽全展開】：預習模式清單化顯示，每題配備極簡語音播放器。
# ==========================================

st.set_page_config(page_title="🇯🇵 日文填空重組", layout="wide")

# 強力手機版 CSS 優化
st.markdown("""
    <style>
    /* 移除多餘邊距 */
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    
    /* 答題區：更緊湊的排版 */
    .res-box {
        font-size: 18px; color: #1e40af; background-color: #ffffff; 
        padding: 10px; border-radius: 10px; border: 1px solid #e2e8f0; 
        min-height: 60px; margin-bottom: 10px; line-height: 1.6;
        display: flex; flex-wrap: wrap; align-items: center;
    }
    .slot-empty { color: #cbd5e1; border-bottom: 2px solid #cbd5e1; margin: 0 3px; min-width: 25px; text-align: center; }
    .slot-filled { color: #1e40af; border-bottom: 2px solid #3b82f6; margin: 0 3px; padding: 0 2px; font-weight: bold; }
    .punc-fixed { color: #64748b; font-weight: bold; font-size: 20px; padding: 0 2px; }

    /* 控制按鈕列：極簡橫排 */
    .ctrl-row .stButton>button { 
        height: 2.5em; font-size: 14px !important; padding: 0px !important;
    }
    
    /* 【關鍵修正】單字按鈕：自動流動排版 */
    .word-btn-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: flex-start;
    }
    /* 覆寫 Streamlit 預設按鈕寬度 */
    div.stButton > button:not(.main-btn) {
        width: auto !important;
        min-width: 60px;
        padding: 0 15px !important;
        display: inline-block;
    }
    /* 檢查答案按鈕設為寬版 */
    .main-btn > div > button { width: 100% !important; height: 3em !important; font-weight: bold !important; }

    /* 隱藏側邊欄多餘資訊 */
    [data-testid="stSidebar"] { width: 220px !important; }
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
    # 側邊欄
    sel_unit = st.sidebar.selectbox("單元", sorted(df[cols['unit']].unique()))
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

        # 功能鍵
        st.markdown('<div class="ctrl-row">', unsafe_allow_html=True)
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
        st.markdown('</div>', unsafe_allow_html=True)

        # 單字按鈕：流式佈局
        st.write("---")
        # 使用自定義容器
        cols = st.columns(3) # 建立虛擬列，但我們會強制按鈕 inline
        for i, t in enumerate(st.session_state.shuf):
            if i not in st.session_state.used_history:
                # 均勻分散到各列中，實現流式排版效果
                with cols[i % 3]:
                    if st.button(t, key=f"btn_{i}"):
                        st.session_state.ans.append(t); st.session_state.used_history.append(i); st.rerun()

        st.write("")
        if st.session_state.ans and not st.session_state.is_correct:
            st.markdown('<div class="main-btn">', unsafe_allow_html=True)
            if st.button("🔍 檢查答案", type="primary"):
                if "".join(st.session_state.ans) == "".join(words):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("不對喔")
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.is_correct:
            st.success("正解！")
            play_audio(ja_raw, auto=True)
            st.markdown('<div class="main-btn">', unsafe_allow_html=True)
            if st.button("下一題 ➡️", type="primary"):
                st.session_state.q_idx += 1; reset_state(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.header("練習完成！")
        if st.button("🔄 重新開始", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
