import streamlit as st
import pandas as pd
import random
import re
import requests
import base64
import urllib.parse

# ==========================================
# 🌟 程式特色與功能說明 (完全相容版)
# ==========================================
# 1. 【排版修復】：電腦版題目回歸，手機版按鈕自動流動換行，不再需要長距離滑動。
# 2. 【核心音訊】：Base64 內嵌音訊，確保 Chrome 與 iPhone 播放器不再變灰。
# 3. 【分詞保護】：保護長語塊（如：見つかりません），確保按鈕邏輯正確。
# 4. 【同步確保】：切換章節立刻重置狀態，電腦手機同步不卡關。
# ==========================================

st.set_page_config(page_title="🇯🇵 日文重組練習器", layout="wide")

# 精準 CSS：區分「題目區」與「按鈕流動區」
st.markdown("""
    <style>
    .block-container { padding: 1rem !important; }
    
    /* 答題區外框 */
    .res-box {
        font-size: 20px; color: #1e40af; background-color: #f0f9ff; 
        padding: 15px; border-radius: 10px; border: 1px solid #bae6fd; 
        min-height: 60px; margin-bottom: 15px; line-height: 1.8;
        display: flex; flex-wrap: wrap; align-items: center;
    }
    .slot-empty { color: #cbd5e1; border-bottom: 2px solid #cbd5e1; margin: 0 5px; min-width: 30px; text-align: center; }
    .slot-filled { color: #1e40af; border-bottom: 2px solid #3b82f6; margin: 0 5px; padding: 0 2px; font-weight: bold; }
    .punc-fixed { color: #64748b; font-weight: bold; font-size: 24px; padding: 0 4px; }

    /* 功能鍵橫排 (🔄等) */
    [data-testid="stHorizontalBlock"] { flex-direction: row !important; display: flex !important; gap: 8px !important; }
    [data-testid="column"] { flex: 1 1 0% !important; min-width: 0px !important; }

    /* 【關鍵】單字按鈕流動區塊：只針對這個區域進行 CSS 覆寫 */
    .word-pool-container div.stButton {
        display: inline-block !important;
        width: auto !important;
        margin-right: 5px !important;
        margin-bottom: 5px !important;
    }
    
    .word-pool-container div.stButton > button {
        width: auto !important;
        padding: 0 15px !important;
        height: 2.6em !important;
        font-size: 16px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Base64 音訊 ---
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
        st.markdown(f'<audio controls {autoplay} style="width:100%; height:40px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)

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

    # 重置鎖
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

        # 1. 顯示題目 (使用標準 st.write，確保電腦版不消失)
        st.write(f"### Q{st.session_state.q_idx + 1} / {len(quiz_list)}")
        st.write(f"#### 💡 {q[cols['cn']]}")

        # 2. 答題區
        u_ans = list(st.session_state.ans)
        html = '<div class="res-box">'
        for t in all_t:
            if t in ['、', '。', '！', '？']: html += f'<span class="punc-fixed">{t}</span>'
            else:
                if u_ans: html += f'<span class="slot-filled">{u_ans.pop(0)}</span>'
                else: html += f'<span class="slot-empty">口</span>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        # 3. 功能鍵
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
        
        # 4. 單字按鈕區 (使用專屬流動容器)
        st.write("點選單字按鈕：")
        st.markdown('<div class="word-pool-container">', unsafe_allow_html=True)
        # 用一個單獨的 container 包住按鈕，透過 CSS 只對這裡面的 div 生效
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
                else: st.error("不對喔")

        if st.session_state.is_correct:
            st.success("正解！")
            play_audio(ja_raw, auto=True)
            if st.button("下一題 ➡️", type="primary", use_container_width=True):
                st.session_state.q_idx += 1; st.session_state.shuf_idx = []; reset_state(); st.rerun()
    else:
        st.header("練習完成！")
        if st.button("🔄 重新開始", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
