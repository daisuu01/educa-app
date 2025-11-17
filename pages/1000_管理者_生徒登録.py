# =============================================
# 1000_管理者_生徒登録.py（Pages方式：管理者専用）
# =============================================

import streamlit as st
import firebase_admin
from firebase_admin import firestore
from firebase_utils import (
    import_students_from_excel_and_csv,
    fetch_all_users,
    USERS,
)
import pandas as pd

# --- Firestore ---
db = firestore.client()

# =============================================
# 🔐 ログイン & 権限チェック
# =============================================
if "login" not in st.session_state or not st.session_state["login"]:
    st.error("⚠️ ログインしてください。")
    st.stop()

if st.session_state["role"] != "admin":
    st.error("⚠️ このページは管理者専用です。")
    st.stop()

admin_name = st.session_state.get("admin_name", "")

# =============================================
# 📌 管理者はサイドバーを表示する
# （CSS を書かない → そのまま表示される）
# =============================================

# =============================================
# 📄 ページタイトル
# =============================================
st.title("👨‍🏫 生徒登録（管理者）")
st.write(f"ログイン中の管理者: **{admin_name}**")

st.markdown("---")

# =============================================
# 📤 Excel/CSV アップロード
# =============================================
st.subheader("📥 生徒情報ファイルをアップロード")

uploaded_file = st.file_uploader(
    "Excel または CSV を選択してください",
    type=["xlsx", "csv"],
    accept_multiple_files=False
)

if uploaded_file:
    try:
        # --- ファイル判定 ---
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
        else:
            df = pd.read_excel(uploaded_file)

        st.success("📄 ファイルを読み込みました。内容を確認してください。")
        st.write(df)

        # --- 登録ボタン ---
        if st.button("📌 このファイルで登録を開始する"):
            with st.spinner("Firestore に登録中..."):
                count_ok, count_failed, logs = import_students_from_excel_and_csv(df)

            st.success(f"✅ 登録完了：{count_ok} 件")
            if count_failed > 0:
                st.error(f"⚠️ エラー：{count_failed} 件")

            # エラーログ
            if logs:
                with st.expander("📘 ログを表示"):
                    for line in logs:
                        st.write(line)

    except Exception as e:
        st.error(f"❌ 読み込みエラー: {e}")

st.markdown("---")

# =============================================
# 📋 登録済みユーザー一覧（簡易表示）
# =============================================
st.subheader("👥 現在の登録ユーザー数")

users = fetch_all_users()
st.write(f"総ユーザー数：**{len(users)} 名**")

# 一部だけ表示（重すぎ防止）
preview_df = pd.DataFrame(users).head(20)
st.dataframe(preview_df)

st.markdown("---")

# =============================================
# 🔙 メニューへ戻る
# =============================================
if st.button("⬅️ 管理者メニューに戻る"):
    st.switch_page("main.py")
