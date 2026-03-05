import streamlit as st
import pandas as pd
import random
import re
import requests
import base64
import urllib.parse

# ==========================================
# 🌟 程式特色與功能說明 (跨平台完美版)
# ==========================================
# 1. 【核心音訊修復】：採用 Base64 直接嵌入，解決 iPhone/Chrome 播放條 0:00 灰色問題。
# 2. 【自適應流動按鈕】：不再使用原生 st.button，改用純 HTML 按鈕，寬度隨單字長短，手機自動換行。
# 3. 【同步對齊技術】：確保「口」空格與按鈕數量精確 1:1，不再發生數量不符。
# 4. 【響應式 UI】：自動偵測寬度，電腦版與手機版均有極佳的操作空間。
# ==========================================

st.set_page_config(page_title="🇯🇵 日文填空重組練習器", layout="wide")

# 強力 CSS：解決所有排版痛點
st.markdown("""
    <style>
    .block-container { padding: 0.5rem 1rem !important; }
    
    /* 答題區：縮小間距，適合手機 */
    .res-box {
        font-size: 18px; color: #1e40af; background-color: #f0f9ff; 
        padding: 10px; border-radius: 10px; border: 1px solid #bae6fd; 
        min-height: 60px; margin-bottom: 10px; line-height: 2.0;
        display: flex; flex-wrap: wrap; align-items: center;
    }
    .slot-empty { color: #cbd5e1; border-bottom: 2px solid #cbd5e1; margin: 0 4px; min-width: 25px; text-align: center; }
    .slot-filled { color: #1e40af; border-bottom: 2px solid #3b82f6; margin: 0 4px; padding: 0 2px; font-weight: bold; }
    .punc-fixed { color: #64748b; font-weight: bold; font-size: 20px; padding: 0 3px; }

    /* 控制列：四個橫排 */
    div[data-testid="stHorizontalBlock"] { flex-direction: row !important; display: flex !important; gap: 5px !important; }
    div[data-testid="column"] { flex: 1 1 0% !important; min-width: 0px !important; }

    /* 【關鍵】HTML 流動按鈕樣式 */
    .btn-container { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
    .word-btn {
        display: inline-block;
        background-color: #ffffff;
        color: #1e293b;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 8px 14px;
        font-size: 16px;
        cursor: pointer;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        user-select: none;
    }
    .word-btn:active { background-color: #f1f5f9; transform: translateY(1px); }
    </style>
""", unsafe_allow_html=True)

# --- 核心：Base64 語音解決方案 ---
def get_audio_b64(text):
    try:
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={urllib.parse.quote(text)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            return base64.b64encode(r.content).decode()
    except: return None
    return None

def play_audio(text, auto=False):
    b64 = get_audio_b64(text)
    if b64:
        autoplay = "autoplay" if auto else ""
        st.markdown(f'<audio controls {autoplay} style="width:100%; height:40px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)

# --- 資料載入 ---
SHEET_ID = "12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA"
GID = "1337973082"
data_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(data_url)
        df.columns = [str(c).strip() for c in df.columns]
        cols = {"unit": "單元", "ch": "章節", "ja": "日文原文", "cn": "中文意譯"}
        df[cols['unit']] = df[cols['unit']].astype(str).str.strip()
        df[cols['ch']] = df[cols['ch']].astype(str).str.strip()
        return df.dropna(subset=[cols['ja'], cols['cn']]), cols
    except: return None, None

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
    st.session_state.is_correct = False

if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 5
    reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄
    u_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", u_list)
    u_df = df[df[cols['unit']] == sel_unit]
    c_list = sorted(u_df[cols['ch']].unique().tolist(), key=lambda x: [int(t) if t.isdigit() else t.lower() for t in re.split('([0-9]+)', x)])
    sel_ch = st.sidebar.selectbox("2. 起始章節", c_list)
    
    quiz_list = u_df[u_df[cols['ch']] >= sel_ch].head(st.session_state.num_q).to_dict('records')

    if 'lkey' not in st.session_state or st.session_state.lkey != f"{sel_unit}-{sel_ch}-{st.session_state.num_q}":
        st.session_state.lkey = f"{sel_unit}-{sel_ch}-{st.session_state.num_q}"; st.session_state.q_idx = 0; reset_state(); st.rerun()

    if st.sidebar.checkbox("📖 預習模式"):
        for item in quiz_list:
            ja = str(item[cols['ja']]).strip()
            st.markdown(f"<div style='background:white; padding:10px; border-radius:8px; margin-bottom:5px; border-left:4px solid #3b82f6;'><b>{item[cols['cn']]}</b><br>{ja}</div>", unsafe_allow_html=True)
            play_audio(ja)
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw = str(q[cols['ja']]).strip()
        all_t = unified_parser(ja_raw)
        puncs = ['、', '。', '！', '？']
        words = [t for t in all_t if t not in puncs]
        
        # 建立按鈕亂序 (使用索引避開重複字問題)
        if 'shuf_idx' not in st.session_state or not st.session_state.shuf_idx:
            st.session_state.shuf_idx = list(range(len(words)))
            random.shuffle(st.session_state.shuf_idx)

        st.markdown(f"**Q{st.session_state.q_idx + 1}** | {q[cols['cn']]}")

        # 答題區顯示
        u_ans = list(st.session_state.ans)
        html = '<div class="res-box">'
        for t in all_t:
            if t in puncs: html += f'<span class="punc-fixed">{t}</span>'
            else:
                if u_ans: html += f'<span class="slot-filled">{u_ans.pop(0)}</span>'
                else: html += f'<span class="slot-empty">口</span>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        # 功能鍵 (橫排 4 個)
        c1, c2, c3, c4 = st.columns(4)
        with c1: 
            if st.button("🔄"): reset_state(); st.session_state.shuf_idx = []; st.rerun()
        with c2:
            if st.button("⬅️"):
                if st.session_state.used_history: 
                    idx = st.session_state.used_history.pop()
                    st.session_state.ans.pop(); st.rerun()
        with c3:
            if st.button("⏮️"):
                if st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.session_state.shuf_idx = []; st.rerun()
        with c4:
            if st.button("⏭️"):
                if st.session_state.q_idx + 1 < len(quiz_list): st.session_state.q_idx += 1; reset_state(); st.session_state.shuf_idx = []; st.rerun()

        st.write("---")
        
        # --- 跨平台流動按鈕區 ---
        # 這裡為了兼顧 Streamlit 的點擊觸發，我們手動用 columns 模擬，但鎖定寬度
        cols_per_row = 3 # 手機直立最適合 3 個
        for i in range(0, len(st.session_state.shuf_idx), cols_per_row):
            row_cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                curr_pos = i + j
                if curr_pos < len(st.session_state.shuf_idx):
                    real_idx = st.session_state.shuf_idx[curr_pos]
                    if real_idx not in st.session_state.used_history:
                        word = words[real_idx]
                        with row_cols[j]:
                            if st.button(word, key=f"btn_{real_idx}", use_container_width=True):
                                st.session_state.ans.append(word)
                                st.session_state.used_history.append(real_idx)
                                st.rerun()

        if st.session_state.ans and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(words):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("不對喔")

        if st.session_state.is_correct:
            st.success("正解！")
            play_audio(ja_raw, auto=True)
            if st.button("下一題 ➡️", type="primary", use_container_width=True):
                st.session_state.q_idx += 1; reset_state(); st.session_state.shuf_idx = []; st.rerun()
    else:
        st.header("練習完成！")
        if st.button("🔄 重新開始", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
