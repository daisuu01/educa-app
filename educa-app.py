# =============================================
# 🎓 educa-app.py（完全動作版：返信・送信・ALL履歴・スタンプ同期）
# =============================================

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from google.cloud.firestore_v1 import FieldFilter
from dotenv import load_dotenv
import os
from datetime import datetime, timezone

# ---------------------------
# Firebase 初期化
# ---------------------------

load_dotenv()
firebase_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

if not firebase_path or not os.path.exists(firebase_path):
    st.error(f"❌ Firebase認証ファイルが見つかりません: {firebase_path}")
    st.stop()

# ✅ ここがポイント：すでに初期化済みでなければ実行
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_path)
    firebase_admin.initialize_app(cred)

# すでに初期化済みなら再利用
app = firebase_admin.get_app()
db = firestore.client(app)


# ---------------------------
# ページ設定
# ---------------------------
st.set_page_config(page_title="Educa Chat", layout="wide")
st.title("💬 Educa Chat")

# ---------------------------
# セッション初期化
# ---------------------------
for key in ["user_id", "user_name", "user_class", "role", "user_type"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ---------------------------
# Firestore補助関数
# ---------------------------
def ensure_room_doc(name: str):
    """ルームが存在しない場合に作成"""
    ref = db.collection("rooms").document(name)
    if not ref.get().exists:
        ref.set({"_init": True}, merge=True)

def ensure_personal_thread(grade: str, user_id: str):
    """個人スレッドが存在しない場合に作成"""
    ensure_room_doc(grade)
    ref = db.collection("rooms").document(grade).collection("personal").document(user_id)
    if not ref.get().exists:
        ref.set({"_createdAt": firestore.SERVER_TIMESTAMP}, merge=True)

def send_message(path: list, sender: str, msg: str, msg_type="text"):
    """メッセージ送信（パスの末尾がコレクションかドキュメントかを自動判定）"""
    ref = db
    for i, p in enumerate(path):
        # 奇数番目の要素がドキュメント名（例: rooms→doc→collection→doc）
        ref = ref.collection(p) if i % 2 == 0 else ref.document(p)

    # 最後の要素がコレクション名の場合は add()、ドキュメント名の場合はその下の messages に add()
    try:
        # CollectionReference なら add() が使える
        ref.add({
            "sender": sender,
            "message": msg,
            "type": msg_type,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except AttributeError:
        # DocumentReference だった場合はその下の messages に追加
        ref.collection("messages").add({
            "sender": sender,
            "message": msg,
            "type": msg_type,
            "timestamp": firestore.SERVER_TIMESTAMP
        })

# ---------------------------
# 既読管理関数
# ---------------------------
def mark_as_read(ref, message_id: str, user_id: str):
    """ユーザーがメッセージを開いたら既読を登録"""
    try:
        msg_ref = ref.document(message_id)
        msg = msg_ref.get()
        if msg.exists:
            data = msg.to_dict()
            read_by = data.get("read_by", [])
            if user_id not in read_by:
                read_by.append(user_id)
                msg_ref.update({"read_by": read_by})
    except Exception as e:
        print("mark_as_read error:", e)

# ---------------------------
# 未読件数カウント関数
# ---------------------------

def count_unread_messages(ref, user_id: str):
    """指定スレッドでの未読件数をカウント"""
    try:
        msgs = ref.stream()
        count = 0
        for m in msgs:
            d = m.to_dict()
            read_by = d.get("read_by", [])
            if user_id not in read_by:
                count += 1
        return count
    except Exception as e:
        print("count_unread_messages error:", e)
        return 0


def get_users_by_grade(grade: str):
    q = db.collection("users").where(filter=FieldFilter("class", "==", grade))
    return list(q.stream())

def display_messages(ref):
    """単一ルームのメッセージ表示（既読付き）"""
    msgs = ref.order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
    st.write("---")
    for m in msgs:
        d = m.to_dict()
        msg_id = m.id

        # === 既読人数を算出 ===
        read_by = d.get("read_by", [])
        if len(read_by) > 1:
            read_status = f" {len(read_by)}人既読"
        elif len(read_by) == 1:
            read_status = " 1人既読"
        else:
            read_status = "🔵 未読"

        # === メッセージ表示 ===
        if d.get("type") == "stamp":
          st.markdown(
             f"**{d.get('sender')}**：<br><img src='{d.get('message')}' width='60'>（{read_status}）",
             unsafe_allow_html=True,
        )
    else:
        st.markdown(f"**{d.get('sender')}**：{d.get('message')}　（{read_status}）")

        st.divider()


def display_messages_from_refs(ref_list, limit=100):
    """複数ルームを結合して時系列表示（既読ボタン付き）"""
    buffer = []
    for ref in ref_list:
        try:
            for m in ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream():
                d = m.to_dict()
                ts = d.get("timestamp") or datetime(1970, 1, 1, tzinfo=timezone.utc)
                buffer.append((ts, d, ref, m.id))
        except Exception:
            continue
    buffer.sort(key=lambda x: x[0], reverse=True)

    st.write("---")
    for _, d, ref, msg_id in buffer:
        read_by = d.get("read_by", [])
        is_read = st.session_state.user_id in read_by

        # === メッセージ表示部分 ===
        col1, col2 = st.columns([5, 1])
        with col1:
            if d.get("type") == "stamp":
                st.markdown(
                    f"**{d.get('sender')}**：<br><img src='{d.get('message')}' width='60'>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"**{d.get('sender')}**：{d.get('message')}")

            # 読まれた人数表示
            if len(read_by) > 0:
                st.caption(f"👀 既読 {len(read_by)}名")

        with col2:
            # 既読ボタン
            if not is_read:
                if st.button("✅ 既読", key=f"read_{msg_id}"):
                    mark_as_read(ref, msg_id, st.session_state.user_id)
                    st.rerun()
            else:
                st.markdown("✔️ 既読")

        st.divider()



# ---------------------------
# スタンプ定義
# ---------------------------
STAMPS = {
    "😊": "https://cdn-icons-png.flaticon.com/512/742/742751.png",
    "👍": "https://cdn-icons-png.flaticon.com/512/2107/2107957.png",
    "❤️": "https://cdn-icons-png.flaticon.com/512/833/833472.png",
    "🎉": "https://cdn-icons-png.flaticon.com/512/1973/1973960.png",
}

# ---------------------------
# ログイン画面
# ---------------------------
if st.session_state.user_id is None:
    st.subheader("🔐 ログインしてください")

    role = st.radio("ログイン種別を選択", ["👨‍🏫 管理者", "🎓 ユーザー"], horizontal=True)

    if role == "👨‍🏫 管理者":
        if st.button("管理者としてログイン"):
            st.session_state.role = "admin"
            st.session_state.user_name = "管理者"
            st.session_state.user_id = "admin"
            st.success("管理者としてログインしました。")
            st.rerun()

    elif role == "🎓 ユーザー":
        st.subheader("🎓 生徒・保護者ログイン")

    # ここでログイン区分を選択
        login_type = st.radio("ログイン区分を選択", ["生徒", "保護者"], horizontal=True)
        user_type = "生徒" if "生徒" in login_type else "保護者"

        user_id = st.text_input("会員番号", placeholder="例：S12345")
        password = st.text_input("パスワード", type="password")

        if st.button("ログイン"):
            doc = db.collection("users").document(user_id).get()
            if not doc.exists:
                st.error("会員番号が登録されていません。")
                st.stop()

            data = doc.to_dict()
            if data.get("password") != password:
                st.error("パスワードが正しくありません。")
                st.stop()

        # ✅ ログイン情報をセッションに保存
            st.session_state.role = "user"
            st.session_state.user_id = user_id
            st.session_state.user_name = data.get("name", "名無し")
            st.session_state.user_class = data.get("class", "未設定")
            st.session_state.user_type = user_type

            st.success(f"{user_type}として {st.session_state.user_name} さんでログインしました。")
            #st.rerun()
            #st.stop()

# ✅ ログイン完了後に次の画面を表示
if st.session_state.get("login_done"):
    st.info("✅ ログイン完了しました。メイン画面を読み込み中...")
    # ここで return せず次のセクションが自然に実行される
else:
    st.stop()

# ---------------------------
# 共通変数
# ---------------------------
role = st.session_state.role
user_name = st.session_state.user_name
user_id = st.session_state.user_id
user_class = st.session_state.user_class

# ======================================================
# 管理者画面
# ======================================================
if role == "admin":
    mode = st.sidebar.radio("メニュー", ["💬 チャット", "🗂 会員登録"], label_visibility="collapsed")

    # 💬 チャットモード
    if mode == "💬 チャット":
        chat_mode = st.sidebar.radio("チャットモード", ["📤 送信", "💬 返信"], label_visibility="collapsed")

        # ======================
        # 🔔 未読メッセージ数表示（管理者）
        # ======================
        st.sidebar.write("### 🔔 未読メッセージ")

        ref_all = db.collection("rooms").document("ALL").collection("messages")
        unread_all = count_unread_messages(ref_all, user_id)
        st.sidebar.write(f"📢 全体：{unread_all}件")

        # 各学年ルーム
        for grade in ["中1","中2","中3","高1","高2","高3"]:
            ref_grade = db.collection("rooms").document(grade).collection("messages")
            unread_grade = count_unread_messages(ref_grade, user_id)
            st.sidebar.write(f"🏫 {grade}：{unread_grade}件")

        # 個人スレッド（管理者専用）
        st.sidebar.write("### 👤 個人スレッド未読")
        users_ref = db.collection("users").stream()
        for u in users_ref:
            uid = u.id
            name = u.to_dict().get("name", "")
            cls = u.to_dict().get("class", "")
            ref_personal = (
                db.collection("rooms")
                .document(cls)
                .collection("personal")
                .document(uid)
                .collection("messages")
            )
            unread_personal = count_unread_messages(ref_personal, user_id)
            if unread_personal > 0:
                st.sidebar.write(f"　📩 {cls}｜{name}：{unread_personal}件")

        # ======== 📤 送信 ========
        if chat_mode == "📤 送信":
            send_target = st.sidebar.radio("送信対象", ["全員に送信", "学年ごとに送信", "個人に送信"])

            def message_input_ui(target_path, title):
                st.subheader(title)
                msg = st.text_input("本文", key=f"input_{'_'.join(target_path)}")
                col1, col2 = st.columns([3, 2])
                with col1:
                    if st.button("📨 送信", key=f"send_{'_'.join(target_path)}"):
                        if msg.strip():
                            send_message(target_path, "講師", msg)
                            st.success("送信しました！")
                            st.rerun()
                        else:
                            st.warning("本文を入力してください。")
                with col2:
                    with st.popover("😊 スタンプ"):
                        cols = st.columns(4)
                        for i, (emoji, url) in enumerate(STAMPS.items()):
                            with cols[i % 4]:
                                if st.button(emoji, key=f"stamp_{emoji}_{'_'.join(target_path)}"):
                                    send_message(target_path, "講師", url, "stamp")
                                    st.rerun()
                ref = db
                for i, p in enumerate(target_path):
                    ref = ref.collection(p) if i % 2 == 0 else ref.document(p)
                st_autorefresh(interval=5000)
                display_messages(ref.collection("messages"))

            if send_target == "全員に送信":
                message_input_ui(["rooms", "ALL"], "📢 全員に送信")
            elif send_target == "学年ごとに送信":
                grade = st.sidebar.selectbox("学年を選択", ["中1","中2","中3","高1","高2","高3"])
                message_input_ui(["rooms", grade], f"📢 {grade} に送信")
            elif send_target == "個人に送信":
                grade = st.sidebar.selectbox("学年を選択", ["中1","中2","中3","高1","高2","高3"])
                users = get_users_by_grade(grade)
                if not users:
                    st.info(f"{grade} に登録されたユーザーはいません。")
                else:
                    choices = [f"{u.id}｜{u.to_dict().get('name','')}" for u in users]
                    selected = st.sidebar.selectbox("ユーザーを選択", choices)
                    uid = users[choices.index(selected)].id
                    message_input_ui(["rooms", grade, "personal", uid], f"📩 {selected} に送信")

        # ======== 💬 返信 ========
        elif chat_mode == "💬 返信":
            st.subheader("💬 返信モード（個人スレッド）")

            grade = st.sidebar.selectbox("学年を選択", ["中1","中2","中3","高1","高2","高3"])
            users = get_users_by_grade(grade)
            if not users:
                st.info("該当学年にユーザーがいません。")
            else:
                choices = [f"{u.id}｜{u.to_dict().get('name','')}" for u in users]
                selected = st.sidebar.selectbox("ユーザーを選択", choices)
                uid = users[choices.index(selected)].id

                ref_path = ["rooms", grade, "personal", uid]
                ref = db.collection("rooms").document(grade).collection("personal").document(uid).collection("messages")

                st.markdown(f"### 🗂 {selected} とのやり取り")
                st_autorefresh(interval=5000)
                ref_all = db.collection("rooms").document("ALL").collection("messages")
                ref_grade = db.collection("rooms").document(grade).collection("messages")
                ref_personal = (
                    db.collection("rooms").document(grade)
                    .collection("personal").document(uid)
                    .collection("messages")
                )
                display_messages_from_refs([ref_all, ref_grade, ref_personal], limit=100)

                msg = st.text_input("返信本文", key=f"reply_msg_{uid}")
                if st.button("📨 返信送信", key=f"send_reply_{uid}"):
                    if msg.strip():
                        send_message(ref_path, "講師", msg)
                        st.rerun()
                    else:
                        st.warning("本文を入力してください。")

                with st.popover("😊 スタンプ"):
                    cols = st.columns(4)
                    for i, (e, url) in enumerate(STAMPS.items()):
                        with cols[i % 4]:
                            if st.button(e, key=f"reply_stamp_{e}_{uid}"):
                                send_message(ref_path, "講師", url, "stamp")
                                st.rerun()

    # 🗂 会員登録モード
    elif mode == "🗂 会員登録":
        st.subheader("🗂 会員登録モード")
        file = st.file_uploader("ユーザー情報Excelをアップロード", type=["xlsx"])
        if file:
            df = pd.read_excel(file)
            st.dataframe(df)
            if st.button("📤 Firestoreに登録"):
                for _, row in df.iterrows():
                    user_id_x = str(row["user_id"])
                    db.collection("users").document(user_id_x).set({
                        "name": row["name"],
                        "class": row["class"],
                        "password": str(row["password"])
                    })
                    ensure_personal_thread(row["class"], user_id_x)
                st.success("✅ 登録が完了しました！")

# ======================================================
# ユーザー画面
# ======================================================
else:
    #st.subheader("✉️ 管理者にメッセージを送る（他ユーザーには非表示）")

    # ---------------------------
    # 🔔 未読メッセージ数表示（ユーザー）
    # ---------------------------
    ref_all = db.collection("rooms").document("ALL").collection("messages")
    ref_grade = db.collection("rooms").document(user_class).collection("messages")
    ref_personal = (
        db.collection("rooms").document(user_class)
        .collection("personal")
        .document(user_id)
        .collection("messages")
    )

    # 各スレッドの未読件数を取得
    unread_all = count_unread_messages(ref_all, user_id)
    unread_grade = count_unread_messages(ref_grade, user_id)
    unread_personal = count_unread_messages(ref_personal, user_id)

    # 合計件数
    total_unread = unread_all + unread_grade + unread_personal

    # 未読がある場合のみ表示
    if total_unread > 0:
        st.markdown(f"### 🔔 未読メッセージ（{total_unread}件）")
        st.write("---")



    sender_label = f"{st.session_state.user_type}：{user_name}"
    ensure_personal_thread(user_class, user_id)

    msg = st.text_input("本文（管理者宛）")
    if st.button("📨 送信"):
        if msg.strip():
            send_message(["rooms", user_class, "personal", user_id], sender_label, msg)
            st.rerun()
        else:
            st.warning("本文を入力してください。")

    st.write("---")
    st.markdown("### 🗂 あなた宛てのメッセージ")
    st_autorefresh(interval=5000)
    ref_all = db.collection("rooms").document("ALL").collection("messages")
    ref_grade = db.collection("rooms").document(user_class).collection("messages")
    ref_personal = (
        db.collection("rooms").document(user_class)
        .collection("personal").document(user_id)
        .collection("messages")
    )
    display_messages_from_refs([ref_all, ref_grade, ref_personal], limit=100)

# ---------------------------
# ログアウト
# ---------------------------
st.sidebar.write("---")
if st.sidebar.button("🚪 ログアウト"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()
