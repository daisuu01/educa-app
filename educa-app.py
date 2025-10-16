# =============================================
# 🎓 educa-app.py（スタンプ送信機能付き）
# =============================================

import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------
# 1️⃣ Firebase 初期化
# ---------------------------------------------------
if not firebase_admin._apps:
    firebase_json = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
    cred = credentials.Certificate(firebase_json)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------------------------------------------
# 2️⃣ ページ設定
# ---------------------------------------------------
st.set_page_config(page_title="Educa Chat", layout="wide")
st.title("💬 Educa Chat")

# ---------------------------------------------------
# 3️⃣ ロール選択
# ---------------------------------------------------
if "role" not in st.session_state:
    st.session_state.role = None
if "user_room" not in st.session_state:
    st.session_state.user_room = None

if st.session_state.role is None:
    st.subheader("🔐 ログインを選択してください")
    role_choice = st.radio("ログイン種別", ["👨‍🏫 管理者", "🎓 ユーザー"], horizontal=True)

    if role_choice == "👨‍🏫 管理者":
        if st.button("管理者としてログイン"):
            st.session_state.role = "admin"
            st.success("管理者としてログインしました。")

    elif role_choice == "🎓 ユーザー":
        st.info("ご自身のクラスを選択してログインしてください。")
        selected_room_before_login = st.selectbox("所属クラス", ["中1", "中2", "中3"])
        if st.button("ユーザーとしてログイン"):
            st.session_state.role = "user"
            st.session_state.user_room = selected_room_before_login
            st.success(f"ユーザーとしてログインしました。（{selected_room_before_login}）")

    st.stop()

# ---------------------------------------------------
# 4️⃣ ロールに応じたルーム設定
# ---------------------------------------------------
role = st.session_state.role

if role == "admin":
    st.sidebar.header("👨‍🏫 管理者モード")
    available_rooms = ["中1", "中2", "中3", "保護者"]
    selected_room = st.sidebar.selectbox("入室するルームを選択", available_rooms)
else:
    st.sidebar.header("🎓 ユーザーモード")
    selected_room = st.session_state.user_room
    st.sidebar.write(f"🟢 現在のルーム：**{selected_room}**")

st.subheader(f"📚 {selected_room} チャットルーム")

# ---------------------------------------------------
# 5️⃣ 自動更新設定（5秒ごと）
# ---------------------------------------------------
st_autorefresh(interval=5000, limit=None, key="chat_refresh")

# ---------------------------------------------------
# 6️⃣ メッセージ・スタンプ送信
# ---------------------------------------------------
if role == "admin":
    sender = st.selectbox("送信者", ["講師A", "講師B", "職員"])
else:
    sender = st.selectbox("送信者", ["生徒", "保護者"])

message = st.text_input("メッセージを入力してください")

col_msg, col_stamp = st.columns([3, 1])
with col_msg:
    if st.button("📨 送信", use_container_width=True):
        if message.strip():
            db.collection("rooms").document(selected_room).collection("messages").add({
                "sender": sender,
                "message": message,
                "type": "text",
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            st.success("メッセージを送信しました！")
        else:
            st.warning("メッセージを入力してください。")

# 🔹 スタンプ送信用ポップアップ
stamps = {
    "👍": "https://cdn-icons-png.flaticon.com/512/456/456115.png",
    "❤️": "https://cdn-icons-png.flaticon.com/512/833/833472.png",
    "😂": "https://cdn-icons-png.flaticon.com/512/742/742751.png",
    "🎉": "https://cdn-icons-png.flaticon.com/512/197/197484.png",
    "🙏": "https://cdn-icons-png.flaticon.com/512/1598/1598191.png",
    "🐸": "https://cdn-icons-png.flaticon.com/512/616/616408.png",
    "💪": "https://cdn-icons-png.flaticon.com/512/1995/1995574.png",
}

with col_stamp:
    with st.popover("😊 スタンプ", use_container_width=True):
        st.markdown("### スタンプを選択")
        cols = st.columns(4)
        for i, (emoji, url) in enumerate(stamps.items()):
            with cols[i % 4]:
                if st.button(emoji, key=f"stamp_{i}"):
                    db.collection("rooms").document(selected_room).collection("messages").add({
                        "sender": sender,
                        "message": url,
                        "type": "stamp",
                        "timestamp": firestore.SERVER_TIMESTAMP
                    })
                    st.success(f"スタンプ {emoji} を送信しました！")
                    st.experimental_rerun()

# ---------------------------------------------------
# 7️⃣ チャット履歴表示
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
        msg_type = data.get("type", "text")
        msg_id = msg.id

        col1, col2 = st.columns([8, 1])
        with col1:
            if msg_type == "stamp":
                st.markdown(f"**{sender_name}**：<br><img src='{text}' width='80'>", unsafe_allow_html=True)
            else:
                st.markdown(f"**{sender_name}**：{text}")

        # 削除権限制御
        if role == "admin":
            with col2:
                with st.popover("⋮", use_container_width=True):
                    if st.button("削除", key=f"delete_{msg_id}", use_container_width=True):
                        msg.reference.delete()
                        st.warning("削除しました。")
                        st.experimental_rerun()
        else:
            if sender_name == sender:
                with col2:
                    with st.popover("⋮", use_container_width=True):
                        if st.button("削除", key=f"delete_{msg_id}", use_container_width=True):
                            msg.reference.delete()
                            st.warning("削除しました。")
                            st.experimental_rerun()

except Exception as e:
    st.error(f"Firestore読み込みエラー: {e}")

# ---------------------------------------------------
# 8️⃣ ログアウト
# ---------------------------------------------------
st.sidebar.divider()
if st.sidebar.button("🚪 ログアウト"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
