# =============================================
# main.py（英作文添削機能統合版・Firestore履歴対応）
# =============================================

import streamlit as st
from firebase_utils import (
    verify_password,
    update_user_password,
    import_students_from_excel_and_csv,
    fetch_all_users,
    USERS,
)
from english_corrector import show_essay_corrector  # ← 🔹 新しく追加

# --- ページ設定 ---
st.set_page_config(page_title="エデュカアプリログイン", layout="centered")

# --- 状態管理 ---
if "login" not in st.session_state:
    st.session_state["login"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "member_id" not in st.session_state:
    st.session_state["member_id"] = None


# ===============================
# 🔐 ログイン画面
# ===============================
if not st.session_state["login"]:
    st.title("エデュカアプリログイン")

    member_id = st.text_input("会員番号")
    password = st.text_input("パスワード", type="password")

    if st.button("ログイン"):
        # 管理者固定ログイン
        if member_id == "1001" and password == "educa123":
            st.session_state.update({"login": True, "role": "admin"})
            st.rerun()
        else:
            doc = USERS.document(member_id).get()
            if not doc.exists:
                st.error("⚠️ ユーザーが見つかりません。")
            else:
                user = doc.to_dict()
                if verify_password(password, user):
                    role_value = user.get("role", "student")
                    st.session_state.update({
                        "login": True,
                        "role": role_value,
                        "member_id": member_id
                    })
                    st.rerun()
                else:
                    st.error("❌ パスワードが違います。")


# ===============================
# 🧭 管理者画面
# ===============================
elif st.session_state["role"] == "admin":
    st.sidebar.title("📋 管理者メニュー")
    mode = st.sidebar.radio("モードを選択してください", ["生徒登録", "登録済みユーザー一覧"])

    if mode == "生徒登録":
        st.markdown("#### 🔽 生徒情報と初期PW対応表をアップロード")
        excel_file = st.file_uploader("📘 Excelファイル（会員番号・姓・名・コード）", type=["xlsx"])
        csv_file = st.file_uploader("📄 CSVファイル（会員番号・初期PW）", type=["csv"])

        if excel_file and csv_file:
            st.info("アップロードされたファイルを確認中...")
            result = import_students_from_excel_and_csv(excel_file, csv_file)
            if len(result) > 0:
                st.success("Firestoreへ登録が完了しました ✅")
                st.dataframe(result, width="stretch")
            else:
                st.warning("⚠ 登録対象が見つかりません（既に登録済みの可能性があります）。")

    elif mode == "登録済みユーザー一覧":
        st.markdown("#### 👥 Firestore 登録済みユーザー一覧")
        df_users = fetch_all_users()
        st.dataframe(df_users, use_container_width=True)

    st.sidebar.markdown("---")
    if st.sidebar.button("ログアウト"):
        st.session_state["login"] = False
        st.rerun()


# ===============================
# 🎓 生徒ページ（英作文添削・PW変更対応）
# ===============================
elif st.session_state["role"] == "student":
    member_id = st.session_state["member_id"]
    doc = USERS.document(member_id).get()

    if not doc.exists:
        st.error("⚠️ ユーザーデータが見つかりません。")
    else:
        user_doc = doc.to_dict()

        # --- サイドバー ---
        st.sidebar.title("📋 メニュー")
        menu = st.sidebar.radio("選択してください", ["ホーム", "英作文添削", "パスワード変更"])

        st.sidebar.markdown("---")
        if st.sidebar.button("ログアウト"):
            st.session_state["login"] = False
            st.rerun()

        # --- メイン画面 ---
        if menu == "ホーム":
            pass  # ← 挨拶文などは一切表示しない

        elif menu == "英作文添削":
            # 🔹 修正点①：ユーザーIDを明示的に渡す
            show_essay_corrector(member_id)

        elif menu == "パスワード変更":
            st.markdown("### 🔑 パスワード変更")

            new_pw = st.text_input("新しいパスワード", type="password")
            confirm_pw = st.text_input("新しいパスワード（確認）", type="password")

            if st.button("変更を保存"):
                if not new_pw or not confirm_pw:
                    st.warning("⚠ 両方の欄を入力してください。")
                elif new_pw != confirm_pw:
                    st.error("❌ パスワードが一致しません。")
                else:
                    update_user_password(member_id, new_pw)
                    st.success("✅ パスワードを変更しました（初期パスワードでも引き続きログインできます）。")
