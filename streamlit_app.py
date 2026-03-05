import streamlit as st
import pandas as pd
import random
import re

# 設定網頁標題
st.set_page_config(page_title="🇯🇵 日文全方位重組練習器", layout="wide")

# CSS 優化：增加字體間距，避免手機端點選太擠
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.2em; font-size: 18px !important; margin-bottom: 8px; }
    .res-box {
        font-size: 26px; color: #1e40af; background-color: #eff6ff; 
        padding: 20px; border-radius: 12px; border: 2px dashed #60a5fa; 
        min-height: 100px; margin-bottom: 15px; line-height: 1.8; letter-spacing: 1px;
    }
    [data-testid="stSidebar"] .stButton>button { height: 2.5em; font-size: 16px !important; }
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
        cols = {"unit": "單元", "ch": "章節", "ja": "日文原文", "cn": "中文意譯"}
        for v in cols.values():
            if v not in df.columns: return None, None
        df[cols['unit']] = df[cols['unit']].astype(str).str.strip()
        df[cols['ch']] = df[cols['ch']].astype(str).str.strip()
        return df.dropna(subset=[cols['ja'], cols['cn']]), cols
    except: return None, None

def word_splitter(text):
    """
    全方位拆解邏輯：
    1. 識別助詞並拆開。
    2. 識別標點符號（、。！？）並拆開。
    """
    text = text.strip()
    particles = ['は', 'が', 'を', 'に', 'へ', 'と', 'も', 'で', 'の', 'から', 'まで']
    # 建立正則表達式，同時捕捉助詞與標點符號
    # 用括號捕捉，確保 re.split 會保留這些分隔符號
    pattern = f"({'|'.join(particles)}|、|。|！|？)"
    
    raw_parts = re.split(pattern, text)
    # 過濾空字串
    tokens = [p for p in raw_parts if p and p.strip()]
    return tokens

def reset_state():
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

if 'q_idx' not in st.session_state:
    st.session_state.q_idx = 0
    st.session_state.num_q = 10
    reset_state()

df, cols = load_data()

if df is not None:
    # --- 側邊欄 ---
    st.sidebar.header("⚙️ 練習設定")
    u_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", u_list)
    u_df = df[df[cols['unit']] == sel_unit]
    
    c_list = sorted(u_df[cols['ch']].unique())
    sel_start_ch = st.sidebar.selectbox("2. 起始章節", c_list)
    
    filtered_df = u_df[u_df[cols['ch']] >= sel_start_ch]
    max_q = len(filtered_df)

    st.sidebar.write(f"3. 練習題數： **{st.session_state.num_q}**")
    c_min, c_pls = st.sidebar.columns(2)
    with c_min:
        if st.button("➖ 少一題"):
            if st.session_state.num_q > 1: st.session_state.num_q -= 1; st.rerun()
    with c_pls:
        if st.button("➕ 多一題"):
            if st.session_state.num_q < max_q: st.session_state.num_q += 1; st.rerun()

    if st.session_state.num_q > max_q: st.session_state.num_q = max_q
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    ckey = f"{sel_unit}-{sel_start_ch}-{st.session_state.num_q}"
    if 'lkey' not in st.session_state or st.session_state.lkey != ckey:
        st.session_state.lkey = ckey
        st.session_state.q_idx = 0
        reset_state()
        st.rerun()

    # --- 主畫面 ---
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

        # 拼湊區 (直接顯示使用者選擇的內容，無標點預顯)
        user_ans = "".join(st.session_state.ans)
        st.markdown(f'<div class="res-box">{user_ans if user_ans else "請依序點選單字、助詞與標點..."}</div>', unsafe_allow_html=True)

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
        # 按鈕顯示 (手機建議 2 欄)
        b_cols = st.columns(2) 
        for i, t in enumerate(st.session_state.shuf):
            if i not in st.session_state.used_history:
                with b_cols[i % 2]:
                    if st.button(t, key=f"btn_{i}"):
                        st.session_state.ans.append(t)
                        st.session_state.used_history.append(i)
                        st.rerun()

        if st.session_state.ans and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                # 完全對比 (包含標點)
                if "".join(st.session_state.ans) == ja_raw.replace(" ",""):
                    st.session_state.is_correct = True; st.rerun()
                else: 
                    st.error("順序不對喔！別忘了標點符號的位置。")

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
