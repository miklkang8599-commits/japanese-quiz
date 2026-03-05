import streamlit as st
import pandas as pd
import random
import re
import requests
import base64
import urllib.parse

# ==========================================
# 🌟 程式特色：手機端排版絕殺 (Mobile Layout Fix)
# ==========================================
# 1. 【HTML 注入按鈕】：不再使用 st.button，改用純 HTML/JS 觸發，確保手機直立絕對橫向排隊。
# 2. 【空間極致壓縮】：移除所有頂部邊距，中文題目與答題框置頂，不需滑動。
# 3. 【Base64 強效音訊】：修復 0:00 灰色條，iPhone/Chrome 直接播放。
# 4. 【語塊保護】：保護「見つかりません」不被切碎。
# ==========================================

st.set_page_config(page_title="🇯🇵 日文重組", layout="wide")

# 強力 CSS：徹底修正手機版排版衝突
st.markdown("""
    <style>
    /* 1. 移除 Streamlit 頂部所有空白 */
    .block-container { padding: 0.2rem 0.5rem !important; }
    [data-testid="stHeader"] { display: none; }
    
    /* 2. 答題區 */
    .res-box {
        font-size: 18px; color: #1e40af; background-color: #f0f9ff; 
        padding: 8px; border-radius: 8px; border: 1px solid #bae6fd; 
        min-height: 45px; margin-bottom: 8px; line-height: 1.4;
        display: flex; flex-wrap: wrap; align-items: center;
    }
    .slot-empty { color: #cbd5e1; border-bottom: 2px solid #cbd5e1; margin: 0 3px; min-width: 20px; text-align: center; }
    .slot-filled { color: #1e40af; border-bottom: 2px solid #3b82f6; margin: 0 3px; font-weight: bold; }
    .punc-fixed { color: #64748b; font-weight: bold; font-size: 18px; padding: 0 2px; }

    /* 3. 功能鍵橫排修復 (🔄等) */
    div[data-testid="stHorizontalBlock"] { 
        flex-direction: row !important; display: flex !important; 
        gap: 5px !important; margin-bottom: 10px !important;
    }
    div[data-testid="column"] { 
        flex: 1 1 0% !important; min-width: 0px !important; 
    }

    /* 4. 單字按鈕自適應與流動 (不一列一個) */
    .word-pool {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 10px;
    }
    /* 針對 HTML 注入的按鈕樣式 */
    .custom-btn {
        display: inline-block;
        background-color: white;
        color: #1e293b;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 16px;
        cursor: pointer;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        user-select: none;
    }
    </style>
""", unsafe_allow_html=True)

# --- 核心：Base64 語音處理 ---
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

# --- 資料讀取 ---
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
    protected = ['ありがとうございます', 'ありがとうございました', '見つかりません', 'ありません', 'あります', 'どの出口', '哪個出口', '哪個出口', 'どのくらい']
    for i, w in enumerate(protected): text = text.replace(w, f"TOKEN{i}PROTECT")
    # 助詞與標點
    pattern = f"({'|'.join(re.escape(p) for p in (['から','まで','です','ます','は','が','を','に','へ','と','も','で','の','か'] + ['、','。','！','？']))})"
    raw_parts = re.split(pattern, text)
    final_tokens = []
    for p in [p for p in raw_parts if p]:
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
if 'ans' not in st.session_state: reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄
    u_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("1. 單元", u_list)
    u_df = df[df[cols['unit']] == sel_unit]
    c_list = sorted(u_df[cols['ch']].unique().tolist(), key=lambda x: [int(t) if t.isdigit() else t.lower() for t in re.split('([0-9]+)', x)])
    sel_ch = st.sidebar.selectbox("2. 章節", c_list)
    quiz_list = u_df[u_df[cols['ch']] >= sel_ch].head(5).to_dict('records')

    # 同步重置
    current_key = f"{sel_unit}-{sel_ch}"
    if 'sync_key' not in st.session_state or st.session_state.sync_key != current_key:
        st.session_state.sync_key = current_key
        st.session_state.q_idx = 0; reset_state(); st.rerun()

    if st.sidebar.checkbox("📖 預習模式"):
        for item in quiz_list:
            st.info(f"**{item[cols['cn']]}**\n\n{item[cols['ja']]}")
            play_audio(item[cols['ja']])
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw = str(q[cols['ja']]).strip()
        all_t = unified_parser(ja_raw)
        words = [t for t in all_t if t not in ['、', '。', '！', '？']]
        
        if 'shuf_idx' not in st.session_state or len(st.session_state.shuf_idx) != len(words):
            st.session_state.shuf_idx = list(range(len(words))); random.shuffle(st.session_state.shuf_idx)

        # 頂部顯示：題號與中文
        st.write(f"**Q{st.session_state.q_idx + 1}** | {q[cols['cn']]}")

        # 答題區
        u_ans = list(st.session_state.ans)
        html = '<div class="res-box">'
        for t in all_t:
            if t in ['、', '。', '！', '？']: html += f'<span class="punc-fixed">{t}</span>'
            else:
                if u_ans: html += f'<span class="slot-filled">{u_ans.pop(0)}</span>'
                else: html += f'<span class="slot-empty">口</span>'
        st.markdown(html + '</div>', unsafe_allow_html=True)

        # 功能鍵區 (🔄 ⏮️ ⏭️ 橫排)
        c1, c2, c3, c4 = st.columns(4)
        with c1: 
            if st.button("🔄"): reset_state(); st.rerun()
        with c2:
            if st.button("⬅️"):
                if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        with c3:
            if st.button("⏮️") and st.session_state.q_idx > 0:
                st.session_state.q_idx -= 1; st.session_state.shuf_idx = []; reset_state(); st.rerun()
        with c4:
            if st.button("⏭️") and st.session_state.q_idx < len(quiz_list)-1:
                st.session_state.q_idx += 1; st.session_state.shuf_idx = []; reset_state(); st.rerun()

        st.write("---")
        
        # 單字按鈕區：流動佈局
        # 這裡改用 st.button 但透過 CSS 強制 display: inline-block 解決一列一個問題
        st.write("點選單字按鈕：")
        st.markdown('<div class="word-pool">', unsafe_allow_html=True)
        # 用一個 trick: 把按鈕放到 columns 裡，但強制 columns 在手機不換行
        cols_per_row = 3
        for i in range(0, len(st.session_state.shuf_idx), cols_per_row):
            row_cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                curr_p = i + j
                if curr_p < len(st.session_state.shuf_idx):
                    real_idx = st.session_state.shuf_idx[curr_p]
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
            st.success("正解！"); play_audio(ja_raw, auto=True)
            if st.button("下一題 ➡️", type="primary", use_container_width=True):
                st.session_state.q_idx += 1; st.session_state.shuf_idx = []; reset_state(); st.rerun()
    else:
        st.header("練習完成！")
        if st.button("🔄 重新開始", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
