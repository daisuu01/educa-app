# =============================================
# pages/1000_admin_menu.py（管理者メニュー：サイドバー常設版）
# =============================================

import streamlit as st
from firebase_admin import firestore

from firebase_utils import (
    import_students_from_excel_and_csv,
    fetch_all_users,
    USERS,
)
from admin_chat import show_admin_chat
from admin_inbox import show_admin_inbox, count_unread_messages
from admin_schedule import show_schedule_main
from unread_guardian_list import show_unread_guardian_list


# --- ページ設定 ---
st.set_page_config(
    page_title="管理者メニュー",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>

/* ======================================
   標準の Pages ナビ（左のメニュー）だけ消す
   ====================================== */
section[data-testid="stSidebarNav"] {
    display: none !important;
}

/* サイドバー本体も非表示 */
[data-testid="stSidebar"] {
    display: none !important;
}
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}

/* ハンバーガーメニュー削除 */
button[aria-label="Menu"],
svg[data-testid="icon-hamburger"],
svg[data-testid="icon-chevron-left"],
svg[data-testid="icon-chevron-right"] {
    display: none !important;
}

/* ======================================
   ★★ メイン領域を壊さずに全幅にする ★★
   （section:first-child は絶対に使わない）
   ====================================== */
main[data-testid="stAppViewContainer"] {
    padding-left: 0 !important;
    margin-left: 0 !important;
    width: 100% !important;
}

</style>
""", unsafe_allow_html=True)


# --- ログインチェック ---
if not st.session_state.get("login"):
    st.switch_page("main.py")

if st.session_state.get("role") != "admin":
    st.error("⚠ 管理者のみアクセスできます。")
    st.stop()

db = firestore.client()

# ==========================================================
# 🧭 サイドバー（管理者専用）
# ==========================================================

st.sidebar.title(f"📋 管理者メニュー（{st.session_state.get('member_id')}）")

# 未読数を動的に表示
unread = count_unread_messages()
inbox_label = f"📥 受信ボックス（{unread}）" if unread > 0 else "📥 受信ボックス"

menu = st.sidebar.radio(
    "機能を選択",
    [
        "👥 生徒登録",
        "📋 登録済みユーザー一覧",
        "💬 チャット管理",
        inbox_label,
        "⏰ 送信予約",
        "👀 保護者未読一覧",
        "🚪 ログアウト",
    ],
)

# ==========================================================
# 📌 ページ描画
# ==========================================================

# ---------------------------
# 👥 生徒登録
# ---------------------------
if menu == "👥 生徒登録":
    st.title("👥 生徒登録")

    excel_file = st.file_uploader("📘 Excel（名簿）", type=["xlsx"])
    csv_file = st.file_uploader("📄 CSV（初期PW）", type=["csv"])

    if excel_file and csv_file:
        st.info("処理中…")
        df = import_students_from_excel_and_csv(excel_file, csv_file)
        if len(df) > 0:
            st.success("Firestoreへの登録が完了しました！")
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("登録対象がありません。")


# ---------------------------
# 📋 登録済みユーザー一覧
# ---------------------------
elif menu == "📋 登録済みユーザー一覧":
    st.title("📋 登録済みユーザー一覧")
    df = fetch_all_users()
    st.dataframe(df, use_container_width=True)


# ---------------------------
# 💬 チャット管理
# ---------------------------
elif menu == "💬 チャット管理":
    st.title("💬 チャット管理")
    show_admin_chat()


# ---------------------------
# 📥 受信ボックス
# ---------------------------
elif menu.startswith("📥 受信ボックス"):
    st.title("📥 受信ボックス")
    show_admin_inbox()


# ---------------------------
# ⏰ 送信予約
# ---------------------------
elif menu == "⏰ 送信予約":
    st.title("⏰ 送信予約")
    show_schedule_main()


# ---------------------------
# 👀 保護者未読一覧
# ---------------------------
elif menu == "👀 保護者未読一覧":
    st.title("👀 保護者未読一覧")
    show_unread_guardian_list()


# ---------------------------
# 🚪 ログアウト
# ---------------------------
elif menu == "🚪 ログアウト":
    st.session_state["login"] = False
    st.session_state["role"] = None
    st.session_state["member_id"] = None
    st.switch_page("main.py")
