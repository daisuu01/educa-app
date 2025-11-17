import streamlit as st
from firebase_utils import update_user_password

# ======================================
# 🔐 ユーザー：パスワード変更ページ
# ======================================

st.set_page_config(page_title="パスワード変更", layout="centered")

st.title("🔑 パスワード変更")

# ログイン情報が無い場合（直接アクセス対策）
if "member_id" not in st.session_state or not st.session_state["member_id"]:
    st.error("⚠️ ログイン情報が確認できません。メニューから再度アクセスしてください。")
    st.stop()

member_id = st.session_state["member_id"]

# ----------------------------
# 📝 入力フォーム
# ----------------------------
new_pw = st.text_input("新しいパスワード", type="password")
confirm_pw = st.text_input("新しいパスワード（確認）", type="password")

if st.button("変更を保存"):
    if not new_pw or not confirm_pw:
        st.warning("⚠ 両方の欄を入力してください。")
    elif new_pw != confirm_pw:
        st.error("❌ パスワードが一致しません。")
    else:
        update_user_password(member_id, new_pw)
        st.success("✅ パスワードを変更しました。")

# ----------------------------
# 🔙 戻るボタン
# ----------------------------
st.markdown("---")
if st.button("⬅️ メニューに戻る"):
    st.session_state["student_page"] = "menu"
    st.rerun()
