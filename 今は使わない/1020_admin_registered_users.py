# =============================================
# pages/1020_admin_registered_users.py
# （管理者：登録済みユーザー一覧・完全版）
# =============================================

import streamlit as st
from firebase_utils import fetch_all_users
from firebase_admin import firestore


# ------------------------------------------------
# ページ設定
# ------------------------------------------------
st.set_page_config(page_title="登録済みユーザー一覧", layout="wide")


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
            el.style.opacity = "1"; // ← 強制上書き
        }
    });
}

// DOM変化を監視してフェード発動を即キャンセル
const observer = new MutationObserver(() => {
    forceFullOpacity();
});

// 監視開始
observer.observe(document.body, { childList: true, subtree: true });

// 保険として 0.2 秒ごとにチェック
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
st.title(f"📋 登録済みユーザー一覧（管理者：{member_id}）")
st.markdown("---")

st.markdown("### 👥 Firestore に登録されているすべてのユーザーを表示します。")

try:
    df = fetch_all_users()

    if len(df) == 0:
        st.warning("⚠ 現在、登録されているユーザーはいません。")
    else:
        st.success(f"🎉 {len(df)} 名のユーザーが登録されています。")
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"❌ Firestore からユーザー一覧を取得できませんでした: {e}")
