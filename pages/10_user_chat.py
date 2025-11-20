# =============================================
# pages/10_ユーザー_チャット.py（生徒チャットページ）
# =============================================

import streamlit as st
from firebase_admin import firestore
from user_chat import show_chat_page, get_user_meta

# --- ページ設定 ---
st.set_page_config(page_title="チャット", layout="centered")

# --- ログインチェック ---
if not st.session_state.get("login"):
    st.switch_page("main.py")

member_id = st.session_state.get("member_id")

# --- Firebase ---
db = firestore.client()

# --- ユーザーの学年・クラス取得 ---
grade, class_name = get_user_meta(member_id)
grade = grade or "未設定"
class_name = class_name or "未設定"

# --- UI ---
st.title("💬 チャット")
st.markdown("管理者とのチャットルームです。")

# --- チャット本体（旧mainのまま） ---
show_chat_page(member_id, grade, class_name)

# --- 戻る ---
st.markdown("---")
if st.button("⬅️ ホームへ戻る"):
    st.switch_page("pages/1_user_home.py")
