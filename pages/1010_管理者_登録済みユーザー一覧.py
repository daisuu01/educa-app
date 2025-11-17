# =============================================
# 1010_管理者_登録済みユーザー一覧.py（Pages方式：管理者専用）
# =============================================

import streamlit as st
import pandas as pd
from firebase_utils import fetch_all_users

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
# 📄 ページタイトル
# =============================================
st.title("📋 登録済みユーザー一覧（管理者）")
st.write(f"ログイン中の管理者: **{admin_name}**")
st.markdown("---")

# =============================================
# 🔍 ユーザー一覧を Firestore から取得
# =============================================
st.subheader("📥 Firestore からユーザー一覧取得中...")

try:
    users = fetch_all_users()  # ← firebase_utils 由来
    st.success(f"ユーザー数：{len(users)} 名")
except Exception as e:
    st.error(f"❌ Firestore 取得エラー: {e}")
    st.stop()

# データフレーム化
df = pd.DataFrame(users)

# =============================================
# 🔍 絞り込み UI
# =============================================
st.subheader("🔎 検索 / フィルタリング")

col1, col2, col3 = st.columns(3)

with col1:
    grade_filter = st.selectbox(
        "学年で絞り込み",
        options=["すべて"] + sorted(df["grade"].dropna().unique()),
        index=0
    )

with col2:
    class_filter = st.selectbox(
        "クラスで絞り込み",
        options=["すべて"] + sorted(df["class_name"].dropna().unique()),
        index=0
    )

with col3:
    name_search = st.text_input("名前検索（部分一致可）")

# =============================================
# 📌 フィルタ処理
# =============================================

df_filtered = df.copy()

if grade_filter != "すべて":
    df_filtered = df_filtered[df_filtered["grade"] == grade_filter]

if class_filter != "すべて":
    df_filtered = df_filtered[df_filtered["class_name"] == class_filter]

if name_search:
    df_filtered = df_filtered[
        df_filtered["name"].str.contains(name_search, case=False, na=False)
        | df_filtered["last_name"].str.contains(name_search, case=False, na=False)
        | df_filtered["first_name"].str.contains(name_search, case=False, na=False)
    ]

# =============================================
# 📋 結果表示
# =============================================
st.write(f"🔎 絞り込み後： {len(df_filtered)} 名")

if len(df_filtered) == 0:
    st.warning("該当するユーザーがいません。")
else:
    st.dataframe(df_filtered, use_container_width=True)

st.markdown("---")

# =============================================
# 🔙 メニューに戻る
# =============================================
if st.button("⬅️ 管理者メニューに戻る"):
    st.switch_page("main.py")
