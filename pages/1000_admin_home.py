# =============================================
# pages/1000_admin_home.py（管理者ホーム）
# =============================================

import streamlit as st
from firebase_admin import firestore
from admin_chat import show_admin_chat
from admin_inbox import show_admin_inbox, count_unread_messages
from firebase_utils import fetch_all_users, import_students_from_excel_and_csv
from admin_schedule import show_schedule_main
from unread_guardian_list import show_unread_guardian_list

# --- ページ設定 ---
st.set_page_config(page_title="管理者ホーム", layout="centered")

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

if st.session_state.get("role") != "admin":
    st.error("⚠️ 管理者のみアクセス可能です。")
    st.stop()

db = firestore.client()


# ============================
# 📌 サブページ判定
# ============================

if "admin_page" not in st.session_state:
    st.session_state["admin_page"] = "menu"

page = st.session_state["admin_page"]


# ============================
# 🎛️ メニュー（ホーム画面）
# ============================
if page == "menu":

    st.title("🛠 管理者メニュー")
    st.markdown("利用する機能を選択してください。")

    unread = count_unread_messages()
    inbox_label = f"📥 受信ボックス（{unread}）" if unread > 0 else "📥 受信ボックス"

    col1, col2 = st.columns(2)

    with col1:
        if st.button("👥 生徒登録", use_container_width=True):
            st.session_state["admin_page"] = "register"
            st.rerun()

        if st.button("💬 チャット管理", use_container_width=True):
            st.session_state["admin_page"] = "chat"
            st.rerun()

        if st.button("📋 登録済みユーザー一覧", use_container_width=True):
            st.session_state["admin_page"] = "list_users"
            st.rerun()

    with col2:
        if st.button(inbox_label, use_container_width=True):
            st.session_state["admin_page"] = "inbox"
            st.rerun()

        if st.button("⏰ 送信予約", use_container_width=True):
            st.session_state["admin_page"] = "schedule"
            st.rerun()

        if st.button("👀 保護者未読一覧", use_container_width=True):
            st.session_state["admin_page"] = "unread_guardians"
            st.rerun()

    st.markdown("---")

    if st.button("🚪 ログアウト", use_container_width=True):
        st.session_state["login"] = False
        st.session_state["member_id"] = None
        st.session_state["role"] = None
        st.switch_page("main.py")


# ============================
# 📂 生徒登録
# ============================
elif page == "register":

    st.title("👥 生徒登録")
    st.markdown("Excel と CSV をアップロードしてください。")

    excel_file = st.file_uploader("📘 Excel（名簿）", type=["xlsx"])
    csv_file = st.file_uploader("📄 CSV（初期PW）", type=["csv"])

    if excel_file and csv_file:
        st.info("処理中…")
        df = import_students_from_excel_and_csv(excel_file, csv_file)
        if len(df) > 0:
            st.success("Firestoreへ登録が完了しました！")
            st.dataframe(df)
        else:
            st.warning("登録対象が見つかりませんでした。")

    st.markdown("---")
    if st.button("⬅️ 戻る"):
        st.session_state["admin_page"] = "menu"
        st.rerun()


# ============================
# 📋 登録済みユーザー一覧
# ============================
elif page == "list_users":

    st.title("📋 登録済みユーザー一覧")
    df = fetch_all_users()
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    if st.button("⬅️ 戻る"):
        st.session_state["admin_page"] = "menu"
        st.rerun()


# ============================
# 📥 受信ボックス
# ============================
elif page == "inbox":

    st.title("📥 受信ボックス")

    show_admin_inbox()

    if st.button("⬅️ 戻る"):
        st.session_state["admin_page"] = "menu"
        st.rerun()


# ============================
# 💬 チャット管理
# ============================
elif page == "chat":

    st.title("💬 チャット管理")

    show_admin_chat()

    if st.button("⬅️ 戻る"):
        st.session_state["admin_page"] = "menu"
        st.rerun()


# ============================
# ⏰ 送信予約
# ============================
elif page == "schedule":

    st.title("⏰ 送信予約")

    show_schedule_main()

    if st.button("⬅️ 戻る"):
        st.session_state["admin_page"] = "menu"
        st.rerun()


# ============================
# 👀 保護者未読一覧
# ============================
elif page == "unread_guardians":

    st.title("👀 保護者未読一覧")

    show_unread_guardian_list()

    if st.button("⬅️ 戻る"):
        st.session_state["admin_page"] = "menu"
        st.rerun()
