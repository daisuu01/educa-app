# =============================================
# 🎓 educa-app.py
# 管理者：左に個人リスト、右に個別トーク（全体送信も可能）
# ユーザー：管理者↔自分の個別トークのみ（全体送信は自分宛として表示）
# Firestoreの personal/messages はコードで自動生成
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
for key in ["user_id", "user_name", "user_class", "role", "admin_selected_room", "admin_selected_user"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ---------------------------
# ヘルパー：自動生成
# ---------------------------
def ensure_room_doc(class_name: str):
    """rooms/{class} ドキュメントを（なければ）作る"""
    room_ref = db.collection("rooms").document(class_name)
    if not room_ref.get().exists:
        room_ref.set({"_init": True}, merge=True)

def ensure_personal_thread(class_name: str, user_id: str):
    """rooms/{class}/personal/{user_id} と messages サブコレを（なければ）作る"""
    ensure_room_doc(class_name)
    personal_ref = (
        db.collection("rooms").document(class_name)
        .collection("personal").document(user_id)
    )
    if not personal_ref.get().exists:
        personal_ref.set({"_createdAt": firestore.SERVER_TIMESTAMP}, merge=True)

    msgs_ref = personal_ref.collection("messages")
    # 初回だけ hidden の初期化メッセージを1件入れて実体化（表示はしない）
    if next(msgs_ref.limit(1).stream(), None) is None:
        msgs_ref.add({
            "sender": "system",
            "message": "thread initialized",
            "type": "system",
            "hidden": True,
            "timestamp": firestore.SERVER_TIMESTAMP
        })

def send_to_room_all(class_name: str, sender_label: str, message: str, msg_type="text"):
    """管理者→クラス全員（rooms/{class}/messages）"""
    ensure_room_doc(class_name)
    db.collection("rooms").document(class_name).collection("messages").add({
        "sender": sender_label,
        "message": message,
        "type": msg_type,
        "to": "ALL",
        "timestamp": firestore.SERVER_TIMESTAMP
    })

def send_to_personal(class_name: str, user_id: str, sender_label: str, message: str, msg_type="text"):
    """管理者/ユーザー → 個別（rooms/{class}/personal/{user_id}/messages）"""
    ensure_personal_thread(class_name, user_id)
    db.collection("rooms").document(class_name).collection("personal").document(user_id).collection("messages").add({
        "sender": sender_label,
        "message": message,
        "type": msg_type,
        "to": user_id,
        "timestamp": firestore.SERVER_TIMESTAMP
    })

def get_users_by_class(class_name: str):
    """users コレクションから class 一致ユーザー一覧"""
    q = db.collection("users").where(filter=FieldFilter("class", "==", class_name))
    return list(q.stream())

# ---------------------------
# ログイン
# ---------------------------
if st.session_state.user_id is None:
    st.subheader("🔐 ログインしてください")
    role = st.radio("ログイン種別を選択", ["👨‍🏫 管理者", "🎓 ユーザー"], horizontal=True)

    if role == "👨‍🏫 管理者":
        if st.button("管理者としてログイン"):
            st.session_state.role = "admin"
            st.session_state.user_name = "管理者"
            st.session_state.user_id = "admin"
            st.session_state.user_class = "中1"  # 初期表示用
            st.session_state.admin_selected_room = "中1"
            st.session_state.admin_selected_user = None
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

            # 個別スレッドの土台をログイン時に作っておく
            ensure_personal_thread(st.session_state.user_class, st.session_state.user_id)

            st.success(f"{st.session_state.user_name} さん（{st.session_state.user_class}）でログインしました。")
            st.rerun()
    st.stop()

# ---------------------------
# 以降：共通UI
# ---------------------------
role = st.session_state.role
user_name = st.session_state.user_name
user_id = st.session_state.user_id
user_class = st.session_state.user_class

st.sidebar.header("📚 ユーザー情報")
st.sidebar.write(f"👤 名前：{user_name}")
if role == "user":
    st.sidebar.write(f"🏫 所属：{user_class}")

# 自動更新（5秒ごと）
st_autorefresh(interval=5000, key="auto_refresh")

# ------------------------------------------
# 管理者UI：2カラム（左：個人リスト／右：個別トーク）
# ------------------------------------------
STAMPS = {
    "😊": "https://cdn-icons-png.flaticon.com/512/742/742751.png",
    "👍": "https://cdn-icons-png.flaticon.com/512/2107/2107957.png",
    "❤️": "https://cdn-icons-png.flaticon.com/512/833/833472.png",
    "🎉": "https://cdn-icons-png.flaticon.com/512/1973/1973960.png",
}

if role == "admin":
    # クラス（ルーム）選択
    st.sidebar.subheader("🧭 管理メニュー")
    st.session_state.admin_selected_room = st.sidebar.selectbox(
        "クラスを選択", ["中1", "中2", "中3", "保護者"],
        index=["中1","中2","中3","保護者"].index(st.session_state.admin_selected_room or "中1")
    )
    current_room = st.session_state.admin_selected_room

    # 2カラムレイアウト
    left, right = st.columns([1, 2], gap="large")

    # 左：個人リスト
    with left:
        st.markdown(f"### 📚 {current_room} の生徒・保護者")
        people = get_users_by_class(current_room)
        if not people:
            st.info("このクラスには登録ユーザーがいません。")
        else:
            # 表示ラベル（id｜name）
            labels = [f"{u.id}｜{u.to_dict().get('name','')}" for u in people]
            # 選択保持
            default_index = 0
            if st.session_state.admin_selected_user:
                # 過去選択がリストにあればそれを初期選択
                try:
                    default_index = [u.id for u in people].index(st.session_state.admin_selected_user)
                except ValueError:
                    default_index = 0

            chosen_label = st.radio("個人を選択", labels, index=default_index if labels else 0)
            chosen_user = people[labels.index(chosen_label)]
            chosen_user_id = chosen_user.id
            chosen_user_name = chosen_user.to_dict().get("name","")
            st.session_state.admin_selected_user = chosen_user_id

            # 個別スレッド土台を確実に作成
            ensure_personal_thread(current_room, chosen_user_id)

    # 右：選択した個人とのトーク画面
    with right:
        st.markdown(f"### 🧑 {chosen_user_name} さんとのトーク（{current_room}）")

        # 送信方法：チェックで「このクラス全員に送る」
        to_all = st.checkbox("このクラス全員に送る（ブロードキャスト）", value=False, help="ONの場合はクラス全員へ送信。OFFなら右の相手との個別送信。")

        admin_msg = st.text_input("本文（管理者）")
        c1, c2 = st.columns([3, 2])
        with c1:
            if st.button("📨 送信", use_container_width=True):
                if admin_msg.strip():
                    if to_all:
                        send_to_room_all(current_room, "講師", admin_msg, msg_type="text")
                    else:
                        send_to_personal(current_room, chosen_user_id, "講師", admin_msg, msg_type="text")
                    st.rerun()
                else:
                    st.warning("本文を入力してください。")
        with c2:
            with st.popover("😊 スタンプ", use_container_width=True):
                cols = st.columns(4)
                for i, (emoji, url) in enumerate(STAMPS.items()):
                    with cols[i % 4]:
                        if st.button(emoji):
                            if to_all:
                                send_to_room_all(current_room, "講師", url, msg_type="stamp")
                            else:
                                send_to_personal(current_room, chosen_user_id, "講師", url, msg_type="stamp")
                            st.rerun()

        st.write("---")
        st.caption("🗂 個別チャット履歴")
        msgs = (
            db.collection("rooms").document(current_room)
            .collection("personal").document(chosen_user_id)
            .collection("messages")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .stream()
        )

        for m in msgs:
            d = m.to_dict()
            if d.get("type") == "system" and d.get("hidden"):
                continue
            sender_name = d.get("sender", "不明")
            mtype = d.get("type", "text")
            content = d.get("message", "")
            colA, colB = st.columns([8, 1])
            with colA:
                if mtype == "stamp":
                    st.markdown(f"**{sender_name}**：<br><img src='{content}' width='80'>", unsafe_allow_html=True)
                else:
                    st.markdown(f"**{sender_name}**：{content}")
            # 管理者は全削除可
            with colB:
                with st.popover("⋮", use_container_width=True):
                    if st.button("削除", key=f"del_admin_{m.id}", use_container_width=True):
                        m.reference.delete()
                        st.warning("削除しました。")
                        st.rerun()

# ------------------------------------------
# ユーザーUI：管理者↔自分の個別スレッド + 全体送信も自分タイムラインで表示
# ------------------------------------------
else:
    current_room = user_class
    st.sidebar.success(f"🟢 {current_room} ルーム（個別トーク）")

    st.markdown("### ✉️ 管理者にメッセージを送る（他ユーザーには見えません）")
    # 生徒/保護者の区分
    sender_role = st.radio("送信者区分", ["生徒", "保護者"], horizontal=True)
    sender_label = f"{sender_role}：{user_name}"

    # 個別スレッド土台を確実に作成
    ensure_personal_thread(current_room, user_id)

    # 送信欄
    user_msg = st.text_input("本文（管理者宛）")
    c1, c2 = st.columns([3, 2])
    with c1:
        if st.button("📨 送信", use_container_width=True):
            if user_msg.strip():
                send_to_personal(current_room, user_id, sender_label, user_msg, msg_type="text")
                st.rerun()
            else:
                st.warning("本文を入力してください。")
    with c2:
        with st.popover("😊 スタンプ", use_container_width=True):
            cols = st.columns(4)
            for i, (emoji, url) in enumerate(STAMPS.items()):
                with cols[i % 4]:
                    if st.button(emoji):
                        send_to_personal(current_room, user_id, sender_label, url, msg_type="stamp")
                        st.rerun()

    st.write("---")
    st.caption("🗂 あなた宛てのメッセージ（管理者↔あなた + クラス全体送信）")

    # ① クラス全体メッセージ（ALL）
    room_stream = db.collection("rooms").document(current_room).collection("messages").order_by(
        "timestamp", direction=firestore.Query.DESCENDING
    ).stream()
    # ② 個別（あなた）スレッド
    personal_stream = db.collection("rooms").document(current_room).collection("personal").document(user_id).collection("messages").order_by(
        "timestamp", direction=firestore.Query.DESCENDING
    ).stream()

    # Python側で統合＆降順
    combined = []
    for m in room_stream:
        d = m.to_dict()
        if d.get("type") == "system" and d.get("hidden"):
            continue
        combined.append(m)
    for m in personal_stream:
        d = m.to_dict()
        if d.get("type") == "system" and d.get("hidden"):
            continue
        combined.append(m)

    def _ts(msg):
        return msg.to_dict().get("timestamp", firestore.SERVER_TIMESTAMP)

    combined.sort(key=_ts, reverse=True)

    # 表示（ユーザーは自分送信のみ削除可）
    for m in combined:
        d = m.to_dict()
        sender_name = d.get("sender", "不明")
        mtype = d.get("type", "text")
        content = d.get("message", "")

        colA, colB = st.columns([8, 1])
        with colA:
            if mtype == "stamp":
                st.markdown(f"**{sender_name}**：<br><img src='{content}' width='80'>", unsafe_allow_html=True)
            else:
                st.markdown(f"**{sender_name}**：{content}")

        can_delete = sender_name.startswith(("生徒：", "保護者：")) and (user_name in sender_name)
        if can_delete:
            with colB:
                with st.popover("⋮", use_container_width=True):
                    if st.button("削除", key=f"del_user_{m.id}", use_container_width=True):
                        m.reference.delete()
                        st.warning("削除しました。")
                        st.rerun()

# ---------------------------
# ログアウト
# ---------------------------
st.sidebar.write("---")
if st.sidebar.button("🚪 ログアウト"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
