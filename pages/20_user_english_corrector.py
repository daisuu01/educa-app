# =============================================
# pages/20_user_english_corrector.py（英作文添削）
# =============================================

import streamlit as st
from firebase_admin import firestore
from english_corrector import show_essay_corrector

# --- ページ設定 ---
st.set_page_config(page_title="英作文添削", layout="centered")

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

# --- Firestore クライアント（必要なら使用） ---
db = firestore.client()

# ===============================
# 📝 英作文添削ページ UI
# ===============================

st.title("📝 英作文添削")
st.markdown("以下の問題を解いて、英作文を送信してください。")

# --- 旧 main.py と同じ関数を使う ---
show_essay_corrector(member_id)

# ===============================
# 🔙 戻るボタン
# ===============================
st.markdown("---")
if st.button("⬅️ ホームへ戻る"):
    st.switch_page("pages/1_user_home.py")
