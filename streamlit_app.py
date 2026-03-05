import streamlit as st
import pandas as pd
import random
import re

# 設定網頁標題
st.set_page_config(page_title="🇯🇵 日文重組 (標點預顯版)", layout="wide")

# 加大手機版按鈕與文字
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3.2em;
        font-size: 18px !important;
        margin-bottom: 8px;
        background-color: #ffffff;
        border: 1px solid #d1d5db;
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
        line-height: 1.4;
    }
    .punc-hint {
        color: #94a3b8;
        font-weight: bold;
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
    """將助詞獨立切開，並徹底過濾掉所有標點符號"""
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

if 'q_idx' not in st.session_state:
    st.session_state.q_idx = 0
    reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄
    unit_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", unit_list)
    unit_df = df[df[cols['unit']] == sel_unit]
    ch_list = sorted(unit_df[cols['ch']].unique())
    sel_start_ch = st.sidebar.selectbox("2. 起始章節", ch_list)
    
    filtered_df = unit_df[unit_df[cols['ch']] >= sel_start_ch]
    
    if not filtered_df.empty:
        num_q = st.sidebar.slider("3. 練習題數", 1, len(filtered_df), min(10, len(filtered_df)))
        quiz_list = filtered_df.head(num_q).to_dict('records')

        if 'last_key' not in st.session_state or st.session_state.last_key != f"{sel_unit}-{sel_start_ch}-{num_q}":
            st.session_state.last_key = f"{sel_unit}-{sel_start_ch}-{num_q}"
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
            
            # 獲取原句末尾的標點符號
            punc_match = re.search(r'[。！？]+$', ja_raw)
            punc_hint = punc_match.group() if punc_match else ""

            if not st.session_state.shuf:
                st.session_state.shuf = word_splitter(ja_raw)
                random.shuffle(st.session_state.shuf)

            st.subheader(f"Q {st.session_state.q_idx + 1} / {len(quiz_list)}")
            st.info(f"💡 {q[cols['cn']]}")

            # --- 拼湊顯示區（包含標點符號提示） ---
            user_input = "".join(st.session_state.ans)
            if user_input:
                display_text = f'{user_input}<span class="punc-hint">{punc_hint}</span>'
            else:
                display_text = f'<span style="color:#94a3b8; font-size:18px;">請選取單字... </span><span class="punc-hint">{punc_hint}</span>'
            
            st.markdown(f'<div class="res-box">{display_text}</div>', unsafe_allow_html=True)

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
                    else: st.error("順序不對喔！再試試看")

            if st.session_state.is_correct:
                st.success(f"🎊 正解！")
                st.markdown(f"### {ja_raw}")
                st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={ja_raw}")
                if st.button("下一題 ➡️", type="primary", use_container_width=True):
                    st.session_state.q_idx += 1; reset_state(); st.rerun()
        else:
            st.header("🎊 練習完成！")
            st.balloons()
            if st.button("🔄 重新開始", type="primary", use_container_width=True): 
                st.session_state.q_idx = 0; reset_state(); st.rerun()
