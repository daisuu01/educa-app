# =============================================
# pages/1030_admin_chat.py
# （管理者：チャット管理ページ・完全版）
# =============================================

import streamlit as st
from firebase_admin import firestore

from admin_chat import show_admin_chat
from admin_inbox import show_admin_inbox
from admin_inbox import count_unread_messages


# ------------------------------------------------
# ページ設定
# ------------------------------------------------
st.set_page_config(page_title="チャット管理", layout="wide")


# ------------------------------------------------
# CSS（サイドバー削除・スピナー削除・フェード殺し）
# ------------------------------------------------
st.markdown("""
<style>
/* ==== サイドバー完全非表示 ==== */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
nav[data-testid="stSidebarNav"],
button[aria-label="Menu"],
button[title="Menu"] {
    display: none !important;
    visibility: hidden !important;
}

/* メイン幅の最適化 */
div[data-testid="stAppViewContainer"] > section:first-child {
    margin-left: 0 !important;
    padding-left: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
}

/* ==== スピナー非表示 ==== */
.stSpinner, div[data-testid="stSpinner"] {
    display: none !important;
}

/* ==== Running時の白フェード無効化 ==== */
[data-testid="stStatusWidget"] {
    display: none !important;
}

/* ==== 透明フェード殺し ==== */
.stApp, .block-container {
    opacity: 1 !important;
    transition: none !important;
}
</style>

<script>
// =============================
// 透明フェード（opacity 0.33）強制無効化
// =============================
function forceFullOpacity() {
    document.querySelectorAll('div, section, main, header').forEach(el => {
        if (el.style.opacity && el.style.opacity < 1) {
            el.style.opacity = "1";
        }
    });
}

const observer = new MutationObserver(() => {
    forceFullOpacity();
});

observer.observe(document.body, { childList: true, subtree: true });

setInterval(forceFullOpacity, 200);
</script>
""", unsafe_allow_html=True)


# ------------------------------------------------
# ログイン & 権限チェック
# ------------------------------------------------
if not st.session_state.get("login"):
    st.switch_page("main.py")

if st.session_state.get("role") != "admin":
    st.error("⚠ 管理者のみアクセスできます")
    st.stop()


member_id = st.session_state.get("member_id")


# ------------------------------------------------
# ページタイトル
# ------------------------------------------------
st.title(f"💬 チャット管理（管理者：{member_id}）")
st.markdown("---")


# ------------------------------------------------
# 🔥 受信BOXからの遷移（クリック1回で個人チャットへ）
# ------------------------------------------------
if st.session_state.get("just_opened_from_inbox", False):

    target_id = st.session_state.get("selected_student_id")
    target_name = st.session_state.get("selected_student_name", "")

    if target_id:
        # 個人チャット表示に必要な state のセット
        st.session_state["target_type"] = "個人"
        st.session_state["target_student_id"] = target_id
        st.session_state["selected_student_id"] = target_id

        # 遷移フラグOFF
        st.session_state["just_opened_from_inbox"] = False

        st.rerun()


# ------------------------------------------------
# 🔥 チャット管理画面本体（main.py と完全同じ）
# ------------------------------------------------

# target_student_id が残っていれば使う
selected_id = st.session_state.get("target_student_id")

if selected_id:
    show_admin_chat(initial_student_id=selected_id)
else:
    show_admin_chat()

# 不要な open_mode のクリア
if "open_mode" in st.session_state and st.session_state["open_mode"] == "admin_chat":
    st.session_state["open_mode"] = None
