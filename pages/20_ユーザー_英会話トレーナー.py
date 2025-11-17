import streamlit as st
from english_conversation import show_english_conversation

role = st.session_state.get("role", None)

# ---- 管理者以外はサイドバー非表示 ----
if role != "admin":
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {display: none !important;}
    div[data-testid="stSidebarNav"] {display: none !important;}
    </style>
    """, unsafe_allow_html=True)
    
# ==============================
# 🎧 ユーザー：英会話トレーナー
# ==============================

st.set_page_config(page_title="英会話トレーナー", layout="centered")

st.title("🎧 英会話トレーナー")
st.markdown("音声で練習できる英会話トレーニングページです。")

# ==============================
# 🔙 戻るボタン
# ==============================
if st.button("⬅️ メニューに戻る"):
    st.session_state["student_page"] = "menu"
    st.rerun()

# ==============================
# 🎤 メイン処理（既存関数呼び出し）
# ==============================
show_english_conversation()
