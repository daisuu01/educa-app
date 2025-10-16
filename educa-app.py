# =============================================
# 🎓 educa-app.py（管理者／ユーザー切り替え対応）
# =============================================

import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------
# 1️⃣ 自動更新設定（5秒ごと）
# ---------------------------------------------------
st_autorefresh(interval=5000, limit=None, key="chat_refresh")

# ---------------------------------------------------
# 2️⃣ Firebase 初期化
# ---------------------------------------------------
if not firebase_admin._apps:
    firebase_json = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
    cred = credentials.Certificate(firebase_json)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------------------------------------------
# 3️⃣ ページ設定
# ---------------------------------------------------
st.set_page_config(page_title="Educa Chat", layout="wide")
st.title("💬 Educa Chat（管理者／ユーザー切り替え版）")

# ---------------------------------------------------
# 4️⃣ ロール選択
# ---------------------------------------------------
role = st.sidebar.radio("ログインタイプを選択", ["👨‍🏫 職員（管理者）", "🎓 生徒・保護者（ユーザー）"])

# ---------------------------------------------------
# 5️⃣ クラスルーム選択（共通）
# ---------------------------------------------------
st.sidebar.header("🏫 クラスルーム")
rooms = ["中1", "中2", "中3", "保護者"]
selected_room = st.sidebar.selectbox("チャットルームを選択", rooms)

st.subheader(f"📚 {selected_room} チャットルーム")

# ---------------------------------------------------
# 6️⃣ 管理者モード
# ---------------------------------------------------
if role == "👨‍🏫 職員（管理者）":
    st.markdown("🧑‍🏫 **管理者モード：講師・スタッフ用画面です。**")
    st.caption("ここから全ルームの送信や削除ができます。")

    col1, col2 = st.columns([1, 3])
    with col1:
        sender = "講師"
    with col2:
        message = st.text_input("メッセージを入力してください")

    if st.button("送信（管理者）", use_container_width=True):
        if message.strip():
            db.collection("rooms").document(selected_room).collection("messages").add({
                "sender": sender,
                "message": message,
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            st.success("メッセージを送信しました！")
        else:
            st.warning("メッセージを入力してください。")

    # 🔥 管理者だけメッセージ削除可能
    st.subheader("🗑 メッセージ削除")
    try:
        messages_ref = db.collection("rooms").document(selected_room).collection("messages").order_by("timestamp", direction=firestore.Query.DESCENDING)
        messages = messages_ref.stream()
        for msg in messages:
            data = msg.to_dict()
            text = data.get("message", "")
            sender = data.get("sender", "")
            if st.button(f"削除: {sender}『{text[:20]}...』"):
                msg.reference.delete()
                st.warning("削除しました！")
                st.experimental_rerun()
    except Exception as e:
        st.error(f"削除時エラー: {e}")

# ---------------------------------------------------
# 7️⃣ ユーザーモード
# ---------------------------------------------------
else:
    st.markdown("🎓 **生徒・保護者モード：閲覧・送信専用です。**")

    sender = st.selectbox("送信者", ["生徒", "保護者"])
    message = st.text_input("メッセージを入力してください")

    if st.button("送信", use_container_width=True):
        if message.strip():
            db.collection("rooms").document(selected_room).collection("messages").add({
                "sender": sender,
                "message": message,
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            st.success("メッセージを送信しました！")
        else:
            st.warning("メッセージを入力してください。")

# ---------------------------------------------------
# 8️⃣ チャット履歴（共通）
# ---------------------------------------------------
st.subheader(f"💬 {selected_room} のチャット履歴")

try:
    messages_ref = db.collection("rooms").document(selected_room).collection("messages").order_by("timestamp", direction=firestore.Query.DESCENDING)
    messages = messages_ref.stream()
    for msg in messages:
        data = msg.to_dict()
        sender = data.get("sender", "不明")
        text = data.get("message", "")
        if sender == "講師":
            st.markdown(f"🧑‍🏫 **{sender}**：<span style='color:#1565C0'>{text}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"🎓 **{sender}**：<span style='color:#2E7D32'>{text}</span>", unsafe_allow_html=True)
except Exception as e:
    st.error(f"Firestore読み込みエラー: {e}")

st.caption("💡 ロールによって機能が変わります。職員は送信＋削除、生徒は送信のみ可能。")
