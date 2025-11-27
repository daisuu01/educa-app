# =============================================
# pages/1010_admin_student_register.py
# 生徒登録ページ（独立ページ）
# =============================================

import streamlit as st
from firebase_utils import import_students_from_excel_and_csv

# ---- ページ設定 ----
st.set_page_config(page_title="生徒登録", layout="wide")

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

st.title("👥 生徒登録")
st.markdown("---")

# ---- アップロード欄 ----
excel_file = st.file_uploader("📘 Excel（名簿）", type=["xlsx"])
csv_file = st.file_uploader("📄 CSV（初期PW）", type=["csv"])

# ---- 登録処理 ----
if excel_file and csv_file:
    st.info("Firestoreへ登録中… しばらくお待ちください")

    df = import_students_from_excel_and_csv(excel_file, csv_file)

    if len(df) > 0:
        st.success("🎉 Firestoreへの登録が完了しました！")
    else:
        st.warning("⚠ 登録対象データが見つかりませんでした")

    st.dataframe(df, use_container_width=True)

# ---- 管理メニューへ戻る ----
st.markdown("---")
if st.button("⬅ 管理者メニューに戻る"):
    st.switch_page("pages/1000_admin_home.py")
