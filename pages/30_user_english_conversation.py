# =============================================
# pages/30_user_english_conversation.py（英会話トレーナー）
# =============================================

import streamlit as st
from firebase_admin import firestore
from english_conversation import show_english_conversation

# --- ページ設定 ---
st.set_page_config(page_title="英会話トレーナー", layout="centered")

# --- サイドバー完全非表示 ---
st.markdown("""
<style>
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stSidebarCollapsedControl"] { display: none !important; }

div[data-testid="stAppViewContainer"] > section:first-child {
    width: 100% !important;
    max-width: 100% !important;
    margin-left: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# --- ログインチェック ---
if not st.session_state.get("login"):
    st.switch_page("main.py")

# --- Firestore（必要なら利用） ---
db = firestore.client()

# ===============================
# 🎧 英会話トレーナー UI
# ===============================

st.title("🎧 英会話トレーナー")
st.markdown("AI講師と英会話練習ができます。")

# --- 旧 main.py の関数をそのまま使用 ---
show_english_conversation()

# ===============================
# 🔙 戻るボタン
# ===============================
st.markdown("---")
if st.button("⬅️ ホームへ戻る"):
    st.switch_page("pages/1_user_home.py")
