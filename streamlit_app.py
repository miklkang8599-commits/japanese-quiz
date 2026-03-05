import streamlit as st
import pandas as pd
import random
import re
import requests
import base64
import urllib.parse

# ==========================================
# 🌟 程式特色：跨平台智慧排版 (Smart Responsive)
# ==========================================
# 1. 【自動辨識裝置】：電腦版維持標準比例，手機版自動壓縮邊距，避免切掉頂部。
# 2. 【功能鍵橫流】：手機端功能鍵強制橫排，騰出空間給下方的單字按鈕。
# 3. 【題目置頂修復】：移除手機版多餘的空白，確保中文題目一眼就能看到。
# 4. 【Base64 強效音訊】：修復 0:00 灰色條，Chrome 與 iPhone 都能直接播。
# ==========================================

st.set_page_config(page_title="🇯🇵 日文重組練習器", layout="wide")

# 強力 CSS：區分電腦與手機排版
st.markdown("""
    <style>
    /* 1. 電腦版基礎設定 */
    .block-container { padding: 1rem 2rem !important; }
    
    /* 2. 手機版專屬修正 (螢幕寬度小於 768px 時觸發) */
    @media (max-width: 768px) {
        .block-container { padding: 0.5rem 0.5rem !important; }
        .stMarkdown h3, .stMarkdown h4 { font-size: 1.1rem !important; margin-bottom: 5px !important; }
        .res-box { padding: 8px !important; min-height: 50px !important; font-size: 18px !important; }
        /* 強制功能鍵在手機也要橫排 */
        div[data-testid="stHorizontalBlock"] { flex-direction: row !important; display: flex !important; gap: 2px !important; }
    }

    /* 答題區 */
    .res-box {
        font-size: 20px; color: #1e40af; background-color: #f0f9ff; 
        padding: 15px; border-radius: 10px; border: 1px solid #bae6fd; 
        min-height: 60px; margin-bottom: 10px; line-height: 1.8;
        display: flex; flex-wrap: wrap; align-items: center;
    }
    .slot-empty { color: #cbd5e1; border-bottom: 2px solid #cbd5e1; margin: 0 4px; min-width: 25px; text-align: center; }
    .slot-filled { color: #1e40af; border-bottom: 2px solid #3b82f6; margin: 0 4px; padding: 0 2px; font-weight: bold; }
    .punc-fixed { color: #64748b; font-weight: bold; font-size: 22px; padding: 0 3px; }

    /* 按鈕流動區塊 */
    .word-pool-container div.stButton {
        display: inline-block !important;
        width: auto !important;
        margin-right: 4px !important;
        margin-bottom: 4px !important;
    }
    div[data-testid="column"] { flex: 1 1 0% !important; min-width: 0px !important; }
    </style>
""", unsafe_allow_html=True)

# --- Base64 語音 ---
def get_audio_b64(text):
    try:
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={urllib.parse.quote(text)}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            return base64.b64encode(r.content).decode()
    except: return None
    return None

def play_audio(text, auto=False):
    b64 = get_audio_b64(text)
    if b64:
        autoplay = "autoplay" if auto else ""
        st.markdown(f'<audio controls {autoplay} style="width:100%; height:35px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)

# --- 資料載入 ---
SHEET_ID = "12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA"
GID = "1337973082"
data_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=10)
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
    protected = ['ありがとうございます', 'ありがとうございました', '見つかりません', 'ありません', 'あります', 'どの出口', 'どのくらい']
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

# --- 初始化 ---
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0
if 'num_q' not in st.session_state: st.session_state.num_q = 5
if 'ans' not in st.session_state: reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄
    u_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", u_list)
    u_df = df[df[cols['unit']] == sel_unit]
    c_list = sorted(u_df[cols['ch']].unique().tolist(), key=lambda x: [int(t) if t.isdigit() else t.lower() for t in re.split('([0-9]+)', x)])
    sel_ch = st.sidebar.selectbox("2. 起始章節", c_list)
    
    filtered_df = u_df[u_df[cols['ch']] >= sel_ch]
    st.session_state.num_q = st.sidebar.slider("3. 練習題數", 1, min(len(filtered_df), 50), st.session_state.num_q)
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    current_key = f"{sel_unit}-{sel_ch}-{st.session_state.num_q}"
    if 'sync_key' not in st.session_state or st.session_state.sync_key != current_key:
        st.session_state.sync_key = current_key
        st.session_state.q_idx = 0; reset_state(); st.rerun()

    # 主畫面
    if st.sidebar.checkbox("📖 預習模式"):
        for item in quiz_list:
            ja = str(item[cols['ja']]).strip()
            st.info(f"**{item[cols['cn']]}**\n\n{ja}")
            play_audio(ja)
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw = str(q[cols['ja']]).strip()
        all_t = unified_parser(ja_raw)
        words = [t for t in all_t if t not in ['、', '。', '！', '？']]
        
        if 'shuf_idx' not in st.session_state or len(st.session_state.shuf_idx) != len(words):
            st.session_state.shuf_idx = list(range(len(words)))
            random.shuffle(st.session_state.shuf_idx)

        # 題目區
        st.write(f"### Q{st.session_state.q_idx + 1} / {len(quiz_list)}")
        st.write(f"#### 💡 {q[cols['cn']]}")

        # 答題區
        u_ans = list(st.session_state.ans)
        html = '<div class="res-box">'
        for t in all_t:
            if t in ['、', '。', '！', '？']: html += f'<span class="punc-fixed">{t}</span>'
            else:
                if u_ans: html += f'<span class="slot-filled">{u_ans.pop(0)}</span>'
                else: html += f'<span class="slot-empty">口</span>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        # 功能鍵區
        c1, c2, c3, c4 = st.columns(4)
        with c1: 
            if st.button("🔄"): reset_state(); st.session_state.shuf_idx = []; st.rerun()
        with c2:
            if st.button("⬅️"):
                if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        with c3:
            if st.button("⏮️"):
                if st.session_state.q_idx > 0: st.session_state.q_idx -= 1; st.session_state.shuf_idx = []; reset_state(); st.rerun()
        with c4:
            if st.button("⏭️"):
                if st.session_state.q_idx + 1 < len(quiz_list): st.session_state.q_idx += 1; st.session_state.shuf_idx = []; reset_state(); st.rerun()

        st.write("---")
        
        # 單字按鈕區
        st.markdown('<div class="word-pool-container">', unsafe_allow_html=True)
        for real_idx in st.session_state.shuf_idx:
            if real_idx not in st.session_state.used_history:
                if st.button(words[real_idx], key=f"btn_{real_idx}"):
                    st.session_state.ans.append(words[real_idx])
                    st.session_state.used_history.append(real_idx)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.ans and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(words):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔")

        if st.session_state.is_correct:
            st.success("正解！")
            play_audio(ja_raw, auto=True)
            if st.button("下一題 ➡️", type="primary", use_container_width=True):
                st.session_state.q_idx += 1; st.session_state.shuf_idx = []; reset_state(); st.rerun()
    else:
        st.header("練習完成！")
        if st.button("🔄 重新開始", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
