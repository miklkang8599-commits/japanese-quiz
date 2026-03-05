import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# ==========================================
# 🌟 程式特色與功能說明 (Program Features)
# ==========================================
# 1. 【核心語音修復】：採用 Base64 二進位嵌入，徹底解決 iPhone 播放條變灰問題。
# 2. 【自適應流動按鈕】：按鈕寬度隨單字長短變化，且在手機直立時自動橫向換行。
# 3. 【填空式重組介面】：答題區預顯標點與「口」，同步對齊下方按鈕數量。
# 4. 【智慧排序與保護】：支援智慧章節排序，並保護常用長詞（如：ありがとうございます）。
# ==========================================

st.set_page_config(page_title="🇯🇵 日文填空重組練習器", layout="wide")

# 強力 CSS：修正按鈕排版與語音樣式
st.markdown("""
    <style>
    .block-container { padding: 0.5rem 0.8rem !important; }
    
    /* 答題區 */
    .res-box {
        font-size: 18px; color: #1e40af; background-color: #f0f9ff; 
        padding: 10px; border-radius: 8px; border: 1px solid #bae6fd; 
        min-height: 50px; margin-bottom: 8px; line-height: 1.6;
        display: flex; flex-wrap: wrap; align-items: center;
    }
    .slot-empty { color: #cbd5e1; border-bottom: 2px solid #cbd5e1; margin: 0 3px; min-width: 25px; text-align: center; }
    .slot-filled { color: #1e40af; border-bottom: 2px solid #3b82f6; margin: 0 4px; padding: 0 2px; font-weight: bold; }
    .punc-fixed { color: #64748b; font-weight: bold; font-size: 20px; padding: 0 2px; }

    /* 【關鍵修正】強制讓按鈕橫向排隊，不再一列一個 */
    div[data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0px !important;
    }
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 5px !important;
    }
    div.stButton > button {
        width: auto !important;
        min-width: 50px !important;
        padding: 0 10px !important;
        height: 2.2em !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 核心音訊修復：將語音轉為 Base64 字串 ---
def get_audio_b64(text):
    try:
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            b64 = base64.b64encode(r.content).decode()
            return f"data:audio/mpeg;base64,{b64}"
    except:
        return None
    return None

def play_audio(text, auto=False):
    audio_data = get_audio_b64(text)
    if audio_data:
        autoplay = "autoplay" if auto else ""
        # 使用 HTML5 播放器嵌入 Base64 數據
        st.markdown(f'<audio controls {autoplay} src="{audio_data}" style="width:100%; height:40px;"></audio>', unsafe_allow_html=True)
    else:
        st.error("語音載入失敗")

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
    protected = ['ありがとうございます', 'ありがとうございました', 'すみません', 'どのくらい', 'どのぐらい', 'どの出口', '見つかりません']
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
    u_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("單元", u_list)
    u_df = df[df[cols['unit']] == sel_unit]
    c_list = sorted(u_df[cols['ch']].unique().tolist(), key=natural_sort_key)
    sel_ch = st.sidebar.selectbox("章節", c_list)
    quiz_list = u_df[u_df[cols['ch']] >= sel_ch].head(st.session_state.num_q).to_dict('records')

    if st.sidebar.checkbox("📖 預習模式"):
        for item in quiz_list:
            ja = str(item[cols['ja']]).strip()
            st.markdown(f"<div style='background:white; padding:8px; border-radius:5px; margin-bottom:5px; border-left:3px solid #3b82f6;'><b>{item[cols['ch']]} {item[cols['cn']]}</b><br>{ja}</div>", unsafe_allow_html=True)
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
        
        # --- 核心：按鈕橫向排列邏輯 ---
        # 這裡用 3 欄式循環排列，但靠 CSS 強制手機版不換行
        n_cols = 3 
        for i in range(0, len(st.session_state.shuf), n_cols):
            row_cols = st.columns(n_cols)
            for j in range(n_cols):
                idx = i + j
                if idx < len(st.session_state.shuf) and idx not in st.session_state.used_history:
                    word = st.session_state.shuf[idx]
                    with row_cols[j]:
                        if st.button(word, key=f"btn_{idx}", use_container_width=True):
                            st.session_state.ans.append(word)
                            st.session_state.used_history.append(idx)
                            st.rerun()

        if st.session_state.ans and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(words):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔")

        if st.session_state.is_correct:
            st.success("正解！")
            play_audio(ja_raw, auto=True)
            if st.button("下一題 ➡️", type="primary", use_container_width=True):
                st.session_state.q_idx += 1; reset_state(); st.rerun()
    else:
        st.header("練習完成！")
        if st.button("🔄 重新開始", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
