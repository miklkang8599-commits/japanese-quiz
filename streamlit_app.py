import streamlit as st
import pandas as pd
import random
import re

st.set_page_config(page_title="日文重組練習器", layout="wide")

# 1. 設定你的 Google Sheets 資訊
SHEET_ID = "1zVUNGboZALvK3val1RSbCQvEESLRSNEulqpNSzsPJ14" 
GID = "176577556" 
url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        
        # --- 精準對位你的欄位名稱 ---
        COL_JA = "日文原文/單字"
        COL_CN = "中文意譯"
        COL_CH = "章節"
        
        # 防呆：如果真的找不到精準名稱，就列出所有欄位讓你知道
        if COL_JA not in df.columns:
            st.error(f"找不到欄位 '{COL_JA}'，目前表中的欄位有：{list(df.columns)}")
            return None, None

        # 轉換章節為數字以便排序
        df[COL_CH] = pd.to_numeric(df[COL_CH], errors='coerce')
        
        # 回傳資料與欄位對照表
        col_map = {'ja': COL_JA, 'cn': COL_CN, 'chapter': COL_CH}
        return df.dropna(subset=[COL_JA, COL_CN]), col_map
    except Exception as e:
        st.error(f"資料讀取失敗，請檢查 Google Sheets 權限或 ID。錯誤訊息：{e}")
        return None, None

def reset_all_state():
    st.session_state.q_idx = 0
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

if 'q_idx' not in st.session_state: reset_all_state()

df, col_map = load_data()

if df is not None:
    st.sidebar.header("⚙️ 練習範圍設定")
    
    # 章節篩選
    chapters = sorted(df[col_map['chapter']].dropna().unique().astype(int).tolist())
    sel_c = st.sidebar.selectbox("1. 選擇章節", chapters)
    
    # 根據章節過濾
    base_df = df[df[col_map['chapter']] == sel_c]
    
    if not base_df.empty:
        total_available = len(base_df)
        num_q = st.sidebar.slider("2. 練習題數", 1, total_available, min(10, total_available))
        quiz_list = base_df.head(num_q).to_dict('records')

        # 只要切換章節或題數就重置
        key = f"{sel_c}-{num_q}"
        if 'last_k' not in st.session_state or st.session_state.last_k != key:
            st.session_state.last_k = key
            reset_all_state()
            st.rerun()

        # 預習模式
        if st.sidebar.checkbox("📖 開啟預習模式", value=False):
            st.header(f"📖 第 {sel_c} 章 預習清單")
            for item in quiz_list:
                with st.expander(f"{item[col_map['cn']]}", expanded=True):
                    st.write(f"### {item[col_map['ja']]}")
                    t_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={item[col_map['ja']]}"
                    st.audio(t_url)

        # --- 測驗主畫面 ---
        elif st.session_state.q_idx < len(quiz_list):
            q = quiz_list[st.session_state.q_idx]
            ja_raw = str(q[col_map['ja']]).strip()
            
            # 打亂詞組
            if not st.session_state.shuf:
                # 優先按標點符號拆，沒標點就每 3 字拆一次
                tokens = re.findall(r'[^、。！？]+[、。！？]?', ja_raw)
                if len(tokens) < 2:
                    tokens = [ja_raw[i:i+3] for i in range(0, len(ja_raw), 3)]
                random.shuffle(tokens)
                st.session_state.shuf = tokens

            st.title(f"問題 {st.session_state.q_idx + 1} / {len(quiz_list)}")
            st.info(f"💡 中文：{q[col_map['cn']]}")

            # 拼湊顯示區
            res_str = "".join(st.session_state.ans)
            st.markdown(f'<div style="font-size:28px; color:#b91c1c; background-color:#fff1f1; padding:20px; border-radius:12px; border:2px dashed #f87171; min-height:80px;">{res_str if res_str else "請點選下方的日文詞組..."}</div>', unsafe_allow_html=True)

            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                if st.button("🔄 全部重填", use_container_width=True):
                    st.session_state.ans, st.session_state.used_history = [], []
                    st.rerun()
            with c2:
                if st.button("⬅️ 退回一步", use_container_width=True):
                    if st.session_state.used_history:
                        st.session_state.used_history.pop(); st.session_state.ans.pop()
                        st.rerun()
            with c3:
                if st.button("⏭️ 跳過此題", use_container_width=True):
                    st.session_state.q_idx += 1
                    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct = [], [], [], False
                    st.rerun()

            st.write("---")
            # 按鈕選單
            cols = st.columns(5)
            for i, t in enumerate(st.session_state.shuf):
                if i not in st.session_state.used_history:
                    with cols[i % 5]:
                        if st.button(t, key=f"btn_{i}", use_container_width=True):
                            st.session_state.ans.append(t)
                            st.session_state.used_history.append(i)
                            st.rerun()

            # 檢查答案
            if len(st.session_state.ans) > 0 and not st.session_state.is_correct:
                if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                    if "".join(st.session_state.ans) == ja_raw.replace(" ",""):
                        st.session_state.is_correct = True
                        st.rerun()
                    else:
                        st.error("順序不對喔！")

            if st.session_state.is_correct:
                st.success(f"正解！✨ {ja_raw}")
                st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={ja_raw}")
                if st.button("下一題 Next ➡️", type="primary", use_container_width=True):
                    st.session_state.q_idx += 1
                    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct = [], [], [], False
                    st.rerun()
        else:
            st.header("🎊 練習成果回顧")
            st.balloons()
            st.button("🔄 重新開始練習", on_click=reset_all_state)
