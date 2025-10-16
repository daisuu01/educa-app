# =============================================
# 🎓 educa-app.py（ログイン＋スタンプ＋削除対応）
# =============================================

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
from streamlit_autorefresh import st_autorefresh

# ---------------------------
# 1. Firebase 初期化
# ---------------------------
if not firebase_admin._apps:
    firebase_json = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
    cred = credentials.Certificate(firebase_json)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------------------
# 2. ページ設定
# ---------------------------
st.set_page_config(page_title="Educa Chat", layout="wide")
st.title("💬 Educa Chat")

# ---------------------------
# 3. セッション初期化
# ---------------------------
for key in ["user_id", "user_name", "user_class", "role"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ---------------------------
# 4. ログイン画面
# ---------------------------
if st.session_state.user_id is None:
    st.subheader("🔐 ログインしてください")

    role = st.radio("ログイン種別を選択", ["👨‍🏫 管理者", "🎓 ユーザー"], horizontal=True)

    if role == "👨‍🏫 管理者":
        if st.button("管理者としてログイン"):
            st.session_state.role = "admin"
            st.session_state.user_name = "管理者"
            st.session_state.user_class = "全ルーム"
            st.session_state.user_id = "admin"
            st.success("管理者としてログインしました。")
            st.rerun()

    elif role == "🎓 ユーザー":
        user_id = st.text_input("会員番号", placeholder="例：S12345")
        password = st.text_input("パスワード", type="password")

        if st.button("ログイン"):
            if not user_id or not password:
                st.warning("会員番号とパスワードを入力してください。")
                st.stop()

            doc_ref = db.collection("users").document(user_id)
            doc = doc_ref.get()
            if not doc.exists:
                st.error("会員番号が登録されていません。")
                st.stop()

            data = doc.to_dict()
            if data.get("password") != password:
                st.error("パスワードが正しくありません。")
                st.stop()

            st.session_state.user_id = user_id
            st.session_state.user_name = data.get("name", "名無し")
            st.session_state.user_class = data.get("class", "未設定")
            st.session_state.role = "user"
            st.success(f"{st.session_state.user_name} さんがログインしました（{st.session_state.user_class}ルーム）。")
            st.rerun()

    st.stop()

# ---------------------------
# 5. チャット画面
# ---------------------------
user_name = st.session_state.user_name
user_class = st.session_state.user_class
role = st.session_state.role

st.sidebar.header("📚 ユーザー情報")
st.sidebar.write(f"👤 名前：{user_name}")
st.sidebar.write(f"🏫 所属：{user_class}")

if role == "admin":
    st.sidebar.write("🛠 管理者モード（全ルーム閲覧可能）")
    room = st.sidebar.selectbox("閲覧ルームを選択", ["中1", "中2", "中3", "保護者"])
else:
    room = user_class
    st.sidebar.success(f"🟢 {room}ルームに参加中")

st.subheader(f"💬 {room} チャットルーム")

# ---------------------------
# 6. 自動更新（5秒）
# ---------------------------
st_autorefresh(interval=5000, key="refresh")

# ---------------------------
# 7. スタンプ選択
# ---------------------------
st.markdown("### 🦕 スタンプを送信")
stamps = {
    "😊": "https://cdn-icons-png.flaticon.com/512/742/742751.png",
    "👍": "https://cdn-icons-png.flaticon.com/512/2107/2107957.png",
    "❤️": "https://cdn-icons-png.flaticon.com/512/833/833472.png",
    "🎉": "https://cdn-icons-png.flaticon.com/512/1973/1973960.png",
}
cols = st.columns(len(stamps))
for i, (emoji, url) in enumerate(stamps.items()):
    with cols[i]:
        if st.button(emoji):
            db.collection("rooms").document(room).collection("messages").add({
                "sender": user_name,
                "message": url,
                "type": "stamp",
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            st.rerun()

# ---------------------------
# 8. メッセージ送信
# ---------------------------
message = st.text_input("✏️ メッセージを入力してください")

if st.button("送信", use_container_width=True):
    if message.strip():
        db.collection("rooms").document(room).collection("messages").add({
            "sender": user_name,
            "message": message,
            "type": "text",
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        st.rerun()
    else:
        st.warning("メッセージを入力してください。")

# ---------------------------
# 9. メッセージ表示＋削除
# ---------------------------
st.write("---")
st.subheader(f"{room} のチャット履歴")

messages_ref = db.collection("rooms").document(room).collection("messages").order_by(
    "timestamp", direction=firestore.Query.DESCENDING
)
messages = messages_ref.stream()

for msg in messages:
    data = msg.to_dict()
    msg_id = msg.id
    sender = data.get("sender", "不明")
    msg_type = data.get("type", "text")
    message = data.get("message", "")

    col1, col2 = st.columns([8, 1])
    with col1:
        if msg_type == "stamp":
            st.markdown(f"**{sender}**：<br><img src='{message}' width='80'>", unsafe_allow_html=True)
        else:
            st.markdown(f"**{sender}**：{message}")

    # 削除ボタン
    if role == "admin" or sender == user_name:
        with col2:
            with st.popover("⋮", use_container_width=True):
                if st.button("削除", key=f"del_{msg_id}", use_container_width=True):
                    msg.reference.delete()
                    st.warning("削除しました。")
                    st.rerun()

# ---------------------------
# 10. ログアウト
# ---------------------------
st.sidebar.write("---")
if st.sidebar.button("🚪 ログアウト"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
