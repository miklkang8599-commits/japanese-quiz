import streamlit as st
import pandas as pd
import random
import re
import requests
import base64
import urllib.parse

# ==========================================
# 🌟 程式特色：手機端彈性流動排版 (Flex Flow Fix)
# ==========================================
# 1. 【Flexbox 流動按鈕】：不再依賴 st.columns，強制按鈕橫向排隊，自動換行，長短自適應。
# 2. 【側邊欄修復】：修正 CSS 衝突，確保左上角選單按鈕 (>) 永遠可見。
# 3. 【Base64 強效音訊】：徹底解決 iPhone 播放器變灰色 0:00 問題。
# 4. 【空間極致壓縮】：移除頂部空白，題目與答題框置頂，減少滑動。
# ==========================================

st.set_page_config(page_title="🇯🇵 日文重組", layout="wide")

# 強力 CSS：徹底破解手機端垂直堆疊限制
st.markdown("""
    <style>
    /* 1. 基礎空間：移除頂部空白，但不影響選單按鈕 */
    .block-container { padding: 3rem 0.5rem 1rem !important; }
    [data-testid="stHeader"] { background: rgba(255,255,255,0.5); }
    
    /* 2. 答題區 */
    .res-box {
        font-size: 18px; color: #1e40af; background-color: #f0f9ff; 
        padding: 8px; border-radius: 8px; border: 1px solid #bae6fd; 
        min-height: 45px; margin-bottom: 8px; line-height: 1.5;
        display: flex; flex-wrap: wrap; align-items: center;
    }
    .slot-empty { color: #cbd5e1; border-bottom: 2px solid #cbd5e1; margin: 0 3px; min-width: 20px; text-align: center; }
    .slot-filled { color: #1e40af; border-bottom: 2px solid #3b82f6; margin: 0 3px; font-weight: bold; }
    .punc-fixed { color: #64748b; font-weight: bold; font-size: 18px; padding: 0 2px; }

    /* 3. 【核心修正】功能鍵與單字按鈕：強制橫向流動 */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important; /* 關鍵：允許換行 */
        align-items: center !important;
        gap: 8px !important;
    }
    
    /* 針對按鈕容器：取消固定寬度 */
    div[data-testid="column"] {
        flex: 0 1 auto !important; /* 關鍵：寬度隨內容伸縮 */
        min-width: 0px !important;
    }

    /* 針對按鈕本身：長短自適應 */
    div.stButton > button {
        width: auto !important;
        padding: 0 12px !important;
        height: 2.4em !important;
        font-size: 15px !important;
        white-space: nowrap !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Base64 語音處理 ---
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
        st.markdown(f'<audio controls {autoplay} style="width:100%; height:35px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)

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
    sel_unit = st.sidebar.selectbox("1. 單元", u_list)
    u_df = df[df[cols['unit']] == sel_unit]
    sel_ch = st.sidebar.selectbox("2. 章節", sorted(u_df[cols['ch']].unique().tolist()))
    quiz_list = u_df[u_df[cols['ch']] >= sel_ch].head(5).to_dict('records')

    # 同步重置
    current_key = f"{sel_unit}-{sel_ch}"
    if 'sync_key' not in st.session_state or st.session_state.sync_key != current_key:
        st.session_state.sync_key = current_key
        st.session_state.q_idx = 0; reset_state(); st.rerun()

    # 主畫面
    if st.sidebar.checkbox("📖 預習模式"):
        for item in quiz_list:
            ja = str(item[cols['ja']]).strip()
            st.info(f"**{item[cols['cn']]}**\n\n{ja}")
            play_audio(ja)
    
    elif st.session_state.q_idx < len(quiz_list):
        q = quiz_list[st.session_state.q_idx]
        ja_raw = str(q[cols['ja']]).strip()
        all_t = unified_parser(ja_raw)
        words = [t for t in all_t if t not in ['、', '。', '！', '？']]
        
        if 'shuf_idx' not in st.session_state or len(st.session_state.shuf_idx) != len(words):
            st.session_state.shuf_idx = list(range(len(words))); random.shuffle(st.session_state.shuf_idx)

        # 頂部顯示
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

        # 4. 【重點】功能鍵與按鈕合併成流動區域
        # 使用多個 st.columns(1) 的組合來達成 Flexbox 效果
        c_ctrl = st.columns([1,1,1,1])
        with c_ctrl[0]: 
            if st.button("🔄"): reset_state(); st.rerun()
        with c_ctrl[1]:
            if st.button("⬅️"):
                if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
        with c_ctrl[2]:
            if st.button("⏮️") and st.session_state.q_idx > 0:
                st.session_state.q_idx -= 1; st.session_state.shuf_idx = []; reset_state(); st.rerun()
        with c_ctrl[3]:
            if st.button("⏭️") and st.session_state.q_idx < len(quiz_list)-1:
                st.session_state.q_idx += 1; st.session_state.shuf_idx = []; reset_state(); st.rerun()

        st.write("---")
        
        # 單字按鈕區：這裡使用單欄並依賴 CSS 的 flex-wrap
        # 建立一組虛擬 columns，CSS 會強迫它們在手機上橫向排列
        word_cols = st.columns(len(st.session_state.shuf_idx))
        for i, ridx in enumerate(st.session_state.shuf_idx):
            if ridx not in st.session_state.used_history:
                with word_cols[i]:
                    if st.button(words[ridx], key=f"btn_{ridx}"):
                        st.session_state.ans.append(words[ridx])
                        st.session_state.used_history.append(ridx)
                        st.rerun()

        if st.session_state.ans and not st.session_state.is_correct:
            if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                if "".join(st.session_state.ans) == "".join(words):
                    st.session_state.is_correct = True; st.rerun()
                else: st.error("不對喔")

        if st.session_state.is_correct:
            st.success("正解！"); play_audio(ja_raw, auto=True)
            if st.button("下一題 ➡️", type="primary", use_container_width=True):
                st.session_state.q_idx += 1; st.session_state.shuf_idx = []; reset_state(); st.rerun()
    else:
        st.header("練習完成！")
        if st.button("🔄 重新開始", type="primary", use_container_width=True): 
            st.session_state.q_idx = 0; reset_state(); st.rerun()
