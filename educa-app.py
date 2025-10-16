# =============================================
# 🎓 educa-app.py
# （管理者：個別/全員送信、ユーザー：管理者宛のみ、
#  LINE風：左リスト＋右トーク表示、Firestore自動生成）
# =============================================

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
from streamlit_autorefresh import st_autorefresh
from google.cloud.firestore_v1 import FieldFilter

# ---------------------------
# Firebase 初期化
# ---------------------------
if not firebase_admin._apps:
    firebase_json = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
    cred = credentials.Certificate(firebase_json)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------------------
# ページ設定
# ---------------------------
st.set_page_config(page_title="Educa Chat", layout="wide")
st.title("💬 Educa Chat")

# ---------------------------
# セッション初期化
# ---------------------------
for key in ["user_id", "user_name", "user_class", "role", "selected_user_id"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ---------------------------
# Firestore ヘルパー
# ---------------------------
def ensure_room_doc(class_name: str):
    ref = db.collection("rooms").document(class_name)
    if not ref.get().exists:
        ref.set({"_init": True}, merge=True)

def ensure_personal_thread(class_name: str, user_id: str):
    ensure_room_doc(class_name)
    ref = db.collection("rooms").document(class_name).collection("personal").document(user_id)
    if not ref.get().exists:
        ref.set({"_createdAt": firestore.SERVER_TIMESTAMP}, merge=True)
    msgs_ref = ref.collection("messages")
    if not next(msgs_ref.limit(1).stream(), None):
        msgs_ref.add({
            "sender": "system",
            "message": "initialized",
            "type": "system",
            "hidden": True,
            "timestamp": firestore.SERVER_TIMESTAMP
        })

def send_to_personal(class_name, user_id, sender, message, msg_type="text"):
    ensure_personal_thread(class_name, user_id)
    db.collection("rooms").document(class_name).collection("personal").document(user_id)\
      .collection("messages").add({
        "sender": sender,
        "message": message,
        "type": msg_type,
        "timestamp": firestore.SERVER_TIMESTAMP
    })

def get_users_by_class(class_name):
    q = db.collection("users").where(filter=FieldFilter("class", "==", class_name))
    return list(q.stream())

# ---------------------------
# ログイン
# ---------------------------
if st.session_state.user_id is None:
    st.subheader("🔐 ログインしてください")
    role = st.radio("ログイン種別", ["👨‍🏫 管理者", "🎓 ユーザー"], horizontal=True)

    if role == "👨‍🏫 管理者":
        if st.button("管理者としてログイン"):
            st.session_state.update({
                "role": "admin",
                "user_name": "管理者",
                "user_class": "中1",
                "user_id": "admin"
            })
            st.success("管理者としてログインしました。")
            st.rerun()

    else:
        uid = st.text_input("会員番号")
        pw = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            doc = db.collection("users").document(uid).get()
            if not doc.exists:
                st.error("会員番号が存在しません。")
                st.stop()
            data = doc.to_dict()
            if data.get("password") != pw:
                st.error("パスワードが違います。")
                st.stop()
            st.session_state.update({
                "role": "user",
                "user_id": uid,
                "user_name": data.get("name", ""),
                "user_class": data.get("class", "")
            })
            ensure_personal_thread(st.session_state.user_class, uid)
            st.success("ログインしました。")
            st.rerun()
    st.stop()

# ---------------------------
# 共通設定
# ---------------------------
role = st.session_state.role
user_name = st.session_state.user_name
user_class = st.session_state.user_class
user_id = st.session_state.user_id
st.sidebar.header("📚 ユーザー情報")
st.sidebar.write(f"👤 {user_name}")
st.sidebar.write(f"🏫 {user_class}")
st_autorefresh(interval=5000, key="refresh")

# ---------------------------
# 管理者ビュー
# ---------------------------
if role == "admin":
    col_left, col_right = st.columns([1.2, 2.8])
    with col_left:
        st.markdown("#### 👥 生徒一覧（新着順）")

        # クラス内ユーザーの最新メッセージ時刻を取得して並べる
        users = get_users_by_class(user_class)
        user_times = []
        for u in users:
            uid = u.id
            ensure_personal_thread(user_class, uid)
            msgs = db.collection("rooms").document(user_class).collection("personal").document(uid)\
                     .collection("messages").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1).stream()
            last = next(msgs, None)
            ts = last.to_dict().get("timestamp") if last else None
            user_times.append((uid, u.to_dict().get("name", ""), ts))
        # 新着順ソート
        user_times.sort(key=lambda x: x[2] or 0, reverse=True)

        names = [f"{u[0]}｜{u[1]}" for u in user_times]
        selected_label = st.radio("ユーザーを選択", names)
        st.session_state.selected_user_id = selected_label.split("｜")[0]
        selected_uid = st.session_state.selected_user_id

        if st.button("🗳 全員に送信"):
            st.session_state.selected_user_id = "ALL"

    with col_right:
        if st.session_state.selected_user_id == "ALL":
            st.markdown("### 📢 全員に送信")
        else:
            st.markdown(f"### 💬 {selected_label} さんとのチャット")

        STAMPS = {
            "😊": "https://cdn-icons-png.flaticon.com/512/742/742751.png",
            "👍": "https://cdn-icons-png.flaticon.com/512/2107/2107957.png",
            "❤️": "https://cdn-icons-png.flaticon.com/512/833/833472.png",
            "🎉": "https://cdn-icons-png.flaticon.com/512/1973/1973960.png",
        }

        msg = st.text_input("本文")
        col_tx, col_sp = st.columns([3, 2])
        with col_tx:
            if st.button("📨 送信", use_container_width=True):
                if msg.strip():
                    if st.session_state.selected_user_id == "ALL":
                        # 全員送信
                        for u in users:
                            send_to_personal(user_class, u.id, "講師", msg)
                    else:
                        send_to_personal(user_class, selected_uid, "講師", msg)
                    st.rerun()
        with col_sp:
            with st.popover("😊 スタンプ", use_container_width=True):
                cols = st.columns(4)
                for i, (emo, url) in enumerate(STAMPS.items()):
                    with cols[i % 4]:
                        if st.button(emo):
                            target = st.session_state.selected_user_id
                            if target == "ALL":
                                for u in users:
                                    send_to_personal(user_class, u.id, "講師", url, msg_type="stamp")
                            else:
                                send_to_personal(user_class, selected_uid, "講師", url, msg_type="stamp")
                            st.rerun()

        # チャット履歴表示
        if selected_uid != "ALL":
            msgs = db.collection("rooms").document(user_class).collection("personal").document(selected_uid)\
                     .collection("messages").order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
            for m in msgs:
                data = m.to_dict()
                if not data.get("hidden"):
                    if data["type"] == "stamp":
                        st.markdown(f"**{data['sender']}**<br><img src='{data['message']}' width='80'>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**{data['sender']}**：{data['message']}")

# ---------------------------
# ユーザービュー
# ---------------------------
else:
    st.markdown("### 💬 管理者とのチャット")
    ensure_personal_thread(user_class, user_id)
    sender_role = st.radio("送信者区分", ["生徒", "保護者"], horizontal=True)
    label = f"{sender_role}：{user_name}"

    msg = st.text_input("本文")
    col_tx, col_sp = st.columns([3, 2])
    with col_tx:
        if st.button("📨 送信", use_container_width=True):
            if msg.strip():
                send_to_personal(user_class, user_id, label, msg)
                st.rerun()
    with col_sp:
        STAMPS = {
            "😊": "https://cdn-icons-png.flaticon.com/512/742/742751.png",
            "👍": "https://cdn-icons-png.flaticon.com/512/2107/2107957.png",
            "❤️": "https://cdn-icons-png.flaticon.com/512/833/833472.png",
            "🎉": "https://cdn-icons-png.flaticon.com/512/1973/1973960.png",
        }
        with st.popover("😊 スタンプ", use_container_width=True):
            cols = st.columns(4)
            for i, (emo, url) in enumerate(STAMPS.items()):
                with cols[i % 4]:
                    if st.button(emo):
                        send_to_personal(user_class, user_id, label, url, msg_type="stamp")
                        st.rerun()

    msgs = db.collection("rooms").document(user_class).collection("personal").document(user_id)\
             .collection("messages").order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
    for m in msgs:
        data = m.to_dict()
        if not data.get("hidden"):
            if data["type"] == "stamp":
                st.markdown(f"**{data['sender']}**<br><img src='{data['message']}' width='80'>", unsafe_allow_html=True)
            else:
                st.markdown(f"**{data['sender']}**：{data['message']}")

# ---------------------------
# ログアウト
# ---------------------------
st.sidebar.write("---")
if st.sidebar.button("🚪 ログアウト"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()
