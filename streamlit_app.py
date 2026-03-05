"""
================================================================
【日文填充重組練習器 - 功能聲明】
1. 資料連動：即時讀取 Google Sheets (支援單元、章節篩選)。
2. 填充格位：依據日文單字/助詞數量，自動生成底線空格。
3. 標點預顯：自動偵測並在空格間預填「、。！？」，強化語感。
4. 手機優化：針對 iPhone 介面設計 2 欄式大按鈕，方便操作。
5. 導航系統：支援「上一題」、「下一題(跳過)」、「重填」與「退回」。
6. 預習模式：提供全文清單與 Google TTS 真人語音朗讀。
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re

# --- 重點 1：介面視覺優化 (CSS) ---
st.set_page_config(page_title="🇯🇵 日文填充練習器", layout="wide")

st.markdown("""
    <style>
    /* 按鈕樣式：加大尺寸以利 iPhone 觸控 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3.2em;
        font-size: 16px !important;
        margin-bottom: 5px;
    }
    /* 答案顯示區：Flexbox 佈局讓格位與標點自動排列 */
    .res-box {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        background-color: #f8fafc;
        padding: 20px;
        border-radius: 15px;
        border: 2px solid #e2e8f0;
        min-height: 100px;
        margin-bottom: 20px;
        align-items: center;
    }
    /* 單字空格：模擬填充題的底線感 */
    .word-slot {
        min-width: 60px;
        height: 40px;
        border-bottom: 3px solid #cbd5e1;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        color: #1e40af;
        font-weight: bold;
    }
    /* 標點符號：淡灰色預顯，不需使用者點選 */
    .punc-display {
        font-size: 24px;
        color: #94a3b8;
        font-weight: bold;
        margin: 0 2px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 重點 2：雲端資料設定 ---
SHEET_ID = "12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA"
GID = "1337973082"
url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60)
def load_data():
    """讀取並清洗 Google Sheets 資料"""
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        COL_UNIT, COL_CH, COL_JA, COL_CN = "單元", "章節", "日文原文", "中文意譯"
        df[COL_UNIT] = df[COL_UNIT].astype(str).str.strip()
        df[COL_CH] = df[COL_CH].astype(str).str.strip()
        df = df.dropna(subset=[COL_JA, COL_CN])
        return df, {"unit": COL_UNIT, "ch": COL_CH, "ja": COL_JA, "cn": COL_CN}
    except: return None, None

# --- 重點 3：自動分詞邏輯 (核心演算法) ---
def word_splitter(text):
    """將句子切分為單字塊，並獨立出助詞，同時剔除標點符號"""
    clean_text = re.sub(r'[、。！？\s]', '', text)
    # 常見日文格助詞清單
    particles = ['は', 'が', 'を', 'に', 'へ', 'と', 'も', 'で', 'の', 'から', 'まで']
    pattern = f"({'|'.join(particles)})"
    # 使用正則表達式進行切割並保留助詞
    raw_tokens = re.split(pattern, clean_text)
    return [t for t in raw_tokens if t and t.strip()]

def reset_state():
    """清空當前題目的作答進度"""
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

# 初始化 Session 狀態
if 'q_idx' not in st.session_state:
    st.session_state.q_idx = 0
    st.session_state.num_q = 10
    reset_state()

df, cols = load_data()

# --- 重點 4：側邊欄互動設計 ---
if df is not None:
    st.sidebar.header("⚙️ 練習設定")
    
    unit_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", unit_list)
    unit_df = df[df[cols['unit']] == sel_unit]
    
    ch_list = sorted(unit_df[cols['ch']].unique())
    sel_start_ch = st.sidebar.selectbox("2. 起始章節", ch_list)
    
    filtered_df = unit_df[unit_df[cols['ch']] >= sel_start_ch]
    max_q = len(filtered_df)

    # 題數加減按鈕 (+/-)
    st.sidebar.write(f"3. 練習題數： **{st.session_state.num_q}**")
    c_minus, c_plus = st.sidebar.columns(2)
    with c_minus:
        if st.button("➖ 少一題"):
            if st.session_state.num_q > 1: st.session_state.num_q -= 1; st.rerun()
    with c_plus:
        if st.button("➕ 多一題"):
            if st.session_state.num_q < max_q: st.session_state.num_q += 1; st.rerun()

    preview_mode = st.sidebar.checkbox("📖 開啟預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    # 當篩選條件改變時，強制回到第一題並重置狀態
    cur_key = f"{sel_unit}-{sel_start_ch}-{st.session_state.num_q}"
    if 'last_key' not in st.session_state or st.session_state.last_key != cur_key:
        st.session_state.last_key = cur_key
        st.session_state.q_idx = 0
        reset_state(); st.rerun()

    # --- 重點 5：內容渲染邏輯 ---
    if preview_mode:
        st.title("📖 課文預習")
        for item in quiz_list:
            with st.expander(f"【{item[cols['ch']]}】{item[cols['cn']]}", expanded=True):
                st.write(f"### {item[cols['ja']]}")
                st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={item[cols['ja']]}")
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw = str(q[cols['ja']]).strip()
        
        if not st.session_state.shuf:
            st.session_state.shuf = word_splitter(ja_raw)
            random.shuffle(st.session_state.shuf)

        st.subheader(f"Q {st.session_state.q_idx + 1} / {len(quiz_list)}")
        st.info(f"💡 {q[cols['cn']]}")

        # --- 重點 6：格位填充與標點預顯實作 ---
        struct_parts = re.split(r'([、。！？])', ja_raw)
        current_ans_list = list(st.session_state.ans)

        html_content = '<div class="res-box">'
        for part in struct_parts:
            if part in ['、', '。', '！', '？']:
                html_content += f'<span class="punc-display">{part}</span>'
            elif part.strip():
                part_tokens = word_splitter(part)
                for _ in range(len(part_tokens)):
                    val = current_ans_list.pop(0) if current_ans_list else ""
                    html_content += f'
