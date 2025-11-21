# =============================================
# pages/1000_admin_menu.py（管理者メニュー：サイドバー版）
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

# --- 🔧 CSS：main.py が消した sidebar を復活させつつ、
#             「Pages 一覧」だけを非表示にする ---
# --- サイドバー完全非表示 ---
# --- サイドバー（Streamlit標準）を透明化 ---
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

# --- 🔥 カスタムサイドバー表示（ここ） ---
st.markdown("""
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
    <h3>管理者メニュー</h3>
    <a style='color:white;'>生徒登録</a><br><br>
    <a style='color:white;'>チャット管理</a><br><br>
    <a style='color:white;'>受信BOX</a><br><br>
</div>
""", unsafe_allow_html=True)




# --- ログインチェック ---
if not st.session_state.get("login"):
    st.switch_page("main.py")

# 🔸 念のため role を文字列化＋ダブルクォート除去
role = st.session_state.get("role")
if isinstance(role, str):
    role = role.strip('"').strip("'")
    st.session_state["role"] = role

if st.session_state.get("role") != "admin":
    st.error("⚠️ 管理者のみアクセス可能です。")
    st.stop()

member_id = st.session_state.get("member_id", "")

db = firestore.client()

# ============================
# 📌 サブページ状態
# ============================
if "admin_page" not in st.session_state:
    st.session_state["admin_page"] = "menu"

page = st.session_state["admin_page"]

# ============================
# 📋 左サイドバーに管理者メニューを表示
# ============================
with st.sidebar:
    st.title(f"📋 管理者メニュー（{member_id}）")
    st.caption("機能を選択")

    unread = count_unread_messages()
    inbox_label = f"📥 受信ボックス（{unread}）" if unread > 0 else "📥 受信ボックス"

    # メニューの選択（ラジオボタン）
    choice = st.radio(
        "メニュー",
        [
            "👥 生徒登録",
            "📋 登録済みユーザー一覧",
            "💬 チャット管理",
            inbox_label,
            "⏰ 送信予約",
            "👀 保護者未読一覧",
        ],
        label_visibility="collapsed",
    )

    # 選択結果を内部キーにマッピング
    if choice.startswith("👥"):
        st.session_state["admin_page"] = "register"
    elif choice.startswith("📋 登録済み"):
        st.session_state["admin_page"] = "list_users"
    elif choice.startswith("💬"):
        st.session_state["admin_page"] = "chat"
    elif choice.startswith("📥"):
        st.session_state["admin_page"] = "inbox"
    elif choice.startswith("⏰"):
        st.session_state["admin_page"] = "schedule"
    elif choice.startswith("👀"):
        st.session_state["admin_page"] = "unread_guardians"

    st.markdown("---")
    if st.button("🚪 ログアウト", use_container_width=True):
        st.session_state["login"] = False
        st.session_state["member_id"] = None
        st.session_state["role"] = None
        st.switch_page("main.py")

# 最新の page を再取得
page = st.session_state["admin_page"]

# ============================
# 右側メインエリアの中身を切り替え
# ============================

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
    df = fetch_all_users()
    st.dataframe(df, use_container_width=True)

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

else:
    # 初回など：とりあえず生徒登録をデフォルトに
    st.session_state["admin_page"] = "register"
    st.experimental_rerun()
