import streamlit as st
import pandas as pd
import random
import re

# 設定網頁標題
st.set_page_config(page_title="🇯🇵 日文助詞重組練習器", layout="wide")

# --- 1. 設定 Google Sheets 資訊 ---
SHEET_ID = "12ZgvpxKtxSjobZLR7MTbEnqMOqGbjTiO9dXJFmayFYA"
GID = "1337973082"
url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        COL_UNIT, COL_CH, COL_JA, COL_CN = "單元", "章節", "日文原文", "中文意譯"
        
        if not all(c in df.columns for c in [COL_UNIT, COL_CH, COL_JA, COL_CN]):
            st.error(f"❌ 欄位不符，目前：{list(df.columns)}")
            return None, None

        df[COL_UNIT] = df[COL_UNIT].astype(str).str.strip()
        df[COL_CH] = df[COL_CH].astype(str).str.strip()
        df = df.dropna(subset=[COL_JA, COL_CN])
        return df, {"unit": COL_UNIT, "ch": COL_CH, "ja": COL_JA, "cn": COL_CN}
    except Exception as e:
        st.error(f"❌ 讀取失敗：{e}"); return None, None

def word_splitter(text):
    """
    更精細的拆解邏輯：將助詞獨立切開
    """
    text = text.strip()
    # 定義要獨立切開的助詞清單
    particles = ['は', 'が', 'を', 'に', 'へ', 'と', 'も', 'で', 'の', 'から', 'まで']
    
    # 建立正則表達式：在助詞前後加上分隔符號
    # 用括號捕捉助詞，以便保留在 split 結果中
    pattern = f"({'|'.join(particles)}|、|。|！|？)"
    
    # 切分句子
    raw_tokens = re.split(pattern, text)
    
    # 過濾掉空字串並清理
    tokens = [t for t in raw_tokens if t and t.strip()]
    
    # 如果切出來太少（例如沒有助詞的短句），則每兩個字強拆
    if len(tokens) < 3:
        tokens = [text[i:i+2] for i in range(0, len(text), 2)]
        
    return tokens

def reset_state():
    st.session_state.q_idx = 0
    st.session_state.ans = []
    st.session_state.used_history = []
    st.session_state.shuf = []
    st.session_state.is_correct = False

if 'q_idx' not in st.session_state: reset_state()

df, cols = load_data()

if df is not None:
    st.sidebar.header("⚙️ 練習設定")
    unit_list = sorted(df[cols['unit']].unique())
    sel_unit = st.sidebar.selectbox("1. 選擇單元", unit_list)
    unit_df = df[df[cols['unit']] == sel_unit]
    ch_list = sorted(unit_df[cols['ch']].unique())
    sel_start_ch = st.sidebar.selectbox("2. 起始章節", ch_list)
    
    filtered_df = unit_df[unit_df[cols['ch']] >= sel_start_ch]
    
    if not filtered_df.empty:
        num_q = st.sidebar.slider("3. 練習題數", 1, len(filtered_df), min(10, len(filtered_df)))
        quiz_list = filtered_df.head(num_q).to_dict('records')

        if 'last_key' not in st.session_state or st.session_state.last_key != f"{sel_unit}-{sel_start_ch}-{num_q}":
            st.session_state.last_key = f"{sel_unit}-{sel_start_ch}-{num_q}"
            reset_state(); st.rerun()

        if st.sidebar.checkbox("📖 開啟預習模式"):
            for item in quiz_list:
                with st.expander(f"【{item[cols['ch']]}】{item[cols['cn']]}", expanded=True):
                    st.write(f"### {item[cols['ja']]}")
                    st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={item[cols['ja']]}")

        elif st.session_state.q_idx < len(quiz_list):
            q = quiz_list[st.session_state.q_idx]
            ja_raw = str(q[cols['ja']]).strip()
            
            if not st.session_state.shuf:
                tokens = word_splitter(ja_raw)
                random.shuffle(tokens)
                st.session_state.shuf = tokens

            st.title(f"問題 {st.session_state.q_idx + 1} / {len(quiz_list)}")
            st.info(f"💡 中文：{q[cols['cn']]}")

            res_str = "".join(st.session_state.ans)
            st.markdown(f'<div style="font-size:32px; color:#1e3a8a; background-color:#f0f9ff; padding:25px; border-radius:15px; border:2px solid #7dd3fc; min-height:100px; margin-bottom:20px; display: flex; align-items: center; flex-wrap: wrap;">{res_str if res_str else "請選取單字與助詞..."}</div>', unsafe_allow_html=True)

            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                if st.button("🔄 全部重填", use_container_width=True):
                    st.session_state.ans, st.session_state.used_history = [], []; st.rerun()
            with c2:
                if st.button("⬅️ 退回", use_container_width=True):
                    if st.session_state.used_history:
                        st.session_state.used_history.pop(); st.session_state.ans.pop(); st.rerun()
            with c3:
                if st.button("⏭️ 跳過", use_container_width=True):
                    st.session_state.q_idx += 1; reset_state(); st.rerun()

            st.write("---")
            # 隨機排布的單字與助詞按鈕
            btn_cols = st.columns(5) 
            for i, t in enumerate(st.session_state.shuf):
                if i not in st.session_state.used_history:
                    with btn_cols[i % 5]:
                        # 助詞按鈕給予不同的視覺暗示（例如更醒目）
                        if st.button(t, key=f"btn_{i}", use_container_width=True):
                            st.session_state.ans.append(t)
                            st.session_state.used_history.append(i)
                            st.rerun()

            if len(st.session_state.ans) > 0 and not st.session_state.is_correct:
                if st.button("🔍 檢查答案", type="primary", use_container_width=True):
                    if "".join(st.session_state.ans).replace(" ","") == ja_raw.replace(" ",""):
                        st.session_state.is_correct = True; st.rerun()
                    else: st.error("順序不對喔！檢查看看助詞是否放錯了？")

            if st.session_state.is_correct:
                st.success(f"🎊 正解！{ja_raw}")
                st.audio(f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ja&client=tw-ob&q={ja_raw}")
                if st.button("下一題 ➡️", type="primary", use_container_width=True):
                    st.session_state.q_idx += 1; reset_state(); st.rerun()
        else:
            st.header("🎊 練習成果回顧")
            st.balloons()
            if st.button("🔄 重新開始"): reset_state(); st.rerun()
    else:
        st.warning(f"⚠️ 篩選範圍內沒有資料。")
