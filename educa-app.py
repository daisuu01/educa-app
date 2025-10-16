# =============================================
# 🎓 educa-app.py（縦三点リーダー＋横並び削除UI対応）
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
st.title("💬 Educa Chat（削除UI改良版：縦三点リーダー）")

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
# 7️⃣ チャット履歴（縦三点リーダー＋横並び削除UI）
# ---------------------------------------------------
st.subheader(f"💬 {selected_room} のチャット履歴（自動更新中）")

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

        # メッセージ行：本文と縦三点リーダーを横並びに配置
        col1, col2 = st.columns([8, 1])
        with col1:
            if sender_name == "講師":
                st.markdown(f"🧑‍🏫 **{sender_name}**：<span style='color:#1565C0'>{text}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"🎓 **{sender_name}**：<span style='color:#2E7D32'>{text}</span>", unsafe_allow_html=True)

        # 縦三点リーダー（⋮）
        with col2:
            menu = st.popover("⋮", use_container_width=True)
            with menu:
                cols = st.columns(3)
                with cols[1]:  # 真ん中に配置
                    if st.button("削除", key=f"delete_{msg_id}", use_container_width=True):
                        msg.reference.delete()
                        st.warning("メッセージを削除しました。")
                        st.experimental_rerun()

except Exception as e:
    st.error(f"Firestore読み込みエラー: {e}")

# ---------------------------------------------------
# 8️⃣ 注意書き
# ---------------------------------------------------
st.caption("💡 各メッセージ右側の『⋮』から削除可能です。削除は全ユーザーに即時反映されます。")
