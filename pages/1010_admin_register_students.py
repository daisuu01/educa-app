# =============================================
# pages/1010_admin_register_students.py
# （管理者：生徒登録ページ・完全版）
# =============================================

import streamlit as st
from firebase_utils import import_students_from_excel_and_csv
from firebase_admin import firestore


# --- ページ設定 ---
st.set_page_config(page_title="生徒登録", layout="wide")


# =============================================
# 共通：スピナー非表示・白フェード無効化
# =============================================
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

// body全体を監視
observer.observe(document.body, { childList: true, subtree: true });

// 保険として 0.2 秒に 1 回上書き
setInterval(forceFullOpacity, 200);
</script>
""", unsafe_allow_html=True)


# =============================================
#  ログイン・権限チェック
# =============================================
if not st.session_state.get("login"):
    st.switch_page("main.py")

if st.session_state.get("role") != "admin":
    st.error("⚠ 管理者のみアクセスできます")
    st.stop()

member_id = st.session_state.get("member_id")


# =============================================
# 生徒登録ページ本体
# =============================================
st.title(f"👥 生徒登録（管理者：{member_id}）")
st.markdown("---")

st.markdown("### 🔽 生徒名簿（Excel）＋ 初期PW対応表（CSV）をアップロードしてください")

# --- ファイルアップロード欄 ---
excel_file = st.file_uploader("📘 Excel（名簿）", type=["xlsx"])
csv_file  = st.file_uploader("📄 CSV（初期PW対応表）", type=["csv"])

# --- 登録処理 ---
if excel_file and csv_file:
    st.info("処理中… ファイル内容を確認しています...")
    df = import_students_from_excel_and_csv(excel_file, csv_file)

    if len(df) > 0:
        st.success("🎉 Firestore への登録が完了しました！")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("⚠ 登録対象が見つかりませんでした。")

