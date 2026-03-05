import streamlit as st
import pandas as pd
import random
import re
import urllib.parse

# ==========================================
# 🌟 程式特色與功能說明 (Program Features)
# ==========================================
# 1. 【核心音訊修復】：採用直接連結優化，修復 0:00 無法播放問題。
# 2. 【強制流動按鈕】：使用特殊 CSS 覆寫，確保手機直立時按鈕依然橫向並排。
# 3. 【手機端空間節省】：移除所有多餘邊距，將控制鍵緊湊化，減少滑動需求。
# 4. 【填空式邏輯】：答題區預顯標點符號與「口」，精確同步按鈕數量。
# ==========================================

st.set_page_config(page_title="🇯🇵 日文填空重組練習器", layout="wide")

# 強力 CSS：強制繞過 Streamlit 的手機端堆疊限制
st.markdown("""
    <style>
    /* 移除 Streamlit 預設的大邊距 */
    .block-container { padding: 0.5rem 1rem !important; }
    
    /* 答題區：輕量化 */
    .res-box {
        font-size: 18px; color: #1e40af; background-color: #f0f9ff; 
        padding: 8px; border-radius: 8px; border: 1px solid #bae6fd; 
        min-height: 50px; margin-bottom: 8px; line-height: 1.5;
        display: flex; flex-wrap: wrap; align-items: center;
    }
    .slot-empty { color: #cbd5e1; border-bottom: 2px solid #cbd5e1; margin: 0 3px; min-width: 20px; text-align: center; }
    .slot-filled { color: #1e40af; border-bottom: 2px solid #3b82f6; margin: 0 3px; font-weight: bold; }
    .punc-fixed { color: #64748b; font-weight: bold; font-size: 18px; padding: 0 2px; }

    /* 【關鍵】強制按鈕在手機上不堆疊，橫向並排 */
    [data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0px !important;
    }
    div[data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        display: flex !important;
        gap: 5px !important;
    }

    /* 隱藏側邊欄多餘元件 */
    [data-testid="stSidebar"] { width: 220px !important; }
    
    /* 按鈕字體調整 */
    div.stButton > button {
        height: 2.2em !important;
        padding: 0 5px !important;
        font-size: 14px !important;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    </style>
""", unsafe_allow_html=True)

# --- 1. 資料載入 ---
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

def unified_parser(text):
    text = re.sub(r'[\s\u3000]', '', text)
    protected = ['ありがとうございます', 'ありがとうございました', 'すみません', 'どのくらい', 'どのぐらい', 'どの出口', '見つかりません']
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
    st.session_state.shuf = []
    st.session_state.is_correct = False

# --- 初始化 ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 5
    reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄
    u_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("單元", u_list)
    u_df = df[df[cols['unit']] == sel_unit]
    c_list = sorted(u_df[cols['ch']].unique().tolist())
    sel_ch = st.sidebar.selectbox("章節", c_list)
    
    quiz_list = u_df[u_df[cols['ch']] >= sel_ch].head(st.session_state.num_q).to_dict('records')

    # 主畫面
    if st.sidebar.checkbox("📖 預習模式"):
        for item in quiz_list:
            ja = str(item[cols['ja']]).strip()
            st.markdown(f"<div style='background:white; padding:8px; border-radius:5px; margin-bottom:5px; border-left:3px solid #3b82f6; font-size:14px;'><b>{item[cols['cn']]}</b><br>{ja}</div>", unsafe_allow_html=True)
            enc = urllib.parse.quote(ja)
            st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={enc}")
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw = str(q[cols['ja']]).strip()
        all_t = unified_parser(ja_raw)
        puncs = ['、', '。', '！', '？']
        words = [t for t in all_t if t not in puncs]
        
        if not st.session_state.shuf:
            st.session_state.shuf = list(words); random.shuffle(st.session_state.shuf)

        st.markdown(f"**Q{st.session_state.q_idx + 1}** | {q[cols['cn']]}")

        # 答題區
        u_ans = list(st.session_state.ans)
        html = '<div class="res-box">'
        for t in all_t:
            if t in puncs: html += f'<span class="punc-fixed">{t}</span>'
            else:
                if u_ans: html += f'<span class="slot-filled">{u_ans.pop(0)}</span>'
                else: html += f'<span class="slot-empty">口</span>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        # 功能鍵 (強制橫向並排 4 個)
        ctrl_cols = st.columns(4)
        with ctrl_cols[0]: 
            if st.button("🔄"): reset_state(); st.rerun()
        with ctrl_cols[1]:
            if st.button("⬅️"):
                if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        with ctrl_cols[2]:
            if st.button("⏮️"):
                if st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        with ctrl_cols[3]:
            if st.button("⏭️"):
                if st.session_state.q_idx + 1 < len(quiz_list): st.session_state.q_idx += 1; reset_state(); st.rerun()

        st.write("---")
        
        # --- 核心：按鈕區域強制 3 欄排列，不論手機是否直立 ---
        n_cols = 3 
        for i in range(0, len(st.session_state.shuf), n_cols):
            row_cols = st.columns(n_cols)
            for j in range(n_cols):
                idx = i + j
                if idx < len(st.session_state.shuf):
                    if idx not in st.session_state.used_history:
                        word = st.session_state.shuf[idx]
                        with row_cols[j]:
                            if st.button(word, key=f"btn_{idx}", use_container_width=True):
                                st.session_state.ans.append(word)
                                st.session_state.used_history.append(idx)
                                st.rerun()

        if st.session_state.ans and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(words):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔")

        if st.session_state.is_correct:
            st.success("正解！")
            enc = urllib.parse.quote(ja_raw)
            st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={enc}")
            if st.button("下一題 ➡️", type="primary", use_container_width=True):
                st.session_state.q_idx += 1; reset_state(); st.rerun()
    else:
        st.header("練習完成！")
        if st.button("🔄 重新開始", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
