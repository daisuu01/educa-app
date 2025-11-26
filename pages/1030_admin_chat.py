# =============================================
# pages/1030_admin_chat.py
# （管理者：チャット管理ページ・完全版）
# =============================================

import streamlit as st
from firebase_admin import firestore

from admin_chat import show_admin_chat
from admin_inbox import show_admin_inbox  # 受信BOX遷移対応のため
from admin_inbox import count_unread_messages


# ------------------------------------------------
# ページ設定
# ------------------------------------------------
st.set_page_config(page_title="チャット管理", layout="wide")


# ------------------------------------------------
# CSS：スピナー非表示 & 白フェード無効化
# ------------------------------------------------
st.markdown("""
<style>
/* ==== スピナー非表示 ==== */
.stSpinner, div[data-testid="stSpinner"] {
    display: none !important;
}

/* ==== Running時の白フェード無効化 ==== */
[data-testid="stStatusWidget"] {
    display: none !important;
}

/* ==== ページ透明フェード禁止 ==== */
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

// DOM変化を監視してフェード発動を即キャンセル
const observer = new MutationObserver(() => {
    forceFullOpacity();
});

observer.observe(document.body, { childList: true, subtree: true });

// 保険として 0.2 秒ごとに実行
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
# ページ本体
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

        # 遷移フラグを消す
        st.session_state["just_opened_from_inbox"] = False

        # 再描画
        st.rerun()


# ------------------------------------------------
# 🔥 チャット画面本体
# ------------------------------------------------
selected_id = st.session_state.get("target_student_id")

if selected_id:
    # 受信BOX → 個人チャットの初期ID
    show_admin_chat(initial_student_id=selected_id)
else:
    # 通常起動
    show_admin_chat()


# ------------------------------------------------
# 不要な state をクリア（前画面から残ってしまう対策）
# ------------------------------------------------
if "open_mode" in st.session_state and st.session_state["open_mode"] == "admin_chat":
    st.session_state["open_mode"] = None
