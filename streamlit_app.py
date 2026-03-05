import streamlit as st
import pandas as pd
import random
import re

# 強制設定網頁標題
st.set_page_config(page_title="🇯🇵 日文重組練習器", layout="wide")

# --- 1. 設定 Google Sheets 資訊 (精確填入你提供的 GID) ---
SHEET_ID = "1zVUNGboZALvK3val1RSbCQvEESLRSNEulqpNSzsPJ14"
GID = "1337973082" 
# 組合 CSV 匯出連結
url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60)
def load_data():
    try:
        # 讀取資料
        df = pd.read_csv(url)
        # 清除所有欄位名稱的前後空格
        df.columns = [str(c).strip() for c in df.columns]
        
        # 定義正確的欄位名稱
        COL_UNIT = "單元"
        COL_CH = "章節"
        COL_JA = "日文原文/單字"
        COL_CN = "中文意譯"
        
        # 檢查欄位是否存在
        for col in [COL_UNIT, COL_CH, COL_JA, COL_CN]:
            if col not in df.columns:
                st.error(f"❌ 找不到欄位：'{col}'")
                st.info(f"目前的欄位有：{list(df.columns)}")
                return None, None

        # 數值轉換
        df[COL_UNIT] = pd.to_numeric(df[COL_UNIT], errors='coerce')
        df[COL_CH] = pd.to_numeric(df[COL_CH], errors='coerce')
        
        return df.dropna(subset=[COL_JA, COL_CN]), {"unit": COL_UNIT, "ch": COL_CH, "ja": COL_JA, "cn": COL_CN}
    except Exception as e:
        st.error(f"❌ 無法連線至 Google Sheets：{e}")
        return None, None

def reset_state():
    st.session_state.q_idx = 0
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

if 'q_idx' not in st.session_state: reset_state()

df, cols = load_data()

if df is not None:
    # --- 側邊欄篩選器 ---
    st.sidebar.header("⚙️ 練習範圍設定")
    
    # 1. 單元篩選
    unit_list = sorted(df[cols['unit']].dropna().unique().astype(int).tolist())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", unit_list)
    
    # 2. 起始章節 (連動單元)
    unit_df = df[df[cols['unit']] == sel_unit]
    ch_list = sorted(unit_df[cols['ch']].dropna().unique().astype(int).tolist())
    sel_start_ch = st.sidebar.selectbox("2. 起始章節", ch_list)
    
    # 過濾出符合條件的內容 (大於等於起始章節)
    filtered_df = unit_df[unit_df[cols['ch']] >= sel_start_ch]
    
    if not filtered_df.empty:
        # 3. 練習題數
        total_available = len(filtered_df)
        num_q = st.sidebar.slider("3. 練習題數", 1, total_available, min(10, total_available))
        quiz_list = filtered_df.head(num_q).to_dict('records')

        # 檢查是否需要重置
        current_key = f"{sel_unit}-{sel_start_ch}-{num_q}"
        if 'last_key' not in st.session_state or st.session_state.last_key != current_key:
            st.session_state.last_key = current_key
            reset_state()
            st.rerun()

        # 模式切換
        if st.sidebar.checkbox("📖 開啟預習模式", value=False):
            st.header(f"📖 單元 {sel_unit} (第 {sel_start_ch} 章起) 預習中")
            for item in quiz_list:
                with st.expander(f"【章節 {int(item[cols['ch']])}】{item[cols['cn']]}", expanded=True):
                    ja_text = item[cols['ja']]
                    st.write(f"### {ja_text}")
                    st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={ja_text}")

        # --- 測驗主畫面 ---
        elif st.session_state.q_idx < len(quiz_list):
            q = quiz_list[st.session_state.q_idx]
            ja_raw = str(q[cols['ja']]).strip()
            
            if not st.session_state.shuf:
                # 日文分詞邏輯
                tokens = re.findall(r'[^、。！？]+[、。！？]?', ja_raw)
                if len(tokens) < 2:
                    tokens = [ja_raw[i:i+3] for i in range(0, len(ja_raw), 3)]
                random.shuffle(tokens)
                st.session_state.shuf = tokens

            st.title(f"Q {st.session_state.q_idx + 1} / {len(quiz_list)}")
            st.info(f"💡 中文意思：{q[cols['cn']]}")

            res_str = "".join(st.session_state.ans)
            st.markdown(f'<div style="font-size:28px; color:#1e3a8a; background-color:#f0f9ff; padding:20px; border-radius:12px; border:2px dashed #7dd3fc; min-height:80px; margin-bottom:20px;">{res_str if res_str else "請點選下方的日文組塊..."}</div>', unsafe_allow_html=True)

            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                if st.button("🔄 重填", use_container_width=True):
                    st.session_state.ans, st.session_state.used_history = [], []
                    st.rerun()
            with c2:
                if st.button("⬅️ 退回", use_container_width=True):
                    if st.session_state.used_history:
                        st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
            with c3:
                if st.button("⏭️ 跳過", use_container_width=True):
                    st.session_state.q_idx += 1; reset_state(); st.rerun()

            st.write("---")
            cols_btn = st.columns(5)
            for i, t in enumerate(st.session_state.shuf):
                if i not in st.session_state.used_history:
                    with cols_btn[i % 5]:
                        if st.button(t, key=f"btn_{i}", use_container_width=True):
                            st.session_state.ans.append(t); st.session_state.used_history.append(i); st.rerun()

            if len(st.session_state.ans) > 0 and not st.session_state.is_correct:
                if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                    if "".join(st.session_state.ans) == ja_raw.replace(" ",""):
                        st.session_state.is_correct = True; st.rerun()
                    else:
                        st.error("順序不對喔！")

            if st.session_state.is_correct:
                st.success(f"🎊 正解：{ja_raw}")
                st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={ja_raw}")
                if st.button("下一題 ➡️", type="primary", use_container_width=True):
                    st.session_state.q_idx += 1; reset_state(); st.rerun()
        else:
            st.header("🎊 練習完成！")
            st.balloons()
            if st.button("🔄 重新開始練習", type="primary"):
                reset_state(); st.rerun()
