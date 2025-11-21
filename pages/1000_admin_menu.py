# =============================================
# pages/1000_admin_menu.py（管理者メニュー：カスタム左サイドバー版）
# =============================================

import streamlit as st
from firebase_admin import firestore

from admin_chat import show_admin_chat
from admin_inbox import show_admin_inbox, count_unread_messages
from firebase_utils import fetch_all_users, import_students_from_excel_and_csv
from admin_schedule import show_schedule_main
from unread_guardian_list import show_unread_guardian_list

# --- ページ設定 ---
st.set_page_config(page_title="管理者メニュー", layout="wide")

# --- Streamlit標準のサイドバーを透明化（クリックも無効化） ---
st.markdown("""
<style>
[data-testid="stSidebar"] {
    opacity: 0 !important;
    pointer-events: none !important;
    width: 0 !important;
}
[data-testid="stSidebarCollapsedControl"] {
    opacity: 0 !important;
    pointer-events: none !important;
}
div[data-testid="stAppViewContainer"] > section:first-child {
    margin-left: 0 !important;
    padding-left: 0 !important;
}
</style>
""", unsafe_allow_html=True)


# --- 🔥 カスタムサイドバー（あなたの正式メニュー） ---
# メニュー状態を取得 or 初期化
if "admin_page" not in st.session_state:
    st.session_state["admin_page"] = "register"

member_id = st.session_state.get("member_id", "")
unread = count_unread_messages()
inbox_label = f"📥 受信ボックス（{unread}）" if unread > 0 else "📥 受信ボックス"

# メニュー項目
MENU = [
    ("register", "👥 生徒登録"),
    ("list_users", "📋 登録済みユーザー一覧"),
    ("chat", "💬 チャット管理"),
    ("inbox", inbox_label),
    ("schedule", "⏰ 送信予約"),
    ("unread_guardians", "👀 保護者未読一覧"),
]

# カスタムHTML生成
menu_html = f"""
<div style="
    position: fixed;
    top: 0;
    left: 0;
    width: 260px;
    height: 100vh;
    background: #1e1e1e;
    padding: 20px;
    color: white;
    z-index: 9999;
">
    <h3 style="margin-top: 0;">📋 管理者メニュー（{member_id}）</h3>
"""

for key, label in MENU:
    active = (st.session_state["admin_page"] == key)
    menu_html += f"""
        <div style="
            padding: 10px 5px;
            margin: 8px 0;
            background: {'#333333' if active else 'none'};
            border-radius: 6px;
        ">
            <a href="?admin_page={key}" 
               style="color: white; text-decoration:none; font-size:16px;">
               {label}
            </a>
        </div>
    """

# ログアウトボタン
menu_html += """
    <hr style="border-color:#555;">
    <a href="?logout=1" style="color:white;text-decoration:none;font-size:16px;">
        🚪 ログアウト
    </a>
</div>
"""

st.markdown(menu_html, unsafe_allow_html=True)


# --- URLパラメータ処理（カスタムサイドバーのクリック用） ---
query_params = st.query_params

if "admin_page" in query_params:
    st.session_state["admin_page"] = query_params["admin_page"]
    st.query_params.clear()

if "logout" in query_params:
    st.session_state.clear()
    st.switch_page("main.py")


# =====================================================
# 右側メインエリア（コンテンツ切り替え）
# =====================================================

page = st.session_state["admin_page"]

if page == "register":
    st.title("👥 生徒登録")
    st.markdown("Excel と CSV をアップロードしてください。")

    excel_file = st.file_uploader("📘 Excel（名簿）", type=["xlsx"])
    csv_file = st.file_uploader("📄 CSV（初期PW）", type=["csv"])

    if excel_file and csv_file:
        st.info("処理中…")
        df = import_students_from_excel_and_csv(excel_file, csv_file)
        if len(df) > 0:
            st.success("Firestoreへ登録が完了しました！")
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("登録対象が見つかりませんでした。")

elif page == "list_users":
    st.title("📋 登録済みユーザー一覧")
    st.dataframe(fetch_all_users(), use_container_width=True)

elif page == "chat":
    st.title("💬 チャット管理")
    show_admin_chat()

elif page == "inbox":
    st.title("📥 受信ボックス")
    show_admin_inbox()

elif page == "schedule":
    st.title("⏰ 送信予約")
    show_schedule_main()

elif page == "unread_guardians":
    st.title("👀 保護者未読一覧")
    show_unread_guardian_list()
