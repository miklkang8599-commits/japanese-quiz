import streamlit as st
import pandas as pd
import random
import re

# 設定網頁標題
st.set_page_config(page_title="🇯🇵 日文重組 (題數加減版)", layout="wide")

# CSS 優化
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3.2em;
        font-size: 18px !important;
        margin-bottom: 8px;
    }
    .res-box {
        font-size: 26px; 
        color: #1e40af; 
        background-color: #eff6ff; 
        padding: 18px; 
        border-radius: 12px; 
        border: 2px dashed #60a5fa; 
        min-height: 90px; 
        margin-bottom: 15px;
    }
    .punc-hint { color: #94a3b8; font-weight: bold; padding: 0 2px; }
    /* 讓側邊欄按鈕稍微縮小一點，適合點擊 */
    [data-testid="stSidebar"] .stButton>button {
        height: 2.5em;
        font-size: 16px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 1. 設定 Google Sheets 資訊 ---
SHEET_ID = "12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA"
GID = "1337973082"
url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        COL_UNIT, COL_CH, COL_JA, COL_CN = "單元", "章節", "日文原文", "中文意譯"
        df[COL_UNIT] = df[COL_UNIT].astype(str).str.strip()
        df[COL_CH] = df[COL_CH].astype(str).str.strip()
        df = df.dropna(subset=[COL_JA, COL_CN])
        return df, {"unit": COL_UNIT, "ch": COL_CH, "ja": COL_JA, "cn": COL_CN}
    except: return None, None

def word_splitter(text):
    clean_text = re.sub(r'[、。！？\s]', '', text)
    particles = ['は', 'が', 'を', 'に', 'へ', 'と', 'も', 'で', 'の', 'から', 'まで']
    pattern = f"({'|'.join(particles)})"
    raw_tokens = re.split(pattern, clean_text)
    return [t for t in raw_tokens if t and t.strip()]

def reset_state():
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

# 初始化 Session State
if 'q_idx' not in st.session_state:
    st.session_state.q_idx = 0
    st.session_state.num_q = 10 # 預設練習題數
    reset_state()

df, cols = load_data()

if df is not None:
    # --- 側邊欄設定 ---
    st.sidebar.header("⚙️ 練習設定")
    
    unit_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", unit_list)
    unit_df = df[df[cols['unit']] == sel_unit]
    
    ch_list = sorted(unit_df[cols['ch']].unique())
    sel_start_ch = st.sidebar.selectbox("2. 起始章節", ch_list)
    
    filtered_df = unit_df[unit_df[cols['ch']] >= sel_start_ch]
    max_q = len(filtered_df)

    # 3. 練習題數 (+/- 功能)
    st.sidebar.write(f"3. 練習題數： **{st.session_state.num_q}**")
    c_minus, c_plus = st.sidebar.columns(2)
    with c_minus:
        if st.button("➖ 少一題"):
            if st.session_state.num_q > 1:
                st.session_state.num_q -= 1
                st.rerun()
    with c_plus:
        if st.button("➕ 多一題"):
            if st.session_state.num_q < max_q:
                st.session_state.num_q += 1
                st.rerun()

    # 安全檢查：確保題數不超過最大範圍
    if st.session_state.num_q > max_q: st.session_state.num_q = max_q

    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    # 切換條件時重置
    cur_key = f"{sel_unit}-{sel_start_ch}-{st.session_state.num_q}"
    if 'last_key' not in st.session_state or st.session_state.last_key != cur_key:
        st.session_state.last_key = cur_key
        st.session_state.q_idx = 0
        reset_state()
        st.rerun()

    # 主畫面區
    if st.sidebar.checkbox("📖 預習模式"):
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

        # 標點符號預顯邏輯
        parts = re.split(r'([、。！？])', ja_raw)
        user_input_list = list(st.session_state.ans)
        display_html = ""
        for p in parts:
            if p in ['、', '。', '！', '？']:
                display_html += f'<span class="punc-hint">{p}</span>'
            elif p.strip():
                tokens_in_part = word_splitter(p)
                for _ in range(len(tokens_in_part)):
                    if user_input_list: display_html += user_input_list.pop(0)
        
        if not st.session_state.ans:
            display_html = f'<span style="color:#94a3b8; font-size:16px;">請選取單字...</span>' + display_html
        
        st.markdown(f'<div class="res-box">{display_html}</div>', unsafe_allow_html=True)

        # 功能鍵
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if st.button("🔄重填"): reset_state(); st.rerun()
        with c2:
            if st.button("⬅️退回"):
                if st.session_state.used_history:
                    st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        with c3:
            if st.button("⏭️跳過"):
                st.session_state.q_idx += 1; reset_state(); st.rerun()

        st.write("---")
        btn_cols = st.columns(2) 
        for i, t in enumerate(st.session_state.shuf):
            if i not in st.session_state.used_history:
                with btn_cols[i % 2]:
                    if st.button(t, key=f"btn_{i}"):
                        st.session_state.ans.append(t)
                        st.session_state.used_history.append(i)
                        st.rerun()

        if st.session_state.ans and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                clean_target = re.sub(r'[、。！？\s]', '', ja_raw)
                if "".join(st.session_state.ans) == clean_target:
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔！")

        if st.session_state.is_correct:
            st.success(f"🎊 正解！")
            st.markdown(f"### {ja_raw}")
            st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={ja_raw}")
            if st.button("下一題 ➡️", type="primary", use_container_width=True):
                st.session_state.q_idx += 1; reset_state(); st.rerun()
    else:
        st.header("🎊 練習完成！")
        if st.button("🔄 重新開始", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
