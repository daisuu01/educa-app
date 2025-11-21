# =============================================
# pages/1000_admin_menu.py（タブ方式：最安定バージョン）
# =============================================

import streamlit as st
from firebase_admin import firestore

from admin_chat import show_admin_chat
from admin_inbox import show_admin_inbox, count_unread_messages
from firebase_utils import fetch_all_users, import_students_from_excel_and_csv
from admin_schedule import show_schedule_main
from unread_guardian_list import show_unread_guardian_list

# ---- ページ設定 ----
st.set_page_config(page_title="管理者メニュー", layout="wide")

# ---- サイドバー完全非表示 ----
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

# ---- ログインチェック ----
if not st.session_state.get("login"):
    st.switch_page("main.py")

if st.session_state.get("role") != "admin":
    st.error("⚠ 管理者のみアクセスできます")
    st.stop()

member_id = st.session_state.get("member_id")

# --------------------------------------------
# 🎉 管理者メニュー（タブ表示）
# --------------------------------------------

st.title(f"📋 管理者メニュー（{member_id}）")
st.markdown("---")

# 🔥 未読数（リアルタイム）
unread = count_unread_messages()

# 🔥 タブ6つ
tabs = st.tabs([
    "👥 生徒登録",
    "📋 登録済みユーザー一覧",
    "💬 チャット管理",
    f"📥 受信ボックス（{unread}）",
    "⏰ 送信予約",
    "👀 保護者未読一覧"
])

# ------------------------
# 👥 生徒登録
# ------------------------
with tabs[0]:
    st.header("👥 生徒登録")
    excel_file = st.file_uploader("📘 Excel（名簿）", type=["xlsx"])
    csv_file = st.file_uploader("📄 CSV（初期PW）", type=["csv"])

    if excel_file and csv_file:
        st.info("処理中…")
        df = import_students_from_excel_and_csv(excel_file, csv_file)
        if len(df) > 0:
            st.success("Firestoreへ登録が完了しました！")
        else:
            st.warning("登録対象が見つかりませんでした。")
        st.dataframe(df, use_container_width=True)

# ------------------------
# 📋 登録済みユーザー一覧
# ------------------------
with tabs[1]:
    st.header("📋 登録済みユーザー一覧")
    st.dataframe(fetch_all_users(), use_container_width=True)

# ------------------------
# 💬 チャット管理
# ------------------------
with tabs[2]:
    st.header("💬 チャット管理")
    show_admin_chat()

# ------------------------
# 📥 受信BOX
# ------------------------
with tabs[3]:
    st.header("📥 受信ボックス")
    show_admin_inbox()

# ------------------------
# ⏰ 送信予約
# ------------------------
with tabs[4]:
    st.header("⏰ 送信予約")
    show_schedule_main()

# ------------------------
# 👀 保護者未読一覧
# ------------------------
with tabs[5]:
    st.header("👀 保護者未読一覧")
    show_unread_guardian_list()
