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

# ---- サイドバー完全非表示＋Running無効化＋フェード無効化 ----
st.markdown("""
<style>
/* ===========================================
   ① Streamlit の白フェード overlay を完全 OFF
   =========================================== */

/* ページ覆う白い膜 */
.stApp::before {
    content: none !important;
    display: none !important;
    background: none !important;
}

/* status widget も白膜を作るので削除 */
[data-testid="stStatusWidget"] {
    display: none !important;
    visibility: hidden !important;
}

/* ===========================================
   ② rerun 中にかかる 0.33 opacity を強制OFF
   =========================================== */

.stApp, .stApp > div, .block-container, div, section, main, header {
    opacity: 1 !important;
    transition: none !important;
}

/* container への fade-in 防止 */
[data-testid="stAppViewContainer"] {
    transition: none !important;
}

/* スピナーを完全非表示 */
.stSpinner, div[data-testid="stSpinner"] {
    display: none !important;
    visibility: hidden !important;
}

/* サイドバー完全削除（必要なら） */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
    visibility: hidden !important;
}
</style>

<script>
// ===========================================
// ③ Streamlit の opacity を JS で強制上書き
// ===========================================

function killOpacity() {
    document.querySelectorAll('*').forEach(el => {
        const style = window.getComputedStyle(el);
        if (style.opacity && parseFloat(style.opacity) < 1) {
            el.style.opacity = "1";
        }
    });
}

// DOM 更新が起きた瞬間に即上書き
new MutationObserver(() => killOpacity())
    .observe(document.body, { childList: true, subtree: true });

// 念のため 0.2 秒ごとにも実行
setInterval(killOpacity, 200);
</script>
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










# # =============================================
# # pages/1000_admin_menu.py（右カラム固定サイドバー版）
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

# # ---- 左公式サイドバー完全非表示 ----
# st.markdown("""
# <style>
# [data-testid="stSidebar"],
# [data-testid="stSidebarCollapsedControl"] {
#     display: none !important;
# }
# </style>
# """, unsafe_allow_html=True)


# # ---- ログインチェック ----
# if not st.session_state.get("login"):
#     st.switch_page("main.py")

# if st.session_state.get("role") != "admin":
#     st.error("⚠ 管理者のみアクセスできます")
#     st.stop()

# member_id = st.session_state.get("member_id")


# # =============================================
# # 🎨 レイアウト（左メイン + 右サイドバー）
# # =============================================

# left, right = st.columns([5, 2])   # ← 右側をサイドバー化


# # =============================================
# # 🎉 右サイドバー（以前の main.py の radio）
# # =============================================
# with right:

#     st.markdown("### 📋 管理者メニュー")

#     unread = count_unread_messages()
#     inbox_label = f"📥 受信ボックス（{unread}）" if unread > 0 else "📥 受信ボックス"

#     menu_options = [
#         "👥 生徒登録",
#         "📋 登録済みユーザー一覧",
#         "💬 チャット管理",
#         inbox_label,
#         "⏰ 送信予約",
#         "👀 保護者未読一覧",
#     ]

#     default_selection = st.session_state.get("admin_menu_selected", menu_options[0])

#     selected = st.radio(
#         "メニューを選択してください",
#         menu_options,
#         index=menu_options.index(default_selection)
#     )

#     # ラベル整形
#     if selected.startswith("📥"):
#         selected_mode = "📥 受信ボックス"
#     else:
#         selected_mode = selected

#     st.session_state["admin_menu_selected"] = selected_mode


# # =============================================
# # 🎉 左メイン画面
# # =============================================
# with left:

#     st.title(f"📋 管理者メニュー（{member_id}）")
#     st.markdown("---")

#     # -----------------------------
#     # 👥 生徒登録
#     # -----------------------------
#     if selected_mode == "👥 生徒登録":
#         st.header("👥 生徒登録")
#         excel_file = st.file_uploader("📘 Excel（名簿）", type=["xlsx"])
#         csv_file = st.file_uploader("📄 CSV（初期PW）", type=["csv"])

#         if excel_file and csv_file:
#             st.info("処理中…")
#             df = import_students_from_excel_and_csv(excel_file, csv_file)
#             if len(df) > 0:
#                 st.success("Firestoreへ登録が完了しました！")
#             else:
#                 st.warning("登録対象が見つかりませんでした。")
#             st.dataframe(df, use_container_width=True)

#     # -----------------------------
#     # 📋 登録済みユーザー一覧
#     # -----------------------------
#     elif selected_mode == "📋 登録済みユーザー一覧":
#         st.header("📋 登録済みユーザー一覧")
#         st.dataframe(fetch_all_users(), use_container_width=True)

#     # -----------------------------
#     # 💬 チャット管理
#     # -----------------------------
#     elif selected_mode == "💬 チャット管理":
#         st.header("💬 チャット管理")
#         show_admin_chat()

#     # -----------------------------
#     # 📥 受信ボックス
#     # -----------------------------
#     elif selected_mode == "📥 受信ボックス":
#         st.header("📥 受信ボックス")
#         show_admin_inbox()

#     # -----------------------------
#     # ⏰ 送信予約
#     # -----------------------------
#     elif selected_mode == "⏰ 送信予約":
#         st.header("⏰ 送信予約")
#         show_schedule_main()

#     # -----------------------------
#     # 👀 保護者未読一覧
#     # -----------------------------
#     elif selected_mode == "👀 保護者未読一覧":
#         st.header("👀 保護者未読一覧")
#         show_unread_guardian_list()

