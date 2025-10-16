# =============================================
# 🎓 educa-app.py
# （管理者：全員/個別送信・ユーザー：管理者宛のみ・
#  ユーザー側は自分宛てのタイムライン表示・
#  personal/messages 自動生成）
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
for key in ["user_id", "user_name", "user_class", "role"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ---------------------------
# ヘルパー：パス自動生成（必要なら作る）
# ---------------------------
def ensure_room_doc(class_name: str):
    """rooms/{class} ドキュメントを作成（なければ）"""
    room_ref = db.collection("rooms").document(class_name)
    if not room_ref.get().exists:
        room_ref.set({"_init": True}, merge=True)

def ensure_personal_thread(class_name: str, user_id: str):
    """
    rooms/{class}/personal/{user_id} ドキュメントを作成（なければ）。
    さらに messages サブコレクションが空なら、非表示の初期メッセージを1件入れて
    サブコレクションを「存在させる」。（表示時は hidden=True を除外）
    """
    ensure_room_doc(class_name)
    personal_ref = (
        db.collection("rooms")
        .document(class_name)
        .collection("personal")
        .document(user_id)
    )
    if not personal_ref.get().exists:
        personal_ref.set({"_createdAt": firestore.SERVER_TIMESTAMP}, merge=True)

    # messages サブコレクションを実体化（初回のみ hidden で1件）
    msgs_ref = personal_ref.collection("messages")
    exists = next(msgs_ref.limit(1).stream(), None)
    if exists is None:
        msgs_ref.add({
            "sender": "system",
            "message": "thread initialized",
            "type": "system",
            "hidden": True,
            "timestamp": firestore.SERVER_TIMESTAMP,
        })

def send_to_room_all(class_name: str, sender_label: str, message: str, msg_type="text"):
    """管理者→ルーム全員（rooms/{class}/messages）に送信"""
    ensure_room_doc(class_name)
    db.collection("rooms").document(class_name).collection("messages").add({
        "sender": sender_label,
        "message": message,
        "type": msg_type,
        "to": "ALL",
        "timestamp": firestore.SERVER_TIMESTAMP
    })

def send_to_personal(class_name: str, user_id: str, sender_label: str, message: str, msg_type="text"):
    """管理者/ユーザー → 個別（rooms/{class}/personal/{user_id}/messages）に送信"""
    ensure_personal_thread(class_name, user_id)
    db.collection("rooms").document(class_name).collection("personal").document(user_id).collection("messages").add({
        "sender": sender_label,
        "message": message,
        "type": msg_type,
        "to": user_id,
        "timestamp": firestore.SERVER_TIMESTAMP
    })

def get_users_by_class(class_name: str):
    """users コレクションから class 一致のユーザー一覧を取得"""
    # 単一条件の等価フィルタ（インデックス不要）
    q = db.collection("users").where(filter=FieldFilter("class", "==", class_name))
    return list(q.stream())

# ---------------------------
# ログイン画面
# ---------------------------
if st.session_state.user_id is None:
    st.subheader("🔐 ログインしてください")

    role = st.radio("ログイン種別を選択", ["👨‍🏫 管理者", "🎓 ユーザー"], horizontal=True)

    if role == "👨‍🏫 管理者":
        # 簡易ログイン（本番は Firebase Auth へ置き換え）
        if st.button("管理者としてログイン"):
            st.session_state.role = "admin"
            st.session_state.user_name = "管理者"
            st.session_state.user_class = "中1"  # 初期表示のクラス。後でサイドバーで切替
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

            # ログイン時に、個別スレッドの土台を自動生成
            ensure_personal_thread(st.session_state.user_class, st.session_state.user_id)

            st.success(f"{st.session_state.user_name} さん（{st.session_state.user_class}）でログインしました。")
            st.rerun()

    st.stop()

# ---------------------------
# 以降：チャットUI
# ---------------------------
role = st.session_state.role
user_name = st.session_state.user_name
user_class = st.session_state.user_class
user_id = st.session_state.user_id

st.sidebar.header("📚 ユーザー情報")
st.sidebar.write(f"👤 名前：{user_name}")
st.sidebar.write(f"🏫 所属：{user_class}")

# 管理者は閲覧クラスを選択可能。ユーザーは固定。
if role == "admin":
    room = st.sidebar.selectbox("閲覧ルームを選択", ["中1", "中2", "中3", "保護者"], index=["中1","中2","中3","保護者"].index(user_class) if user_class in ["中1","中2","中3","保護者"] else 0)
else:
    room = user_class
    st.sidebar.success(f"🟢 {room} ルーム")

st.subheader(f"💬 {room} チャット")

# 自動更新
st_autorefresh(interval=5000, key="refresh")

# ---------------------------
# 送信 UI
# ---------------------------

# スタンプ（画像URL）は必要に応じて差し替えOK
STAMPS = {
    "😊": "https://cdn-icons-png.flaticon.com/512/742/742751.png",
    "👍": "https://cdn-icons-png.flaticon.com/512/2107/2107957.png",
    "❤️": "https://cdn-icons-png.flaticon.com/512/833/833472.png",
    "🎉": "https://cdn-icons-png.flaticon.com/512/1973/1973960.png",
}

if role == "admin":
    # 送信先：全員 or 個別
    st.markdown("#### ✉️ 管理者送信")
    target_mode = st.radio("送信先", ["ルーム全員に送信", "特定個人に送信"], horizontal=True)

    selected_user_id = None
    selected_user_label = None

    if target_mode == "特定個人に送信":
        # クラスに所属するユーザー一覧
        ensure_room_doc(room)
        candidates = get_users_by_class(room)
        if not candidates:
            st.info("このクラスに登録されたユーザーがいません。users コレクションをご確認ください。")
        else:
            # 表示用リスト
            options = []
            for u in candidates:
                d = u.to_dict()
                options.append((u.id, f"{u.id}｜{d.get('name','')}", d.get("name","")))
            # 選択
            labels = [opt[1] for opt in options]
            choice = st.selectbox("送信先ユーザー", labels)
            chosen = options[labels.index(choice)]
            selected_user_id = chosen[0]
            selected_user_label = chosen[2]

            # スレッド土台を事前に用意（自動生成）
            ensure_personal_thread(room, selected_user_id)

    # メッセージ送信欄
    admin_msg = st.text_input("本文（管理者）")
    col_tx, col_sp = st.columns([3, 2])

    with col_tx:
        if st.button("📨 送信", use_container_width=True):
            if admin_msg.strip():
                if target_mode == "ルーム全員に送信":
                    send_to_room_all(room, "講師", admin_msg, msg_type="text")
                else:
                    if selected_user_id:
                        send_to_personal(room, selected_user_id, "講師", admin_msg, msg_type="text")
                st.rerun()
            else:
                st.warning("本文を入力してください。")

    with col_sp:
        with st.popover("😊 スタンプ", use_container_width=True):
            cols = st.columns(4)
            for i, (emoji, url) in enumerate(STAMPS.items()):
                with cols[i % 4]:
                    if st.button(emoji):
                        if target_mode == "ルーム全員に送信":
                            send_to_room_all(room, "講師", url, msg_type="stamp")
                        else:
                            if selected_user_id:
                                send_to_personal(room, selected_user_id, "講師", url, msg_type="stamp")
                        st.rerun()

else:
    # ユーザー → 管理者のみ（個別スレッドへ）
    st.markdown("#### ✉️ 管理者にメッセージを送る（他ユーザーには見えません）")
    # 区分（生徒/保護者）を明示したい場合はここで選択
    sender_role = st.radio("送信者区分", ["生徒", "保護者"], horizontal=True)
    sender_label = f"{sender_role}：{user_name}"

    # 事前に自分のスレッド土台を用意（自動生成）
    ensure_personal_thread(room, user_id)

    user_msg = st.text_input("本文（管理者宛）")
    col_tx, col_sp = st.columns([3, 2])

    with col_tx:
        if st.button("📨 送信", use_container_width=True):
            if user_msg.strip():
                send_to_personal(room, user_id, sender_label, user_msg, msg_type="text")
                st.rerun()
            else:
                st.warning("本文を入力してください。")

    with col_sp:
        with st.popover("😊 スタンプ", use_container_width=True):
            cols = st.columns(4)
            for i, (emoji, url) in enumerate(STAMPS.items()):
                with cols[i % 4]:
                    if st.button(emoji):
                        send_to_personal(room, user_id, sender_label, url, msg_type="stamp")
                        st.rerun()

# ---------------------------
# タイムライン表示
# ---------------------------
st.write("---")
st.markdown("### 🗂 タイムライン")

def render_message_row(msg, role_scope: str):
    data = msg.to_dict()
    msg_id = msg.id
    sender_name = data.get("sender", "不明")
    mtype = data.get("type", "text")
    content = data.get("message", "")
    hidden = data.get("hidden", False)

    if hidden:
        return  # 非表示の初期化メッセージは描画しない

    col1, col2 = st.columns([8, 1])
    with col1:
        if mtype == "stamp":
            st.markdown(f"**{sender_name}**：<br><img src='{content}' width='80'>", unsafe_allow_html=True)
        else:
            st.markdown(f"**{sender_name}**：{content}")

    # 削除権限：
    # 管理者 → すべて削除可能
    # ユーザー → 自分が送ったメッセージのみ削除可能
    can_delete = False
    if role_scope == "admin":
        can_delete = True
    elif role_scope == "user" and sender_name.startswith(("生徒：", "保護者：")) and (st.session_state.user_name in sender_name):
        can_delete = True

    if can_delete:
        with col2:
            with st.popover("⋮", use_container_width=True):
                if st.button("削除", key=f"del_{msg_id}", use_container_width=True):
                    msg.reference.delete()
                    st.warning("削除しました。")
                    st.rerun()

if role == "admin":
    # 管理者ビュー：ルーム全体メッセージと、（必要なら個別スレッド選択も）
    st.caption("👀 表示：ルーム全体メッセージ")
    room_msgs = (
        db.collection("rooms").document(room).collection("messages")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .stream()
    )
    for m in room_msgs:
        render_message_row(m, "admin")

    st.write("---")
    st.caption("👀 表示：個別スレッド（ユーザー選択）")
    # クラスのユーザー一覧
    users = get_users_by_class(room)
    if users:
        uid_labels = [f"{u.id}｜{u.to_dict().get('name','')}" for u in users]
        chosen = st.selectbox("閲覧したいユーザー", uid_labels, index=0)
        chosen_uid = users[uid_labels.index(chosen)].id
        ensure_personal_thread(room, chosen_uid)
        personal_msgs = (
            db.collection("rooms").document(room)
            .collection("personal").document(chosen_uid)
            .collection("messages")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .stream()
        )
        for m in personal_msgs:
            render_message_row(m, "admin")
    else:
        st.info("このクラスにはユーザーが登録されていません。")

else:
    # ユーザービュー：
    # 1) ルーム全体（ALL）宛メッセージ
    # 2) 自分の個別スレッド（管理者↔自分）
    # を統合して「自分宛てのタイムライン」として表示
    ensure_personal_thread(room, user_id)

    room_stream = db.collection("rooms").document(room).collection("messages").order_by(
        "timestamp", direction=firestore.Query.DESCENDING
    ).stream()
    personal_stream = db.collection("rooms").document(room).collection("personal").document(user_id).collection("messages").order_by(
        "timestamp", direction=firestore.Query.DESCENDING
    ).stream()

    # Python側で統合＆ソート
    combined = []
    for m in room_stream:
        d = m.to_dict()
        if d.get("type") == "system" and d.get("hidden"):
            continue
        combined.append(("all", m))
    for m in personal_stream:
        d = m.to_dict()
        if d.get("type") == "system" and d.get("hidden"):
            continue
        combined.append(("personal", m))

    # timestamp 降順で並べ替え
    def _ts(x):
        d = x[1].to_dict()
        return d.get("timestamp", firestore.SERVER_TIMESTAMP)

    combined.sort(key=_ts, reverse=True)

    st.caption("👀 あなた宛てのメッセージ")
    for origin, m in combined:
        render_message_row(m, "user")

# ---------------------------
# ログアウト
# ---------------------------
st.sidebar.write("---")
if st.sidebar.button("🚪 ログアウト"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
