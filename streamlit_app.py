import streamlit as st
import pandas as pd
import random
import re
import requests
import base64
import urllib.parse

# ==========================================
# 🌟 程式特色：手機端絕對流動佈局 (Pure Flex)
# ==========================================
# 1. 【核心修正】：捨棄 st.columns，改用純 CSS Flexbox 確保手機橫向排隊。
# 2. 【空間回收】：移除頂部空白，找回選單按鈕，中文題目完全可見。
# 3. 【Base64 音訊】：徹底解決 iPhone 播放器變灰色 0:00 問題。
# 4. 【按鈕智慧寬度】：長單字佔長位，短助詞佔短位，完美利用手機螢幕。
# ==========================================

st.set_page_config(page_title="🇯🇵 日文重組", layout="wide")

# 強力 CSS：徹底繞過原生組件的垂直限制
st.markdown("""
    <style>
    /* 1. 空間管理：保留頂部選單按鈕，縮小邊距 */
    [data-testid="stHeader"] { display: block !important; height: 3rem !important; }
    .block-container { padding: 3rem 0.6rem 1rem !important; }
    
    /* 2. 答題區 */
    .res-box {
        font-size: 18px; color: #1e40af; background-color: #f0f9ff; 
        padding: 10px; border-radius: 8px; border: 1px solid #bae6fd; 
        min-height: 50px; margin-bottom: 8px; line-height: 1.6;
        display: flex; flex-wrap: wrap; align-items: center;
    }
    .slot-empty { color: #cbd5e1; border-bottom: 2px solid #cbd5e1; margin: 0 3px; min-width: 22px; text-align: center; }
    .slot-filled { color: #1e40af; border-bottom: 2px solid #3b82f6; margin: 0 4px; padding: 0 2px; font-weight: bold; }
    .punc-fixed { color: #64748b; font-weight: bold; font-size: 20px; padding: 0 2px; }

    /* 3. 功能鍵與單字按鈕：強制橫向並排並自動換行 */
    /* 我們直接針對所有被包在流動容器裡的按鈕進行處理 */
    .flow-container {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 6px !important;
        margin-bottom: 10px !important;
    }

    /* 關鍵：讓 Streamlit 的 button 容器失去「佔滿整行」的特性 */
    div.stButton {
        display: inline-block !important;
        width: auto !important;
    }

    div.stButton > button {
        width: auto !important;
        min-width: 45px !important;
        height: 2.4em !important;
        padding: 0 12px !important;
        font-size: 15px !important;
        white-space: nowrap !important;
    }
    
    /* 功能鍵 (🔄等) 專屬縮小 */
    .ctrl-btn button {
        font-size: 18px !important;
        padding: 0 8px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Base64 音訊嵌入 ---
def get_audio_b64(text):
    try:
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={urllib.parse.quote(text)}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            return base64.b64encode(r.content).decode()
    except: return None
    return None

def play_audio(text, auto=False):
    b64 = get_audio_b64(text)
    if b64:
        autoplay = "autoplay" if auto else ""
        st.markdown(f'<audio controls {autoplay} style="width:100%; height:38px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)

# --- 資料讀取 ---
@st.cache_data(ttl=10)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA/export?format=csv&gid=1337973082"
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(subset=['日文原文', '中文意譯']), {'unit': '單元', 'ch': '章節', 'ja': '日文原文', 'cn': '中文意譯'}
    except: return None, None

def unified_parser(text):
    text = re.sub(r'[\s\u3000]', '', text)
    protected = ['ありがとうございます', 'ありがとうございました', '見つかりません', 'ありません', 'あります', 'どの出口', 'ございます']
    for i, w in enumerate(protected): text = text.replace(w, f"TOKEN{i}PROTECT")
    pattern = f"({'|'.join(re.escape(p) for p in (['から','まで','です','ます','は','が','を','に','へ','と','も','で','の','か','、','。','！','？']))})"
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
    st.session_state.is_correct = False

if 'q_idx' not in st.session_state: st.session_state.q_idx = 0
if 'ans' not in st.session_state: reset_state()

df, cols = load_data()

if df is not None:
    # 側邊欄
    u_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("單元", u_list)
    u_df = df[df[cols['unit']] == sel_unit]
    sel_ch = st.sidebar.selectbox("章節", sorted(u_df[cols['ch']].unique().tolist()))
    quiz_list = u_df[u_df[cols['ch']] >= sel_ch].head(5).to_dict('records')

    # 同步鎖
    current_key = f"{sel_unit}-{sel_ch}"
    if 'sync_key' not in st.session_state or st.session_state.sync_key != current_key:
        st.session_state.sync_key = current_key; st.session_state.q_idx = 0; reset_state(); st.rerun()

    if st.sidebar.checkbox("📖 預習模式"):
        for item in quiz_list:
            st.info(f"**{item[cols['cn']]}**\n\n{item[cols['ja']]}")
            play_audio(item[cols['ja']])
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw = str(q[cols['ja']]).strip()
        all_t = unified_parser(ja_raw)
        words = [t for t in all_t if t not in ['、', '。', '！', '？']]
        
        if 'shuf_idx' not in st.session_state or len(st.session_state.shuf_idx) != len(words):
            st.session_state.shuf_idx = list(range(len(words))); random.shuffle(st.session_state.shuf_idx)

        # 頂部中文題目
        st.markdown(f"**Q{st.session_state.q_idx + 1}** | {q[cols['cn']]}")

        # 答題區
        u_ans = list(st.session_state.ans)
        html = '<div class="res-box">'
        for t in all_t:
            if t in ['、', '。', '！', '？']: html += f'<span class="punc-fixed">{t}</span>'
            else:
                if u_ans: html += f'<span class="slot-filled">{u_ans.pop(0)}</span>'
                else: html += f'<span class="slot-empty">口</span>'
        st.markdown(html + '</div>', unsafe_allow_html=True)

        # 🔄 功能鍵區域：強制在一行內流動
        st.markdown('<div class="flow-container ctrl-btn">', unsafe_allow_html=True)
        btn_cols = st.columns(len(st.session_state.shuf_idx) + 4) # 建立足夠的欄位防止換行
        
        # 放置功能鍵
        with btn_cols[0]:
            if st.button("🔄"): reset_state(); st.rerun()
        with btn_cols[1]:
            if st.button("⬅️"):
                if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        with btn_cols[2]:
            if st.button("⏮️") and st.session_state.q_idx > 0:
                st.session_state.q_idx -= 1; st.session_state.shuf_idx = []; reset_state(); st.rerun()
        with btn_cols[3]:
            if st.button("⏭️") and st.session_state.q_idx < len(quiz_list)-1:
                st.session_state.q_idx += 1; st.session_state.shuf_idx = []; reset_state(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.write("---")
        
        # 單字按鈕區：流動佈局
        st.write("點選單字：")
        st.markdown('<div class="flow-container">', unsafe_allow_html=True)
        for i, ridx in enumerate(st.session_state.shuf_idx):
            if ridx not in st.session_state.used_history:
                # 直接按順序使用剩下的 columns
                with btn_cols[i + 4]:
                    if st.button(words[ridx], key=f"btn_{ridx}"):
                        st.session_state.ans.append(words[ridx]); st.session_state.used_history.append(ridx); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.ans and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(words): st.session_state.is_correct = True; st.rerun()
                else: st.error("不對喔")

        if st.session_state.is_correct:
            st.success("正解！"); play_audio(ja_raw, auto=True)
            if st.button("下一題 ➡️", type="primary", use_container_width=True):
                st.session_state.q_idx += 1; st.session_state.shuf_idx = []; reset_state(); st.rerun()
    else:
        st.header("練習完成！")
        if st.button("🔄 重新開始", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
