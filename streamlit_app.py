import streamlit as st
import pandas as pd
import random
import re

# ==========================================
# 【重點 1】介面與手機版優化
# ==========================================
st.set_page_config(page_title="🇯🇵 日文填充練習器", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3.2em; font-size: 16px !important; margin-bottom: 5px; }
    .res-box { display: flex; flex-wrap: wrap; gap: 8px; background-color: #f8fafc; padding: 20px; border-radius: 15px; border: 2px solid #e2e8f0; min-height: 100px; margin-bottom: 20px; align-items: center; }
    .word-slot { min-width: 60px; height: 40px; border-bottom: 3px solid #cbd5e1; display: flex; align-items: center; justify-content: center; font-size: 22px; color: #1e40af; font-weight: bold; }
    .punc-display { font-size: 24px; color: #94a3b8; font-weight: bold; margin: 0 2px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 【重點 2】資料讀取
# ==========================================
SHEET_ID = "12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA"
GID = "1337973082"
url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        COL_UNIT, COL_CH, COL_JA, COL_CN = "單元", "章節", "日文原文", "中文意譯"
        df = df.dropna(subset=[COL_JA, COL_CN])
        return df, {"unit": COL_UNIT, "ch": COL_CH, "ja": COL_JA, "cn": COL_CN}
    except: return None, None

# ==========================================
# 【重點 3】修正後的拆解邏輯 (優先讀取空格)
# ==========================================
def word_splitter(text):
    """
    1. 如果字串中有空格，則按空格拆分。
    2. 如果沒空格，才啟動自動助詞拆分。
    """
    text = text.strip()
    
    # 檢查是否有手動空格
    if " " in text or "　" in text:
        # 同時支援半形與全形空格
        raw_tokens = re.split(r'[ 　]+', text)
    else:
        # 自動拆分邏輯 (備援)
        clean_text = re.sub(r'[、。！？\s]', '', text)
        particles = ['は', 'が', 'を', 'に', 'へ', 'と', 'も', 'で', 'の', 'から', 'まで']
        pattern = f"({'|'.join(particles)})"
        raw_tokens = re.split(pattern, clean_text)
    
    # 過濾標點符號，不讓標點成為按鈕
    return [t for t in raw_tokens if t and t not in ['、', '。', '！', '？']]

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

# ==========================================
# 【重點 4】UI 渲染
# ==========================================
if df is not None:
    # 側邊欄設定... (略，保持原有邏輯)
    unit_list = sorted(df[cols['unit']].astype(str).unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", unit_list)
    unit_df = df[df[cols['unit']].astype(str) == sel_unit]
    ch_list = sorted(unit_df[cols['ch']].astype(str).unique())
    sel_start_ch = st.sidebar.selectbox("2. 起始章節", ch_list)
    filtered_df = unit_df[unit_df[cols['ch']].astype(str) >= sel_start_ch]
    
    st.sidebar.write(f"3. 練習題數： **{st.session_state.num_q}**")
    c1, c2 = st.sidebar.columns(2)
    if c1.button("➖ 少一題") and st.session_state.num_q > 1: st.session_state.num_q -= 1; st.rerun()
    if c2.button("➕ 多一題") and st.session_state.num_q < len(filtered_df): st.session_state.num_q += 1; st.rerun()
    
    preview_mode = st.sidebar.checkbox("📖 開啟預習模式")
    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if preview_mode:
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

        # 渲染填充框 (顯示原句結構含標點)
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
                    html_content += f'<div class="word-slot">{val}</div>'
        html_content += '</div>'
        st.markdown(html_content, unsafe_allow_html=True)

        # 功能鍵 (上一題、下一題等)
        col1, col2, col3, col4 = st.columns(4)
        if col1.button("⬅️上一題") and st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        if col2.button("➡️下一題") and st.session_state.q_idx < len(quiz_list)-1: st.session_state.q_idx += 1; reset_state(); st.rerun()
        if col3.button("🔄重填"): reset_state(); st.rerun()
        if col4.button("⬅️退回"): 
            if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

        # 按鈕區 (2 欄排列)
        btn_cols = st.columns(2)
        for i, t in enumerate(st.session_state.shuf):
            if i not in st.session_state.used_history:
                with btn_cols[i % 2]:
                    if st.button(t, key=f"btn_{i}"):
                        st.session_state.ans.append(t); st.session_state.used_history.append(i); st.rerun()

        # 檢查答案
        if len(st.session_state.ans) == len(word_splitter(ja_raw)) and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary"):
                if "".join(st.session_state.ans) == ja_raw.replace(" ","").replace("　","").replace("。","").replace("、","").replace("！","").replace("？",""):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔！")

        if st.session_state.is_correct:
            st.success("🎊 正解！")
            st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={ja_raw}")
            if st.button("下一題 ➡️", type="primary"): st.session_state.q_idx += 1; reset_state(); st.rerun()
