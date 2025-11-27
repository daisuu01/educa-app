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

/* サイドバー完全削除 */
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

new MutationObserver(() => killOpacity())
    .observe(document.body, { childList: true, subtree: true });

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

# 🔥 ★追加：タブ切替のための内部状態
if "_active_tab" not in st.session_state:
    st.session_state["_active_tab"] = "👥 生徒登録"


# --------------------------------------------
# 🎉 管理者メニュー（タブ表示）
# --------------------------------------------

st.title(f"📋 管理者メニュー（{member_id}）")
st.markdown("---")

# 🔥 未読数（リアルタイム）
unread = count_unread_messages()


# 🔥 タブ定義
tab_labels = [
    "👥 生徒登録",
    "📋 登録済みユーザー一覧",
    "💬 チャット管理",
    f"📥 受信ボックス（{unread}）",
    "⏰ 送信予約",
    "👀 保護者未読一覧"
]

# 🔥 ★ここだけ追加：key を状態に紐付ける
tabs = st.tabs(tab_labels)



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

    # 🔥 受信ボックスから来たときだけ自動遷移
    if st.session_state.get("redirect_to_admin_chat", False):
        show_admin_chat(initial_student_id=st.session_state.get("selected_student_id"))
        st.session_state["redirect_to_admin_chat"] = False
        st.stop()

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






