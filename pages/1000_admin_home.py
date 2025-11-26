# # =============================================
# # pages/1000_admin_menu.py（タブ方式：最安定バージョン）
# # =============================================

# import streamlit as st
# from firebase_admin import firestore

# from admin_chat import show_admin_chat
# from admin_inbox import show_admin_inbox, count_unread_messages
# from firebase_utils import fetch_all_users, import_students_from_excel_and_csv
# from admin_schedule import show_schedule_main
# from unread_guardian_list import show_unread_guardian_list

# # ---- ページ設定 ----
# st.set_page_config(page_title="管理者メニュー", layout="wide")

# # ---- サイドバー完全非表示＋Running無効化＋フェード無効化 ----
# st.markdown("""
# <style>
# /* ==== サイドバー完全削除 ==== */
# [data-testid="stSidebar"],
# [data-testid="stSidebarCollapsedControl"] {
#     display: none !important;
#     visibility: hidden !important;
# }
# div[data-testid="stAppViewContainer"] > section:first-child {
#     width: 100% !important;
#     max-width: 100% !important;
#     margin-left: 0 !important;
#     padding-left: 0 !important;
# }

# /* ==== Running スピナー非表示 ==== */
# .stSpinner, div[data-testid="stSpinner"] {
#     display: none !important;
# }

# /* ==== Running時の白フェード無効化 ==== */
# [data-testid="stStatusWidget"] {
#     display: none !important;
# }

# /* ==== ページの透明フェード完全禁止 ==== */
# .stApp, .block-container {
#     opacity: 1 !important;
#     transition: none !important;
# }
# </style>

# <script>
# // =============================
# // 透明フェード（opacity 0.33）強制無効化
# // =============================
# function forceFullOpacity() {
#     document.querySelectorAll('div, section, main, header').forEach(el => {
#         if (el.style.opacity && el.style.opacity < 1) {
#             el.style.opacity = "1"; // ← 強制上書き
#         }
#     });
# }

# // DOM変化を監視してフェード発動を即キャンセル
# const observer = new MutationObserver(() => {
#     forceFullOpacity();
# });

# // body全体を監視
# observer.observe(document.body, { childList: true, subtree: true });

# // 保険として 0.2 秒に 1 回上書き
# setInterval(forceFullOpacity, 200);
# </script>
# """, unsafe_allow_html=True)

# # ---- ログインチェック ----
# if not st.session_state.get("login"):
#     st.switch_page("main.py")

# if st.session_state.get("role") != "admin":
#     st.error("⚠ 管理者のみアクセスできます")
#     st.stop()

# member_id = st.session_state.get("member_id")

# # --------------------------------------------
# # 🎉 管理者メニュー（タブ表示）
# # --------------------------------------------

# st.title(f"📋 管理者メニュー（{member_id}）")
# st.markdown("---")

# # 🔥 未読数（リアルタイム）
# unread = count_unread_messages()

# # 🔥 タブ6つ
# tabs = st.tabs([
#     "👥 生徒登録",
#     "📋 登録済みユーザー一覧",
#     "💬 チャット管理",
#     f"📥 受信ボックス（{unread}）",
#     "⏰ 送信予約",
#     "👀 保護者未読一覧"
# ])

# # ------------------------
# # 👥 生徒登録
# # ------------------------
# with tabs[0]:
#     st.header("👥 生徒登録")
#     excel_file = st.file_uploader("📘 Excel（名簿）", type=["xlsx"])
#     csv_file = st.file_uploader("📄 CSV（初期PW）", type=["csv"])

#     if excel_file and csv_file:
#         st.info("処理中…")
#         df = import_students_from_excel_and_csv(excel_file, csv_file)
#         if len(df) > 0:
#             st.success("Firestoreへ登録が完了しました！")
#         else:
#             st.warning("登録対象が見つかりませんでした。")
#         st.dataframe(df, use_container_width=True)

# # ------------------------
# # 📋 登録済みユーザー一覧
# # ------------------------
# with tabs[1]:
#     st.header("📋 登録済みユーザー一覧")
#     st.dataframe(fetch_all_users(), use_container_width=True)

# # ------------------------
# # 💬 チャット管理
# # ------------------------
# with tabs[2]:
#     st.header("💬 チャット管理")
#     show_admin_chat()

# # ------------------------
# # 📥 受信BOX
# # ------------------------
# with tabs[3]:
#     st.header("📥 受信ボックス")
#     show_admin_inbox()

# # ------------------------
# # ⏰ 送信予約
# # ------------------------
# with tabs[4]:
#     st.header("⏰ 送信予約")
#     show_schedule_main()

# # ------------------------
# # 👀 保護者未読一覧
# # ------------------------
# with tabs[5]:
#     st.header("👀 保護者未読一覧")
#     show_unread_guardian_list()





# =============================================
# pages/1000_admin_menu.py（右サイドバー完全版）
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

# ---- 左サイドバー完全非表示＋フェード無効化 ----
st.markdown("""
<style>
/* ==== 左公式サイドバー完全削除 ==== */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
    visibility: hidden !important;
}

/* ==== Running スピナー非表示 ==== */
.stSpinner, div[data-testid="stSpinner"] {
    display: none !important;
}

/* ==== Running時の白フェード無効化 ==== */
[data-testid="stStatusWidget"] {
    display: none !important;
}

/* ==== ページの透明フェード完全禁止 ==== */
.stApp, .block-container {
    opacity: 1 !important;
    transition: none !important;
}

/* ==== 右サイドバー（自作） ==== */
.right-sidebar {
    position: fixed;
    top: 0;
    right: 0;
    width: 260px;
    height: 100%;
    background-color: #f8f9fa;
    border-left: 1px solid #ddd;
    padding: 20px 15px;
    overflow-y: auto;
    z-index: 9999;
}

/* ==== メインコンテンツの幅調整 ==== */
.main-container {
    margin-right: 280px;
    padding-right: 20px;
}
</style>

<script>
function forceFullOpacity() {
    document.querySelectorAll('div, section, main, header').forEach(el => {
        if (el.style.opacity && el.style.opacity < 1) {
            el.style.opacity = "1";
        }
    });
}
const observer = new MutationObserver(() => { forceFullOpacity(); });
observer.observe(document.body, { childList: true, subtree: true });
setInterval(forceFullOpacity, 200);
</script>
""", unsafe_allow_html=True)


# ---- ログインチェック ----
if not st.session_state.get("login"):
    st.switch_page("main.py")

if st.session_state.get("role") != "admin":
    st.error("⚠ 管理者のみアクセスできます")
    st.stop()

member_id = st.session_state.get("member_id")

# =============================================
# 🎉 右側：管理者メニュー（以前の main.py の radio）
# =============================================

# 未読数（リアルタイム）
unread = count_unread_messages()
inbox_label = f"📥 受信ボックス（{unread}）" if unread > 0 else "📥 受信ボックス"

menu_options = [
    "👥 生徒登録",
    "📋 登録済みユーザー一覧",
    "💬 チャット管理",
    inbox_label,
    "⏰ 送信予約",
    "👀 保護者未読一覧",
]

# 選択保持
default_selection = st.session_state.get("admin_menu_selected", menu_options[0])

# ---- 右サイドバー描画 ----
with st.container():
    st.markdown('<div class="right-sidebar">', unsafe_allow_html=True)
    st.markdown(f"### 📋 管理者メニュー（{member_id}）")

    selected = st.radio(
        "メニューを選択してください",
        menu_options,
        index=menu_options.index(default_selection),
    )

    # "受信ボックス（数字）" → "受信ボックス" に正規化
    if selected.startswith("📥 受信ボックス"):
        selected_mode = "📥 受信ボックス"
    else:
        selected_mode = selected

    st.session_state["admin_menu_selected"] = selected_mode
    st.markdown('</div>', unsafe_allow_html=True)


# =============================================
# 🎉 メインコンテンツ（右サイドバーの横に表示）
# =============================================
st.markdown('<div class="main-container">', unsafe_allow_html=True)

st.title("📋 管理者メニュー")
st.markdown("---")

# -----------------------------
# 👥 生徒登録
# -----------------------------
if selected_mode == "👥 生徒登録":
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

# -----------------------------
# 📋 登録済みユーザー一覧
# -----------------------------
elif selected_mode == "📋 登録済みユーザー一覧":
    st.header("📋 登録済みユーザー一覧")
    st.dataframe(fetch_all_users(), use_container_width=True)

# -----------------------------
# 💬 チャット管理
# -----------------------------
elif selected_mode == "💬 チャット管理":
    st.header("💬 チャット管理")
    show_admin_chat()

# -----------------------------
# 📥 受信ボックス
# -----------------------------
elif selected_mode == "📥 受信ボックス":
    st.header("📥 受信ボックス")
    show_admin_inbox()

# -----------------------------
# ⏰ 送信予約
# -----------------------------
elif selected_mode == "⏰ 送信予約":
    st.header("⏰ 送信予約")
    show_schedule_main()

# -----------------------------
# 👀 保護者未読一覧
# -----------------------------
elif selected_mode == "👀 保護者未読一覧":
    st.header("👀 保護者未読一覧")
    show_unread_guardian_list()

st.markdown('</div>', unsafe_allow_html=True)



