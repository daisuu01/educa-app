# =============================================
# pages/40_user_password_change.py（パスワード変更）
# =============================================

import streamlit as st
from firebase_utils import update_user_password
from firebase_admin import firestore

# --- ページ設定 ---
st.set_page_config(page_title="パスワード変更", layout="centered")

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


# ===============================
# 🔑 パスワード変更 UI
# ===============================

st.title("🔑 パスワード変更")

st.markdown("新しいパスワードを入力してください。")

new_pw = st.text_input("新しいパスワード", type="password", key="new_pw")
confirm_pw = st.text_input("新しいパスワード（確認）", type="password", key="confirm_pw")

if st.button("変更を保存", use_container_width=True):
    if not new_pw or not confirm_pw:
        st.warning("⚠ 両方の欄を入力してください。")
    elif new_pw != confirm_pw:
        st.error("❌ パスワードが一致しません。")
    else:
        update_user_password(member_id, new_pw)
        st.success("✅ パスワードを変更しました！")


# ===============================
# 🔙 戻る
# ===============================
st.markdown("---")
if st.button("⬅️ ホームへ戻る"):
    st.switch_page("pages/1_user_home.py")
