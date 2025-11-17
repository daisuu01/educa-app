# =============================================
# 10_ユーザー_英作文添削.py（ユーザー用 英作文添削ページ）
# =============================================

import streamlit as st
from firebase_utils import USERS
from english_corrector import show_essay_corrector

# =============================================
# 🔐 ログインチェック（未ログイン → main.pyへ）
# =============================================
if "login" not in st.session_state or not st.session_state["login"]:
    st.error("⚠️ ログインしてください。")
    st.stop()

if st.session_state["role"] != "student":
    st.error("⚠️ このページは生徒専用です。")
    st.stop()

member_id = st.session_state["member_id"]

# =============================================
# 🔙 戻るボタン
# =============================================
if st.button("⬅️ メニューに戻る", use_container_width=True):
    st.switch_page("main.py")

# =============================================
# 📝 英作文添削ページ本体
# =============================================
st.title("📝 英作文添削")

show_essay_corrector(member_id)

# =============================================
# 🔙 最下部の戻るボタン
# =============================================
st.markdown("<br><br><hr>", unsafe_allow_html=True)
if st.button("⬅️ 戻る（メニュー）", use_container_width=True, key="back_bottom"):
    st.switch_page("main.py")
