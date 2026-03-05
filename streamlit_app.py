import streamlit as st
import pandas as pd
import random
import re

# 設定網頁標題
st.set_page_config(page_title="🇯🇵 日文重組練習器", layout="wide")

# --- 1. 設定 Google Sheets 資訊 ---
SHEET_ID = "12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA"
GID = "1337973082"
url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        
        COL_UNIT = "單元"
        COL_CH = "章節"
        COL_JA = "日文原文"
        COL_CN = "中文意譯"
        
        required = [COL_UNIT, COL_CH, COL_JA, COL_CN]
        if not all(c in df.columns for c in required):
            st.error(f"❌ 找不到欄位！目前欄位：{list(df.columns)}")
            return None, None

        # --- 關鍵修正：不強制轉數字，保留原始格式 ---
        df[COL_UNIT] = df[COL_UNIT].astype(str).str.strip()
        df[COL_CH] = df[COL_CH].astype(str).str.strip()
        
        # 過濾空行
        df = df.dropna(subset=[COL_JA, COL_CN])
        
        return df, {"unit": COL_UNIT, "ch": COL_CH, "ja": COL_JA, "cn": COL_CN}
    except Exception as e:
        st.error(f"❌ 讀取失敗：{e}")
        return None, None

def reset_state():
    st.session_state.q_idx = 0
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

if 'q_idx' not in st.session_state:
    reset_state()

df, cols = load_data()

if df is not None:
    # --- 側邊欄篩選 ---
    st.sidebar.header("⚙️ 練習設定")
    
    # 1. 選擇單元 (改為字串排序)
    unit_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", unit_list)
    
    # 2. 選擇起始章節
    unit_df = df[df[cols['unit']] == sel_unit]
    ch_list = sorted(unit_df[cols['ch']].unique())
    sel_start_ch = st.sidebar.selectbox("2. 起始章節 (含此章以後)", ch_list)
    
    # 過濾範圍：利用字串排序特性過濾「大於等於」所選編號的章節
    filtered_df = unit_df[unit_df[cols['ch']] >= sel_start_ch]
    
    if not filtered_df.empty:
        # 3. 題數
        num_q = st.sidebar.slider("3. 練習題數", 1, len(filtered_df), min(10, len(filtered_df)))
        quiz_list = filtered_df.head(num_q).to_dict('records')

        cur_key = f"{sel_unit}-{sel_start_ch}-{num_q}"
        if 'last_key' not in st.session_state or st.session_state.last_key != cur_key:
            st.session_state.last_key = cur_key
            reset_state()
            st.rerun()

        is_study = st.sidebar.checkbox("📖 開啟預習模式")

        if is_study:
            st.header(f"📖 預習：{sel_unit} (自 {sel_start_ch} 起)")
            for item in quiz_list:
                with st.expander(f"【{item[cols['ch']]}】{item[cols['cn']]}", expanded=True):
                    st.write(f"### {item[cols['ja']]}")
                    st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={item[cols['ja']]}")

        # --- 測驗主畫面 ---
        elif st.session_state.q_idx < len(quiz_list):
            q = quiz_list[st.session_state.q_idx]
            ja_raw = str(q[cols['ja']]).strip()
            
            if not st.session_state.shuf:
                # 強化拆分：標點符號、或每3個字
                tokens = re.findall(r'[^、。！？]+[、。！？]?', ja_raw)
                if len(tokens) < 2:
                    tokens = [ja_raw[i:i+3] for i in range(0, len(ja_raw), 3)]
                random.shuffle(tokens)
                st.session_state.shuf = tokens

            st.title(f"問題 {st.session_state.q_idx + 1} / {len(quiz_list)}")
            st.info(f"💡 中文意思：{q[cols['cn']]}")

            res_str = "".join(st.session_state.ans)
            st.markdown(f'<div style="font-size:28px; color:#1e3a8a; background-color:#f0f9ff; padding:20px; border-radius:12px; border:2px dashed #7dd3fc; min-height:80px; margin-bottom:20px;">{res_str if res_str else "請選下方的日文組塊..."}</div>', unsafe_allow_html=True)

            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                if st.button("🔄 全部重填"): st.session_state.ans, st.session_state.used_history = [], []; st.rerun()
            with c2:
                if st.button("⬅️ 退回"):
                    if st.session_state.used_history: st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
            with c3:
                if st.button("⏭️ 跳過"): st.session_state.q_idx += 1; reset_state(); st.rerun()

            st.write("---")
            btn_cols = st.columns(5)
            for i, t in enumerate(st.session_state.shuf):
                if i not in st.session_state.used_history:
                    with btn_cols[i % 5]:
                        if st.button(t, key=f"btn_{i}", use_container_width=True):
                            st.session_state.ans.append(t); st.session_state.used_history.append(i); st.rerun()

            if len(st.session_state.ans) > 0 and not st.session_state.is_correct:
                if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                    if "".join(st.session_state.ans) == ja_raw.replace(" ",""):
                        st.session_state.is_correct = True; st.rerun()
                    else: st.error("順序不對喔！")

            if st.session_state.is_correct:
                st.success(f"🎊 正解！{ja_raw}")
                st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={ja_raw}")
                if st.button("下一題 ➡️", type="primary"):
                    st.session_state.q_idx += 1; reset_state(); st.rerun()
        else:
            st.header("🎊 練習成果回顧")
            st.balloons()
            if st.button("🔄 重新開始"): reset_state(); st.rerun()
    else:
        st.warning(f"⚠️ 篩選範圍內沒有資料。目前選定的單元是 {sel_unit}。")
