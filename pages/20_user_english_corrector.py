# =============================================
# pages/20_user_english_corrector.py（英作文添削）
# =============================================

import streamlit as st
from firebase_admin import firestore
from english_corrector import show_essay_corrector

# --- ページ設定 ---
st.set_page_config(page_title="英作文添削", layout="centered")

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

member_id = st.session_state.get("member_id")

# --- Firestore クライアント（必要なら使用） ---
db = firestore.client()

# ===============================
# 📝 英作文添削ページ UI
# ===============================

st.title("📝 英作文添削")
st.markdown("以下の問題を解いて、英作文を送信してください。")

# --- 旧 main.py と同じ関数を使う ---
show_essay_corrector(member_id)

# ===============================
# 🔙 戻るボタン
# ===============================
st.markdown("---")
if st.button("⬅️ ホームへ戻る"):
    st.switch_page("pages/1_user_home.py")
