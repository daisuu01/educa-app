# =============================================
# 🎓 educa-app.py（ユーザー側は自分の投稿のみ三点リーダー表示）
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
st.title("💬 Educa Chat（削除権限＋UI最適化版）")

# ---------------------------------------------------
# 4️⃣ ロール選択
# ---------------------------------------------------
role = st.sidebar.radio("ログインタイプを選択", ["👨‍🏫 職員（管理者）", "🎓 生徒・保護者（ユーザー）"])

# ---------------------------------------------------
# 5️⃣ クラスルーム選択
# ---------------------------------------------------
st.sidebar.header("🏫 クラスルーム")
rooms = ["中1", "中2", "中3", "保護者"]
selected_room = st.sidebar.selectbox("チャットルームを選択", rooms)

st.subheader(f"📚 {selected_room} チャットルーム")

# ---------------------------------------------------
# 6️⃣ メッセージ送信
# ---------------------------------------------------
if role == "👨‍🏫 職員（管理者）":
    sender = "講師"
else:
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
# 7️⃣ チャット履歴（ユーザーは自分の投稿のみ⋮表示）
# ---------------------------------------------------
st.subheader(f"💬 {selected_room} のチャット履歴（自動更新中）")

# 💅 CSS：削除ボタンを横中央揃え
st.markdown("""
<style>
.delete-btn {
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: #ffcccc;
    color: #333;
    font-weight: bold;
    border-radius: 8px;
    padding: 6px 20px;
    text-align: center;
    cursor: pointer;
    transition: 0.2s;
}
.delete-btn:hover {
    background-color: #ff9999;
}
</style>
""", unsafe_allow_html=True)

try:
    messages_ref = (
        db.collection("rooms")
        .document(selected_room)
        .collection("messages")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
    )
    messages = messages_ref.stream()

    for msg in messages:
        data = msg.to_dict()
        sender_name = data.get("sender", "不明")
        text = data.get("message", "")
        msg_id = msg.id

        # メッセージ本文＋三点リーダー列
        col1, col2 = st.columns([8, 1])
        with col1:
            if sender_name == "講師":
                st.markdown(f"🧑‍🏫 **{sender_name}**：<span style='color:#1565C0'>{text}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"🎓 **{sender_name}**：<span style='color:#2E7D32'>{text}</span>", unsafe_allow_html=True)

        # 🔹 三点リーダーの表示条件を判定
        if role == "👨‍🏫 職員（管理者）":
            # 管理者は全てに表示
            with col2:
                with st.popover("⋮", use_container_width=True):
                    if st.button("削除", key=f"delete_{msg_id}", use_container_width=True):
                        msg.reference.delete()
                        st.warning("メッセージを削除しました。")
                        st.experimental_rerun()
        else:
            # ユーザーは自分の投稿のみ表示
            if sender == sender_name:
                with col2:
                    with st.popover("⋮", use_container_width=True):
                        if st.button("削除", key=f"delete_{msg_id}", use_container_width=True):
                            msg.reference.delete()
                            st.warning("メッセージを削除しました。")
                            st.experimental_rerun()

except Exception as e:
    st.error(f"Firestore読み込みエラー: {e}")

# ---------------------------------------------------
# 8️⃣ 注意書き
# ---------------------------------------------------
st.caption("💡 ユーザーは自分のメッセージのみ削除可能。管理者は全削除可能です。")
