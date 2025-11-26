# =============================================
# pages/40_user_password_change.py（パスワード変更）
# =============================================

import streamlit as st
from firebase_utils import update_user_password
from firebase_admin import firestore

# --- ページ設定 ---
st.set_page_config(page_title="パスワード変更", layout="centered")

# --- サイドバー完全非表示 ---
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


# --- ログインチェック ---
if not st.session_state.get("login"):
    st.switch_page("main.py")

member_id = st.session_state.get("member_id")


# ===============================
# 🔑 パスワード変更 UI
# ===============================

st.title("🔑 パスワード変更")

st.markdown("新しいパスワードを入力してください。")

new_pw = st.text_input("新しいパスワード", type="password", key="new_pw")
confirm_pw = st.text_input("新しいパスワード（確認）", type="password", key="confirm_pw")

if st.button("変更を保存", use_container_width=True):
    if not new_pw or not confirm_pw:
        st.warning("⚠ 両方の欄を入力してください。")
    elif new_pw != confirm_pw:
        st.error("❌ パスワードが一致しません。")
    else:
        update_user_password(member_id, new_pw)
        st.success("✅ パスワードを変更しました！")


# ===============================
# 🔙 戻る
# ===============================
st.markdown("---")
if st.button("⬅️ ホームへ戻る"):
    st.switch_page("pages/1_user_home.py")
