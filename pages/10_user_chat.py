# =============================================
# pages/10_ユーザー_チャット.py（生徒チャットページ）
# =============================================

import streamlit as st
from firebase_admin import firestore
from user_chat import show_chat_page, get_user_meta

# --- ページ設定 ---
st.set_page_config(page_title="チャット", layout="centered")

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

# --- Firebase ---
db = firestore.client()

# --- ユーザーの学年・クラス取得 ---
grade, class_name = get_user_meta(member_id)
grade = grade or "未設定"
class_name = class_name or "未設定"

# --- UI ---
st.title("💬 チャット")
st.markdown("管理者とのチャットルームです。")

# --- チャット本体（旧mainのまま） ---
show_chat_page(member_id, grade, class_name)

# --- 戻る ---
st.markdown("---")
if st.button("⬅️ ホームへ戻る"):
    st.switch_page("pages/1_user_home.py")
