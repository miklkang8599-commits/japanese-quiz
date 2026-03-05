import streamlit as st
import pandas as pd
import random
import re
import requests
import base64
import urllib.parse

# ==========================================
# 🌟 程式特色：手機極致排版 (Mobile Optimized)
# ==========================================
# 1. 【頂部零距離】：移除 Streamlit 預設大片空白，題目直接置頂，不被切掉。
# 2. 【橫向流動按鈕】：按鈕長度隨字變，橫向自動排隊換行，手機直立不拉長。
# 3. 【控制鍵緊湊化】：🔄 ⏮️ ⏭️ 橫向一列併排，節省垂直 200px 空間。
# 4. 【Base64 語音】：解決 iPhone 0:00 灰色條問題。
# ==========================================

st.set_page_config(page_title="🇯🇵 日文重組", layout="wide")

# 強力 CSS：徹底修正手機版佈局
st.markdown("""
    <style>
    /* 1. 移除 Streamlit 頂部所有空白 */
    .block-container { padding: 0.5rem 0.5rem !important; }
    [data-testid="stHeader"] { display: none; }
    div[data-testid="stVerticalBlock"] > div:first-child { margin-top: -30px; }

    /* 2. 題目與答題區緊湊化 */
    h3, h4 { font-size: 1.1rem !important; margin: 0 !important; padding: 2px 0 !important; }
    .res-box {
        font-size: 18px; padding: 8px; border-radius: 8px; 
        min-height: 45px; margin-bottom: 5px; line-height: 1.4;
        display: flex; flex-wrap: wrap; align-items: center; background-color: #f0f9ff;
    }
    .slot-empty { color: #cbd5e1; border-bottom: 2px solid #cbd5e1; margin: 0 3px; min-width: 20px; text-align: center; }
    .slot-filled { color: #1e40af; border-bottom: 2px solid #3b82f6; margin: 0 3px; font-weight: bold; }
    .punc-fixed { color: #64748b; font-weight: bold; font-size: 18px; padding: 0 2px; }

    /* 3. 【核心】強制功能鍵橫排 */
    [data-testid="column"] { flex: 1 1 0% !important; min-width: 0px !important; }
    div[data-testid="stHorizontalBlock"] { flex-direction: row !important; display: flex !important; gap: 4px !important; margin-bottom: 5px; }

    /* 4. 【核心】按鈕流動排列 (不一列一個) */
    .word-pool div.stButton { display: inline-block !important; margin-right: 4px !important; margin-bottom: 4px !important; }
    .word-pool div.stButton > button { width: auto !important; padding: 0 10px !important; height: 2.2em !important; font-size: 15px !important; }
    </style>
""", unsafe_allow_html=True)

# --- Base64 語音處理 ---
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

# --- 資料讀取與解析 ---
@st.cache_data(ttl=10)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA/export?format=csv&gid=1337973082"
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(subset=['日文原文', '中文意譯']), {'unit': '單元', 'ch': '章節', 'ja': '日文原文', 'cn': '中文意譯'}
    except: return None, None

def unified_parser(text):
    text = re.sub(r'[\s\u3000]', '', text)
    protected = ['ありがとうございます', 'ありがとうございました', '見つかりません', 'ありません', 'あります', 'どの出口', 'どのくらい']
    for i, w in enumerate(protected): text = text.replace(w, f"TOKEN{i}PROTECT")
    pattern = f"({'|'.join(re.escape(p) for p in (['から','まで','です','ます','は','が','を','に','へ','と','も','で','の','か'] + ['、','。','！','？']))})"
    raw_parts = re.split(pattern, text)
    final_tokens = []
    for p in [p for p in raw_parts if p]:
        is_p = False
        for i, w in enumerate(protected):
            if f"TOKEN{i}PROTECT" in p: final_tokens.append(w); is_p = True; break
        if not is_p: final_tokens.append(p)
    return final_tokens

# --- 狀態初始化 ---
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0
if 'ans' not in st.session_state: st.session_state.ans, st.session_state.used_history, st.session_state.is_correct = [], [], False

df, cols = load_data()

if df is not None:
    # 側邊欄
    u_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", u_list)
    u_df = df[df[cols['unit']] == sel_unit]
    c_list = sorted(u_df[cols['ch']].unique().tolist(), key=lambda x: [int(t) if t.isdigit() else t.lower() for t in re.split('([0-9]+)', x)])
    sel_ch = st.sidebar.selectbox("2. 起始章節", c_list)
    quiz_list = u_df[u_df[cols['ch']] >= sel_ch].head(5).to_dict('records')

    # 重置鎖
    ck = f"{sel_unit}-{sel_ch}"
    if 'ck' not in st.session_state or st.session_state.ck != ck:
        st.session_state.ck, st.session_state.q_idx = ck, 0
        st.session_state.ans, st.session_state.used_history, st.session_state.is_correct = [], [], False
        st.rerun()

    if st.sidebar.checkbox("📖 預習模式"):
        for item in quiz_list:
            st.info(f"**{item[cols['cn']]}**\n\n{item[cols['ja']]}")
            play_audio(item[cols['ja']])
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        all_t = unified_parser(str(q[cols['ja']]))
        words = [t for t in all_t if t not in ['、', '。', '！', '？']]
        
        if 'shuf_idx' not in st.session_state or len(st.session_state.shuf_idx) != len(words):
            st.session_state.shuf_idx = list(range(len(words))); random.shuffle(st.session_state.shuf_idx)

        # 頂部顯示：中文題目
        st.write(f"### Q{st.session_state.q_idx+1} | {q[cols['cn']]}")

        # 答題區
        u_ans = list(st.session_state.ans)
        html = '<div class="res-box">'
        for t in all_t:
            if t in ['、', '。', '！', '？']: html += f'<span class="punc-fixed">{t}</span>'
            else:
                if u_ans: html += f'<span class="slot-filled">{u_ans.pop(0)}</span>'
                else: html += f'<span class="slot-empty">口</span>'
        st.markdown(html + '</div>', unsafe_allow_html=True)

        # 功能鍵：水平橫排
        c1, c2, c3, c4 = st.columns(4)
        with c1: 
            if st.button("🔄"): st.session_state.ans, st.session_state.used_history, st.rerun()
        with c2:
            if st.button("⬅️"):
                if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        with c3:
            if st.button("⏮️") and st.session_state.q_idx > 0:
                st.session_state.q_idx -= 1; st.session_state.ans, st.session_state.used_history, st.session_state.shuf_idx = [], [], []; st.rerun()
        with c4:
            if st.button("⏭️") and st.session_state.q_idx < len(quiz_list)-1:
                st.session_state.q_idx += 1; st.session_state.ans, st.session_state.used_history, st.session_state.shuf_idx = [], [], []; st.rerun()

        # 按鈕池：流動佈局
        st.markdown('<div class="word-pool">', unsafe_allow_html=True)
        for ridx in st.session_state.shuf_idx:
            if ridx not in st.session_state.used_history:
                if st.button(words[ridx], key=f"b_{ridx}"):
                    st.session_state.ans.append(words[ridx]); st.session_state.used_history.append(ridx); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.ans and not st.session_state.is_correct:
            if st.button("🔍 檢查", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(words): st.session_state.is_correct = True; st.rerun()
                else: st.error("不對喔")
        if st.session_state.is_correct:
            st.success("正解！"); play_audio(q[cols['ja']], auto=True)
            if st.button("下一題 ➡️", type="primary", use_container_width=True):
                st.session_state.q_idx += 1; st.session_state.ans, st.session_state.used_history, st.session_state.shuf_idx, st.session_state.is_correct = [], [], [], False; st.rerun()
