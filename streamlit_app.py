import streamlit as st
import pandas as pd
import random
import re

st.set_page_config(page_title="日文重組練習 - 語法強化版", layout="wide")

# 1. 資料讀取 (請修改為您的日文 Google Sheet ID 與 GID)
SHEET_ID = "1zVUNGboZALvK3val1RSbCQvEESLRSNEulqpNSzsPJ14"
GID = "176577556"
url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        # 尋找對應欄位 (模糊比對)
        def find_col(keywords):
            for col in df.columns:
                if any(k in col for k in keywords): return col
            return None
        
        col_map = {
            'year': find_col(['年度', 'Year']),
            'chapter': find_col(['章節', '冊', '課', 'Chapter']),
            'ja': find_col(['日文', '原文', '單字', 'Japanese']),
            'cn': find_col(['中文', '意譯', '翻譯', 'Chinese']),
            'id': find_col(['編號', '句', 'ID'])
        }
        
        # 轉換數值型態
        for key in ['year', 'chapter', 'id']:
            if col_map[key]:
                df[col_map[key]] = pd.to_numeric(df[col_map[key]], errors='coerce')
        
        return df.dropna(subset=[col_map['ja'], col_map['cn']]), col_map
    except Exception as e:
        st.error(f"資料讀取失敗: {e}")
        return None, None

def reset_all_state():
    st.session_state.q_idx = 0
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.history = {}
    st.session_state.finished = False
    st.session_state.is_correct = False
    st.session_state.has_started_quiz = False
    st.session_state.check_clicked = False

if 'q_idx' not in st.session_state: reset_all_state()

df, col_map = load_data()

if df is not None:
    # --- 側邊欄：篩選系統 ---
    st.sidebar.header("⚙️ 練習範圍設定")
    
    # 年度/章節篩選 (動態產生)
    years = sorted(df[col_map['year']].dropna().unique().astype(int).tolist()) if col_map['year'] else [0]
    sel_y = st.sidebar.selectbox("1. 選擇年度", years)
    df_filtered = df[df[col_map['year']] == sel_y] if col_map['year'] else df
    
    chapters = sorted(df_filtered[col_map['chapter']].dropna().unique().astype(int).tolist()) if col_map['chapter'] else [0]
    sel_c = st.sidebar.selectbox("2. 選擇章節/冊編號", chapters)
    base_df = df_filtered[df_filtered[col_map['chapter']] == sel_c]
    
    if not base_df.empty:
        col_id = col_map['id'] if col_map['id'] else base_df.columns[0]
        min_id = int(base_df[col_id].min())
        max_id = int(base_df[col_id].max())
        start_id = st.sidebar.number_input(f"3. 起始編號", min_id, max_id, min_id)
        
        filtered_df = base_df[base_df[col_id] >= start_id].sort_values(col_id)
        total_available = len(filtered_df)
        num_q = st.sidebar.slider("4. 練習題數", 1, total_available, min(10, total_available))
        quiz_list = filtered_df.head(num_q).to_dict('records')

        # 重置判斷
        key = f"{sel_y}-{sel_c}-{start_id}-{num_q}"
        if 'last_k' not in st.session_state or st.session_state.last_k != key:
            st.session_state.last_k = key
            reset_all_state()
            st.rerun()

        # 模式切換
        is_study_mode = st.sidebar.checkbox("📖 開啟預習模式", value=False)

        if is_study_mode:
            st.header(f"📖 第 {sel_c} 章 預習清單")
            for item in quiz_list:
                with st.expander(f"{item[col_map['cn']]}", expanded=True):
                    st.write(f"### {item[col_map['ja']]}")
                    t_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={item[col_map['ja']]}"
                    st.audio(t_url)

        # --- 測驗主畫面 ---
        elif not st.session_state.finished and st.session_state.q_idx < len(quiz_list):
            q = quiz_list[st.session_state.q_idx]
            ja_raw = str(q[col_map['ja']]).strip()
            
            # 日文分詞邏輯：按標點符號或長度切分 (可視需求調整)
            if not st.session_state.shuf:
                # 簡單分詞：按句點、逗點、或每隔3-4個字切分，並打亂
                tokens = re.findall(r'[^、。！？]+[、。！？]?', ja_raw)
                if len(tokens) < 3: # 句子太短則改用字元切分
                    tokens = [ja_raw[i:i+2] for i in range(0, len(ja_raw), 2)]
                random.shuffle(tokens)
                st.session_state.shuf = tokens

            st.title(f"問題 {st.session_state.q_idx + 1} / {len(quiz_list)}")
            st.info(f"💡 中文：{q[col_map['cn']]}")

            # 拼湊顯示區
            st.write("### 拼湊結果：")
            res_str = "".join(st.session_state.ans)
            st.markdown(f'''<div style="font-size:28px; color:#b91c1c; background-color:#fff1f1; padding:20px; 
                        border-radius:12px; border:2px dashed #f87171; min-height:80px;">
                        {res_str if res_str else "請點選下方的日文詞組..."}</div>''', unsafe_allow_html=True)

            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                if st.button("🔄 全部重填", use_container_width=True):
                    st.session_state.ans, st.session_state.used_history, st.session_state.check_clicked = [], [], False
                    st.rerun()
            with c2:
                if st.button("⬅️ 退回一步", use_container_width=True):
                    if st.session_state.used_history:
                        st.session_state.used_history.pop(); st.session_state.ans.pop()
                        st.session_state.check_clicked = False
                        st.rerun()
            with c3:
                if st.button("⏭️ 跳過此題", use_container_width=True):
                    st.session_state.history[st.session_state.q_idx] = {"內容": ja_raw, "狀態": "❌ 跳過"}
                    st.session_state.q_idx += 1
                    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct, st.session_state.check_clicked = [], [], [], False, False
                    st.rerun()

            st.write("---")
            # 按鈕選單
            if not st.session_state.is_correct:
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
                    u_ans = "".join(st.session_state.ans).replace(" ","")
                    t_ans = ja_raw.replace(" ","")
                    if u_ans == t_ans:
                        st.session_state.is_correct = True
                        st.session_state.history[st.session_state.q_idx] = {"內容": ja_raw, "狀態": "✅ 正確"}
                        st.rerun()
                    else:
                        st.error("順序不對喔，再檢查一下助詞！")

            if st.session_state.is_correct:
                st.success(f"正解！✨ {ja_raw}")
                st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={ja_raw}")
                if st.button("下一題 Next ➡️", type="primary", use_container_width=True):
                    st.session_state.q_idx += 1
                    st.session_state.ans, st.session_state.used_history, st.session_state.shuf, st.session_state.is_correct, st.session_state.check_clicked = [], [], [], False, False
                    st.rerun()

        else:
            st.header("🎊 練習成果回顧")
            if st.session_state.history:
                res_df = pd.DataFrame.from_dict(st.session_state.history, orient='index')
                st.table(res_df)
            st.button("🔄 重新開始練習", on_click=reset_all_state)
    else:
        st.warning("在此範圍下找不到題目，請重新檢查篩選條件。")
