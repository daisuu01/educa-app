# =============================================
# 🎓 educa-app.py（会員番号ログイン＋自動ルーム割り当て版）
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
# 3. セッション状態初期化
# ---------------------------
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "user_class" not in st.session_state:
    st.session_state.user_class = None
if "role" not in st.session_state:
    st.session_state.role = None

# ---------------------------
# 4. ログイン画面
# ---------------------------
if st.session_state.user_id is None:
    st.subheader("🔐 ログインしてください")

    role = st.radio("ログイン種別を選択", ["👨‍🏫 管理者", "🎓 ユーザー"], horizontal=True)

    # 管理者モード（簡易）
    if role == "👨‍🏫 管理者":
        if st.button("管理者としてログイン"):
            st.session_state.role = "admin"
            st.session_state.user_name = "管理者"
            st.session_state.user_class = "全ルーム"
            st.session_state.user_id = "admin"
            st.success("管理者としてログインしました。")
        st.stop()

    # ユーザーモード
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
            st.experimental_rerun()

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
# 6. 自動更新
# ---------------------------
st_autorefresh(interval=5000, key="refresh")

# ---------------------------
# 7. メッセージ送信
# ---------------------------
message = st.text_input("メッセージを入力してください")

if st.button("送信", use_container_width=True):
    if message.strip():
        db.collection("rooms").document(room).collection("messages").add({
            "sender": user_name,
            "message": message,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        st.experimental_rerun()
    else:
        st.warning("メッセージを入力してください。")

# ---------------------------
# 8. メッセージ表示
# ---------------------------
messages_ref = db.collection("rooms").document(room).collection("messages").order_by("timestamp", direction=firestore.Query.DESCENDING)
messages = messages_ref.stream()

st.write("---")
st.subheader(f"{room}のチャット履歴")

for msg in messages:
    data = msg.to_dict()
    st.markdown(f"**{data.get('sender', '不明')}**：{data.get('message', '')}")

# ---------------------------
# 9. ログアウト
# ---------------------------
st.sidebar.write("---")
if st.sidebar.button("🚪 ログアウト"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.experimental_rerun()
