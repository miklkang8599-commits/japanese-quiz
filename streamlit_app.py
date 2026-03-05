import streamlit as st
import pandas as pd
import random
import re

# 設定網頁標題
st.set_page_config(page_title="🇯🇵 日文全單字重組 (功能優化版)", layout="wide")

# 手機版 UI 優化
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

# --- 1. 資料讀取 ---
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

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def word_splitter(text):
    text = re.sub(r'[\s\u3000]', '', text)
    protected = ['ありがとうございます', 'ありがとうございました', 'どのくらい', 'どのぐらい', 'すみません', 'ごめんなさい', 'おはようございます', '失礼します', 'お疲れ様です']
    for i, w in enumerate(protected):
        text = text.replace(w, f"TOKEN{i}PROTECT")
    particles = ['から', 'まで', 'です', 'ます', 'は', 'が', 'を', 'に', 'へ', 'と', 'も', 'で', 'の', 'か']
    punctuations = ['、', '。', '！', '？']
    pattern = f"({'|'.join(re.escape(p) for p in (particles + punctuations))})"
    raw_parts = re.split(pattern, text)
    tokens = []
    for p in raw_parts:
        if not p: continue
        is_protected = False
        for i, w in enumerate(protected):
            if f"TOKEN{i}PROTECT" in p:
                tokens.append(w); is_protected = True; break
        if not is_protected:
            p_clean = p.strip()
            if p_clean: tokens.append(p_clean)
    return tokens

def reset_state():
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

# --- 初始化狀態 ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx = 0
if 'num_q' not in st.session_state:
    st.session_state.num_q = 5  # 預設題數設為 5
if 'ans' not in st.session_state:
    reset_state()

df, cols = load_data()

if df is not None:
    # --- 側邊欄 ---
    st.sidebar.header("⚙️ 練習設定")
    
    # 1. 選擇單元
    u_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", u_list)
    u_df = df[df[cols['unit']] == sel_unit]
    
    # 2. 選擇章節 (智慧排序)
    c_list_raw = u_df[cols['ch']].unique().tolist()
    c_list = sorted(c_list_raw, key=natural_sort_key)
    sel_start_ch = st.sidebar.selectbox("2. 起始章節", c_list)
    
    # 過濾範圍
    start_idx = c_list.index(sel_start_ch)
    valid_chapters = c_list[start_idx:]
    filtered_df = u_df[u_df[cols['ch']].isin(valid_chapters)]
    max_q_available = len(filtered_df)

    # 確保題數不會超過最大可用題數
    if st.session_state.num_q > max_q_available:
        st.session_state.num_q = max_q_available

    # 3. 練習題數控制
    st.sidebar.write(f"3. 設定練習題數 (最大: {max_q_available})")
    
    # 數字拉桿 (Slider)
    st.session_state.num_q = st.sidebar.slider(
        "調整題數", 
        min_value=1, 
        max_value=max_q_available, 
        value=st.session_state.num_q,
        step=1
    )
    
    # 微調按鈕
    c_m, c_p = st.sidebar.columns(2)
    with c_m:
        if st.button("➖ 少一題"):
            if st.session_state.num_q > 1: 
                st.session_state.num_q -= 1
                st.rerun()
    with c_p:
        if st.button("➕ 多一題"):
            if st.session_state.num_q < max_q_available: 
                st.session_state.num_q += 1
                st.rerun()

    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    # 切換條件重置
    ckey = f"{sel_unit}-{sel_start_ch}-{st.session_state.num_q}"
    if 'lkey' not in st.session_state or st.session_state.lkey != ckey:
        st.session_state.lkey = ckey
        st.session_state.q_idx = 0
        reset_state()
        st.rerun()

    # --- 主畫面測驗區 ---
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

        user_ans = "".join(st.session_state.ans)
        st.markdown(f'<div class="res-box">{user_ans if user_ans else "請點選按鈕拼湊句子..."}</div>', unsafe_allow_html=True)

        ctrl_cols = st.columns(4)
        with ctrl_cols[0]:
            if st.button("🔄重填"): reset_state(); st.rerun()
        with ctrl_cols[1]:
            if st.button("⬅️退回"):
                if st.session_state.used_history:
                    st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        with ctrl_cols[2]:
            if st.button("⏮️上題"):
                if st.session_state.q_idx > 0:
                    st.session_state.q_idx -= 1; reset_state(); st.rerun()
        with ctrl_cols[3]:
            if st.button("⏭️下題"):
                st.session_state.q_idx += 1; reset_state(); st.rerun()

        st.write("---")
        b_cols = st.columns(2) 
        for i, t in enumerate(st.session_state.shuf):
            if t and t.strip() and i not in st.session_state.used_history:
                with b_cols[i % 2]:
                    if st.button(t, key=f"btn_{i}"):
                        st.session_state.ans.append(t); st.session_state.used_history.append(i); st.rerun()

        if st.session_state.ans and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                clean_target = re.sub(r'[\s\u3000]', '', ja_raw)
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
