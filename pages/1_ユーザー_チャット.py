# =============================================
# 1_ユーザー_チャット.py（ユーザー専用チャットページ）
# =============================================

import streamlit as st
import firebase_admin
from firebase_admin import firestore
from firebase_utils import USERS
from user_chat import show_chat_page, get_user_meta

# --- Firebase クライアント ---
db = firestore.client()

# =============================================
# 🔐 ログイン確認（未ログイン → main.py に戻す）
# =============================================
if "login" not in st.session_state or not st.session_state["login"]:
    st.error("⚠️ ログインしてください。")
    st.stop()

if st.session_state["role"] != "student":
    st.error("⚠️ このページは生徒専用です。")
    st.stop()

member_id = st.session_state["member_id"]

# =============================================
# 🔹 学年・クラス取得
# =============================================
grade, class_name = get_user_meta(member_id)
grade = grade or "未設定"
class_name = class_name or "未設定"

# =============================================
# 🔙 戻るボタン
# =============================================
if st.button("⬅️ メニューに戻る", use_container_width=True):
    st.switch_page("main.py")

# =============================================
# 💬 チャット本体
# =============================================
st.title("💬 チャット")

show_chat_page(member_id, grade, class_name)

# =============================================
# 🔙 最下部の戻るボタン
# =============================================
st.markdown("<br><br><hr>", unsafe_allow_html=True)
if st.button("⬅️ 戻る（メニュー）", use_container_width=True, key="back_bottom"):
    st.switch_page("main.py")
