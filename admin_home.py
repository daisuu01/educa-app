# =============================================
# admin_home.py（管理者メニュー完全版）
# =============================================

import streamlit as st
import firebase_admin
from firebase_admin import firestore

# --- Firestore / 認証は main.py で初期化済み ---
db = firestore.client()
USERS = db.collection("users")

# --- 必要モジュール ---
from firebase_utils import (
    import_students_from_excel_and_csv,
    fetch_all_users,
)
from admin_inbox import show_admin_inbox, count_unread_messages
from admin_chat import show_admin_chat
from admin_schedule import show_schedule_main
from unread_guardian_list import show_unread_guardian_list


# ===========================
# 🔐 ログイン前のアクセス防止
# ===========================
if not st.session_state.get("login"):
    st.error("⚠️ ログインが必要です。main.py からアクセスしてください。")
    st.stop()

if st.session_state.get("role") != "admin":
    st.error("⚠️ 管理者専用ページです。")
    st.stop()


# ===========================
# 🧭 サイドバー（管理者用）
# ===========================
st.sidebar.title("📋 管理者メニュー")

unread = count_unread_messages()
inbox_label = f"受信ボックス（{unread}）" if unread > 0 else "受信ボックス"

options = [
    "生徒登録",
    "登録済みユーザー一覧",
    "チャット管理",
    inbox_label,
    "送信予約",
    "保護者未読一覧",
]

current = st.session_state.get("admin_mode", "生徒登録")

if current.startswith("受信ボックス"):
    default_index = 3
else:
    default_index = ["生徒登録", "登録済みユーザー一覧", "チャット管理"].index(current) \
        if current in ["生徒登録", "登録済みユーザー一覧", "チャット管理"] else 0

selected_label = st.sidebar.radio("モードを選択してください", options, index=default_index)
mode = "受信ボックス" if selected_label.startswith("受信ボックス") else selected_label
st.session_state["admin_mode"] = mode


# =====================================
# 📂 生徒登録
# =====================================
if mode == "生徒登録":
    st.title("📘 生徒登録")
    excel_file = st.file_uploader("Excelファイル（生徒情報）", type=["xlsx"])
    csv_file = st.file_uploader("CSVファイル（初期PW対応表）", type=["csv"])

    if excel_file and csv_file:
        st.info("ファイル検証中 ...")
        result = import_students_from_excel_and_csv(excel_file, csv_file)

        if len(result) > 0:
            st.success("Firestore 登録が完了しました！")
            st.dataframe(result, use_container_width=True)
        else:
            st.warning("登録対象がありません。")


# =====================================
# 👥 登録済みユーザー一覧
# =====================================
elif mode == "登録済みユーザー一覧":
    st.title("👥 Firestore 登録済みユーザー一覧")
    df = fetch_all_users()
    st.dataframe(df, use_container_width=True)


# =====================================
# 💬 チャット管理
# =====================================
elif mode == "チャット管理":

    # 🔽 受信BOX → チャット自動遷移フラグ処理
    if st.session_state.get("just_opened_from_inbox", False):

        target_id = st.session_state.get("selected_student_id")

        if target_id:
            st.session_state["target_type"] = "個人"
            st.session_state["target_student_id"] = target_id

            st.session_state["just_opened_from_inbox"] = False
            st.session_state["admin_mode"] = "チャット管理"
            st.rerun()

    # 🔽 通常チャット画面
    selected_id = st.session_state.get("target_student_id")

    if selected_id:
        show_admin_chat(initial_student_id=selected_id)
    else:
        show_admin_chat()

    # フラグ除去
    if st.session_state.get("open_mode") == "admin_chat":
        st.session_state["open_mode"] = None


# =====================================
# 📥 受信ボックス
# =====================================
elif mode == "受信ボックス":
    show_admin_inbox()

    if st.session_state.get("just_opened_from_inbox", False):

        tgt = st.session_state.get("selected_student_id")
        if tgt:
            st.session_state["target_student_id"] = tgt
            st.session_state["target_type"] = "個人"
            st.session_state["admin_mode"] = "チャット管理"
            st.session_state["just_opened_from_inbox"] = False
            st.rerun()


# =====================================
# ⏰ 送信予約
# =====================================
elif mode == "送信予約":
    st.title("⏰ メッセージ送信予約")
    show_schedule_main()


# =====================================
# 👀 保護者未読一覧
# =====================================
elif mode == "保護者未読一覧":
    st.title("👀 保護者未読一覧")
    show_unread_guardian_list()


# =====================================
# 🚪 ログアウト
# =====================================
st.sidebar.markdown("---")
if st.sidebar.button("ログアウト"):
    st.session_state.clear()
    st.rerun()
