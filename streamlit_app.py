import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# ==========================================
# 【重點 1】視覺優化與 CSS
# ==========================================
st.set_page_config(page_title="🇯🇵 日文結構練習器", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3.2em; font-size: 16px !important; margin-bottom: 5px; }
    .res-box { display: flex; flex-wrap: wrap; gap: 8px; background-color: #f8fafc; padding: 20px; border-radius: 15px; border: 2px solid #e2e8f0; min-height: 100px; margin-bottom: 20px; align-items: center; }
    .word-slot { min-width: 65px; height: 45px; border-bottom: 3px solid #cbd5e1; display: flex; align-items: center; justify-content: center; font-size: 22px; color: #1e40af; font-weight: bold; }
    .punc-display { font-size: 26px; color: #94a3b8; font-weight: bold; margin: 0 2px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 【重點 2】音訊處理函數 (核心修復)
# ==========================================
def get_audio_html(text):
    """將 Google TTS 音訊轉為 Base64 嵌入 HTML，解決 iPhone 灰色不可點擊問題"""
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
    try:
        response = requests.get(tts_url)
        if response.status_code == 200:
            b64 = base64.b64encode(response.content).decode()
            # 建立直接嵌入的音訊標籤
            return f'<audio controls style="width:100%; height:40px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
        else:
            return "音訊載入失敗"
    except Exception as e:
        return f"錯誤: {e}"

# ==========================================
# 【重點 3】資料讀取與結構拆解
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

def get_sentence_structure(text):
    raw_parts = re.split(r'([、。！？])', text.strip())
    structure = []
    for part in raw_parts:
        if not part: continue
        if part in ['、', '。', '！', '？']:
            structure.append({"type": "punc", "content": part})
        else:
            if " " in part or "　" in part:
                tokens = [t for t in re.split(r'[ 　]+', part) if t]
            else:
                particles = ['は', 'が', 'を', 'に', 'へ', 'と', 'も', 'で', 'の', 'から', 'まで']
                pattern = f"({'|'.join(particles)})"
                tokens = [t for t in re.split(pattern, part) if t]
            for token in tokens:
                structure.append({"type": "word", "content": token})
    return structure

def reset_state():
    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct = [], [], [], False

if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 10
    reset_state()

df, cols = load_data()

# ==========================================
# 【重點 4】UI 與功能邏輯
# ==========================================
if df is not None:
    # 側邊欄與題數加減 (保持原有功能)
    st.sidebar.header("⚙️ 練習設定")
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
        st.title("📖 課文預習")
        for item in quiz_list:
            with st.expander(f"【{item[cols['ch']]}】{item[cols['cn']]}", expanded=True):
                text = item[cols['ja']]
                st.write(f"### {text}")
                # 使用 Base64 HTML 嵌入音訊，解決灰色按鈕問題
                st.markdown(get_audio_html(text), unsafe_allow_html=True)
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw = str(q[cols['ja']]).strip()
        sentence_struct = get_sentence_structure(ja_raw)
        word_tokens = [s['content'] for s in sentence_struct if s['type'] == 'word']
        
        if not st.session_state.shuf:
            st.session_state.shuf = list(word_tokens); random.shuffle(st.session_state.shuf)

        st.subheader(f"Q {st.session_state.q_idx + 1} / {len(quiz_list)}")
        st.info(f"💡 {q[cols['cn']]}")

        # 渲染填充框
        current_ans_list = list(st.session_state.ans)
        html_content = '<div class="res-box">'
        for item in sentence_struct:
            if item['type'] == 'punc': html_content += f'<span class="punc-display">{item["content"]}</span>'
            else:
                val = current_ans_list.pop(0) if current_ans_list else ""
                html_content += f'<div class="word-slot">{val}</div>'
        html_content += '</div>'
        st.markdown(html_content, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)
        if col1.button("⬅️上一題") and st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        if col2.button("➡️下一題") and st.session_state.q_idx < len(quiz_list)-1: st.session_state.q_idx += 1; reset_state(); st.rerun()
        if col3.button("🔄重填"): reset_state(); st.rerun()
        if col4.button("⬅️退回"): 
            if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

        st.write("---")
        btn_cols = st.columns(2)
        for i, t in enumerate(st.session_state.shuf):
            if i not in st.session_state.used_history:
                with btn_cols[i % 2]:
                    if st.button(t, key=f"btn_{i}"):
                        st.session_state.ans.append(t); st.session_state.used_history.append(i); st.rerun()

        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary"):
                if "".join(st.session_state.ans) == "".join(word_tokens):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔！")

        if st.session_state.is_correct:
            st.success("🎊 正解！")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("下一題 ➡️", type="primary"): st.session_state.q_idx += 1; reset_state(); st.rerun()
    else:
        st.header("🎊 練習完成！")
        if st.button("🔄 重新開始", type="primary"): st.session_state.q_idx = 0; reset_state(); st.rerun()
