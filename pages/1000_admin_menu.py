# =============================================
# pages/1000_admin_menu.py（白上塗り＋カスタムサイドバー完全版）
# =============================================

import streamlit as st
from firebase_admin import firestore

from admin_chat import show_admin_chat
from admin_inbox import show_admin_inbox, count_unread_messages
from firebase_utils import fetch_all_users, import_students_from_excel_and_csv
from admin_schedule import show_schedule_main
from unread_guardian_list import show_unread_guardian_list

# -------------------------------------------------------------
# ページ設定
# -------------------------------------------------------------
st.set_page_config(page_title="管理者メニュー", layout="wide")

# -------------------------------------------------------------
# 1) pages サイドバーを「白ペンキ」で完全上書きし消す
# -------------------------------------------------------------
st.markdown("""
<style>
/* サイドバー本体を白で上書き（真っ黒問題を確実に防ぐ） */
[data-testid="stSidebar"] {
    background-color: white !important;
    width: 260px !important;
    opacity: 1 !important;
}

/* pages の ナビゲーションを非表示（ユーザー画面のリンクが出ないように） */
nav[data-testid="stSidebarNav"] {
    display: none !important;
}

/* ハンバーガーメニューも消す */
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}

/* メインエリアを全幅に広げる */
div[data-testid="stAppViewContainer"] > section:first-child {
    margin-left: 0 !important;
    padding-left: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2) ログインチェック
# -------------------------------------------------------------
if not st.session_state.get("login"):
    st.switch_page("main.py")

role = str(st.session_state.get("role", "")).replace('"', "")
if role != "admin":
    st.error("⚠ 管理者のみアクセス可能です")
    st.stop()

member_id = st.session_state.get("member_id", "")

# -------------------------------------------------------------
# 3) 管理者ページの内部状態
# -------------------------------------------------------------
if "admin_page" not in st.session_state:
    st.session_state["admin_page"] = "register"

page = st.session_state["admin_page"]

# 未読件数
unread = count_unread_messages()
inbox_label = f"📥 受信ボックス（{unread}）" if unread > 0 else "📥 受信ボックス"

MENU = [
    ("register", "👥 生徒登録"),
    ("list_users", "📋 登録済みユーザー一覧"),
    ("chat", "💬 チャット管理"),
    ("inbox", inbox_label),
    ("schedule", "⏰ 送信予約"),
    ("unread_guardians", "👀 保護者未読一覧"),
]

# -------------------------------------------------------------
# 4) 白く上塗りした上に「自作サイドバー」を重ねる
# -------------------------------------------------------------
sidebar_html = f"""
<div style="
    position: fixed;
    top: 0;
    left: 0;
    width: 260px;
    height: 100vh;
    background: #1e1e1e;  /* ← あなたの好きな黒サイドバー */
    padding: 20px;
    color: white;
    z-index: 9999;
">
    <h3 style="margin-top:0;">📋 管理者メニュー（{member_id}）</h3>
"""

for key, label in MENU:
    active = (page == key)
    bg = "#333" if active else "none"
    sidebar_html += f"""
        <div style="
            padding: 10px;
            margin: 8px 0;
            background: {bg};
            border-radius: 6px;
        ">
            <a href='?admin_page={key}'
               style="color:white; text-decoration:none; font-size:16px;">
                {label}
            </a>
        </div>
    """

sidebar_html += """
<hr style="border-color:#555;">
<a href="?logout=1" style="color:white;text-decoration:none;font-size:16px;">
    🚪 ログアウト
</a>
</div>
"""

# 自作サイドバー描画
st.markdown(sidebar_html, unsafe_allow_html=True)

# -------------------------------------------------------------
# 5) URLパラメータ処理
# -------------------------------------------------------------
qs = st.query_params

if "admin_page" in qs:
    st.session_state["admin_page"] = qs["admin_page"]
    st.query_params.clear()
    st.rerun()

if "logout" in qs:
    st.session_state.clear()
    st.switch_page("main.py")

# -------------------------------------------------------------
# 6) メインエリア（自作サイドバーの横に表示）
# -------------------------------------------------------------
st.markdown("<div style='margin-left:280px;'>", unsafe_allow_html=True)

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

st.markdown("</div>", unsafe_allow_html=True)
