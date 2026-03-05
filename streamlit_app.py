import streamlit as st
import pandas as pd
import random
import re

# ==========================================
# 🌟 程式特色與功能說明 (Program Features)
# ==========================================
# 1. 【填空式重組介面】：答題區預先顯示標點符號與空白框，直觀掌握句子結構。
# 2. 【標點免輸入】：標點符號固定在正確位置，學生只需專注於單字與助詞排序。
# 3. 【智慧分詞系統】：精準切分單字與助詞，並保護常用長詞（如：ありがとうございます）。
# 4. 【響應式優化】：針對手機設計 2 欄大按鈕，操作流暢。
# 5. 【智慧排序】：支援「數字+字母」的章節排序。
# 6. 【功能列全開】：重填、退回一步、上一題、跳過下一題功能完整。
# ==========================================

st.set_page_config(page_title="🇯🇵 日文填空重組練習器", layout="wide")

# CSS 優化：定義空白框與標點樣式
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.2em; font-size: 18px !important; margin-bottom: 8px; }
    .res-box {
        font-size: 26px; color: #1e40af; background-color: #eff6ff; 
        padding: 20px; border-radius: 12px; border: 2px dashed #60a5fa; 
        min-height: 100px; margin-bottom: 15px; line-height: 2.0; letter-spacing: 2px;
        display: flex; flex-wrap: wrap; align-items: center;
    }
    .slot-empty { color: #bfdbfe; border-bottom: 2px solid #bfdbfe; margin: 0 5px; min-width: 40px; text-align: center; }
    .slot-filled { color: #1e40af; border-bottom: 2px solid #60a5fa; margin: 0 5px; }
    .punc-fixed { color: #1e3a8a; font-weight: bold; font-size: 30px; padding: 0 5px; }
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
        df[cols['unit']] = df[cols['unit']].astype(str).str.strip()
        df[cols['ch']] = df[cols['ch']].astype(str).str.strip()
        return df.dropna(subset=[cols['ja'], cols['cn']]), cols
    except: return None, None

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def word_splitter(text, include_punc=False):
    """
    分詞器：
    include_punc=False 用於生成按鈕（不含標點）
    include_punc=True 用於建立答題區結構（含標點）
    """
    text = re.sub(r'[\s\u3000]', '', text)
    protected = ['ありがとうございます', 'ありがとうございました', 'どのくらい', 'どのぐらい', 'すみません', 'ごめんなさい', 'おはようございます', '失礼します', 'お疲れ様です']
    for i, w in enumerate(protected):
        text = text.replace(w, f"TOKEN{i}PROTECT")
    
    particles = ['から', 'まで', 'です', 'ます', 'は', 'が', 'を', 'に', 'へ', 'と', 'も', 'で', 'の', 'か']
    punctuations = ['、', '。', '！', '？']
    
    if include_punc:
        pattern = f"({'|'.join(re.escape(p) for p in (particles + punctuations))})"
    else:
        pattern = f"({'|'.join(re.escape(p) for p in particles)})"
        text = re.sub(r'[、。！？]', '', text) # 生成按鈕時徹底移除標點

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

if 'q_idx' not in st.session_state:
    st.session_state.q_idx = 0
    st.session_state.num_q = 5
    reset_state()

df, cols = load_data()

if df is not None:
    # --- 側邊欄 ---
    st.sidebar.header("⚙️ 練習設定")
    u_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", u_list)
    u_df = df[df[cols['unit']] == sel_unit]
    c_list = sorted(u_df[cols['ch']].unique().tolist(), key=natural_sort_key)
    sel_start_ch = st.sidebar.selectbox("2. 起始章節", c_list)
    
    start_idx = c_list.index(sel_start_ch)
    filtered_df = u_df[u_df[cols['ch']].isin(c_list[start_idx:])]
    max_q = len(filtered_df)

    st.sidebar.write(f"3. 練習題數: {st.session_state.num_q}")
    st.session_state.num_q = st.sidebar.slider("調整題數", 1, max_q, st.session_state.num_q)
    c_m, c_p = st.sidebar.columns(2)
    with c_m:
        if st.button("➖ 少一題"):
            if st.session_state.num_q > 1: st.session_state.num_q -= 1; st.rerun()
    with c_p:
        if st.button("➕ 多一題"):
            if st.session_state.num_q < max_q: st.session_state.num_q += 1; st.rerun()

    quiz_list = filtered_df.head(st.session_state.num_q).to_dict('records')

    if 'lkey' not in st.session_state or st.session_state.lkey != f"{sel_unit}-{sel_start_ch}-{st.session_state.num_q}":
        st.session_state.lkey = f"{sel_unit}-{sel_start_ch}-{st.session_state.num_q}"; st.session_state.q_idx = 0; reset_state(); st.rerun()

    # --- 主畫面 ---
    if st.sidebar.checkbox("📖 預習模式"):
        for item in quiz_list:
            with st.expander(f"【{item[cols['ch']]}】{item[cols['cn']]}", expanded=True):
                st.write(f"### {item[cols['ja']]}")
                st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={item[cols['ja']]}")
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw = str(q[cols['ja']]).strip()
        
        # 建立按鈕 (不含標點)
        if not st.session_state.shuf:
            st.session_state.shuf = word_splitter(ja_raw, include_punc=False)
            random.shuffle(st.session_state.shuf)

        st.subheader(f"Q {st.session_state.q_idx + 1} / {len(quiz_list)}")
        st.info(f"💡 {q[cols['cn']]}")

        # --- 填空式重組核心邏輯 ---
        full_structure = word_splitter(ja_raw, include_punc=True)
        user_ans_temp = list(st.session_state.ans)
        display_html = '<div class="res-box">'
        
        for part in full_structure:
            if part in ['、', '。', '！', '？']:
                display_html += f'<span class="punc-fixed">{part}</span>'
            else:
                if user_ans_temp:
                    word = user_ans_temp.pop(0)
                    display_html += f'<span class="slot-filled">{word}</span>'
                else:
                    display_html += f'<span class="slot-empty">口</span>'
        display_html += '</div>'
        st.markdown(display_html, unsafe_allow_html=True)

        # 功能鍵
        ctrl = st.columns(4)
        with ctrl[0]:
            if st.button("🔄重填"): reset_state(); st.rerun()
        with ctrl[1]:
            if st.button("⬅️退回"):
                if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        with ctrl[2]:
            if st.button("⏮️上題"):
                if st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        with ctrl[3]:
            if st.button("⏭️下題"):
                st.session_state.q_idx += 1; reset_state(); st.rerun()

        st.write("---")
        b_cols = st.columns(2) 
        for i, t in enumerate(st.session_state.shuf):
            if t and i not in st.session_state.used_history:
                with b_cols[i % 2]:
                    if st.button(t, key=f"btn_{i}"):
                        st.session_state.ans.append(t); st.session_state.used_history.append(i); st.rerun()

        if st.session_state.ans and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                clean_target = re.sub(r'[、。！？\s]', '', ja_raw)
                if "".join(st.session_state.ans) == clean_target:
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔！")

        if st.session_state.is_correct:
            st.success("🎊 正解！")
            st.markdown(f"### {ja_raw}")
            st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={ja_raw}")
            if st.button("下一題 ➡️", type="primary", use_container_width=True):
                st.session_state.q_idx += 1; reset_state(); st.rerun()
    else:
        st.header("🎊 練習完成！")
        if st.button("🔄 重新開始", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
