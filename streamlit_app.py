"""
================================================================
【日文結構練習器 - 專業標註版】
版本編號：v2.6.20260306
更新時間：2026-03-06
核心修復：使用 Base64 編碼嵌入音訊，徹底解決 iPhone 播放器灰色問題。
================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
import requests
import base64

# --- 【重點 1】手機版視覺優化與 CSS 樣式 ---
st.set_page_config(page_title="🇯🇵 日文結構練習器 v2.6", layout="wide")

st.markdown("""
    <style>
    /* 加大按鈕，方便 iPhone 觸控 */
    .stButton>button { width: 100%; border-radius: 8px; height: 3.2em; font-size: 16px !important; margin-bottom: 5px; }
    /* 答案顯示區：Flexbox 佈局確保格位與標點完美對齊 */
    .res-box { display: flex; flex-wrap: wrap; gap: 8px; background-color: #f8fafc; padding: 20px; border-radius: 15px; border: 2px solid #e2e8f0; min-height: 100px; margin-bottom: 20px; align-items: center; }
    /* 單字填充空格樣式 */
    .word-slot { min-width: 65px; height: 45px; border-bottom: 3px solid #cbd5e1; display: flex; align-items: center; justify-content: center; font-size: 22px; color: #1e40af; font-weight: bold; }
    /* 預顯標點符號樣式 */
    .punc-display { font-size: 26px; color: #94a3b8; font-weight: bold; margin: 0 2px; }
    </style>
""", unsafe_allow_html=True)

# --- 【重點 2】獨立解決方案：Base64 音訊嵌入技術 ---
def get_audio_html(text):
    """
    透過伺服器端抓取 Google TTS 並轉為 Base64 字串，
    直接將音訊資料嵌入 HTML，繞過行動裝置瀏覽器的預載限制。
    """
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={text}"
    try:
        response = requests.get(tts_url)
        if response.status_code == 200:
            b64 = base64.b64encode(response.content).decode()
            # 直接建立 Data URI 音訊標籤，確保 iPhone 上不顯示灰色
            return f'<audio controls style="width:100%; height:45px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
        else: return "音訊載入失敗"
    except Exception as e: return f"錯誤: {e}"

# --- 【重點 3】資料讀取與結構化拆解邏輯 ---
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
    """
    原地拆解法：連同標點符號一起分析，確保語意結構不變。
    優先讀取手動空格，其次為自動助詞拆分。
    """
    raw_parts = re.split(r'([、。！？])', text.strip())
    structure = []
    for part in raw_parts:
        if not part: continue
        if part in ['、', '。', '！', '？']:
            structure.append({"type": "punc", "content": part})
        else:
            if " " in part or "　" in part: # 手動空格優先
                tokens = [t for t in re.split(r'[ 　]+', part) if t]
            else: # 自動助詞拆分
                particles = ['は', 'が', 'を', 'に', 'へ', 'と', 'も', 'で', 'の', 'から', 'まで']
                pattern = f"({'|'.join(particles)})"
                tokens = [t for t in re.split(pattern, part) if t]
            for token in tokens:
                structure.append({"type": "word", "content": token})
    return structure

# --- 【重點 4】狀態重置與初始化 ---
def reset_state():
    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct = [], [], [], False

if 'q_idx' not in st.session_state:
    st.session_state.q_idx, st.session_state.num_q = 0, 10
    reset_state()

df, cols = load_data()

# --- 【重點 5】主程式 UI 與 功能邏輯 ---
if df is not None:
    # 側邊欄：範圍選擇與題數調整
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

    # 顯示渲染
    if preview_mode:
        st.title("📖 課文預習 (語音已優化)")
        for item in quiz_list:
            with st.expander(f"【{item[cols['ch']]}】{item[cols['cn']]}", expanded=True):
                st.write(f"### {item[cols['ja']]}")
                # 這裡調用 Base64 音訊嵌入函數，解決 iPhone 灰色問題
                st.markdown(get_audio_html(item[cols['ja']]), unsafe_allow_html=True)
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw = str(q[cols['ja']]).strip()
        sentence_struct = get_sentence_structure(ja_raw)
        word_tokens = [s['content'] for s in sentence_struct if s['type'] == 'word']
        
        if not st.session_state.shuf:
            st.session_state.shuf = list(word_tokens); random.shuffle(st.session_state.shuf)

        st.subheader(f"Q {st.session_state.q_idx + 1} / {len(quiz_list)}")
        st.info(f"💡 {q[cols['cn']]}")

        # 核心：格位填充與標點符號預顯
        current_ans_list = list(st.session_state.ans)
        html_content = '<div class="res-box">'
        for item in sentence_struct:
            if item['type'] == 'punc': html_content += f'<span class="punc-display">{item["content"]}</span>'
            else:
                val = current_ans_list.pop(0) if current_ans_list else ""
                html_content += f'<div class="word-slot">{val}</div>'
        html_content += '</div>'
        st.markdown(html_content, unsafe_allow_html=True)

        # 功能導航鍵
        col1, col2, col3, col4 = st.columns(4)
        if col1.button("⬅️上一題") and st.session_state.q_idx > 0: st.session_state.q_idx -= 1; reset_state(); st.rerun()
        if col2.button("➡️下一題") and st.session_state.q_idx < len(quiz_list)-1: st.session_state.q_idx += 1; reset_state(); st.rerun()
        if col3.button("🔄重填"): reset_state(); st.rerun()
        if col4.button("⬅️退回"): 
            if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()

        st.write("---")
        # 單字按鈕
        btn_cols = st.columns(2)
        for i, t in enumerate(st.session_state.shuf):
            if i not in st.session_state.used_history:
                with btn_cols[i % 2]:
                    if st.button(t, key=f"btn_{i}"):
                        st.session_state.ans.append(t); st.session_state.used_history.append(i); st.rerun()

        # 判分
        if len(st.session_state.ans) == len(word_tokens) and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary"):
                if "".join(st.session_state.ans) == "".join(word_tokens):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("順序不對喔！")

        if st.session_state.is_correct:
            st.success("🎊 正解！")
            st.markdown(get_audio_html(ja_raw), unsafe_allow_html=True)
            if st.button("下一題 ➡️", type="primary"): st.session_state.q_idx += 1; reset_state(); st.rerun()
