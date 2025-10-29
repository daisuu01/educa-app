# =============================================
# user_chat.py（直近3件だけ表示＋それ以前は折りたたみで全表示）
# =============================================

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh
from dotenv import load_dotenv
import os

# --- Firebase 初期化 ---
load_dotenv()
firebase_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

if not firebase_admin._apps:
    if not firebase_path or not os.path.exists(firebase_path):
        st.error("❌ Firebase認証ファイルが見つかりません。")
        st.stop()
    cred = credentials.Certificate(firebase_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()


# ==================================================
# 🔹 Firestoreから学年・クラス情報を取得
# ==================================================
def get_user_meta(user_id: str):
    doc = db.collection("users").document(user_id).get()
    if doc.exists:
        u = doc.to_dict()
        return u.get("grade"), u.get("class_name")
    return None, None


# ==================================================
# 🔹 メッセージ取得（全員・学年・クラス・個人 全て統合）
# ==================================================
def get_all_messages(user_id: str, grade: str, class_name: str, limit: int = 50):
    """個人＋クラス＋学年＋全体宛てメッセージを統合して取得"""
    all_msgs = []

    # 個人宛て
    personal_ref = (
        db.collection("rooms")
        .document("personal")
        .collection(user_id)
        .document("messages")
        .collection("items")
    )
    for d in personal_ref.order_by("timestamp", direction=firestore.Query.ASCENDING).limit(limit).stream():
        m = d.to_dict()
        if m:
            m["scope"] = "個人"
            m["id"] = d.id
            all_msgs.append(m)

    # クラス宛て（学年＋クラス名両方揃っている場合）
    if grade and class_name:
        class_ref = (
            db.collection("rooms")
            .document("class")
            .collection(grade)
            .document(class_name)
            .collection("messages")
        )
        for d in class_ref.order_by("timestamp", direction=firestore.Query.ASCENDING).limit(limit).stream():
            m = d.to_dict()
            if m:
                m["scope"] = "クラス"
                m["id"] = d.id
                all_msgs.append(m)

    # 学年宛て
    if grade:
        grade_ref = (
            db.collection("rooms")
            .document("grade")
            .collection(grade)
            .document("messages")
            .collection("items")
        )
        for d in grade_ref.order_by("timestamp", direction=firestore.Query.ASCENDING).limit(limit).stream():
            m = d.to_dict()
            if m:
                m["scope"] = "学年"
                m["id"] = d.id
                all_msgs.append(m)

    # 全体宛て
    all_ref = (
        db.collection("rooms")
        .document("all")
        .collection("messages")
    )
    for d in all_ref.order_by("timestamp", direction=firestore.Query.ASCENDING).limit(limit).stream():
        m = d.to_dict()
        if m:
            m["scope"] = "全体"
            m["id"] = d.id
            all_msgs.append(m)

    # タイムスタンプでソート（新しい順）
    all_msgs.sort(key=lambda x: x.get("timestamp", datetime(2000, 1, 1)), reverse=True)
    return all_msgs

# ==================================================
# 🔹 メッセージ削除関数（ユーザー専用）
# ==================================================
def delete_message(user_id: str, msg: dict):
    """自分の送信メッセージを削除"""
    try:
        msg_id = msg.get("id")
        scope = msg.get("scope")

        if scope == "個人":
            ref = (
                db.collection("rooms")
                .document("personal")
                .collection(user_id)
                .document("messages")
                .collection("items")
                .document(msg_id)
            )
        elif scope == "クラス":
            grade, class_name = get_user_meta(user_id)
            ref = (
                db.collection("rooms")
                .document("class")
                .collection(grade or "未設定")
                .document(class_name or "未設定")
                .collection("messages")
                .document(msg_id)
            )
        elif scope == "学年":
            grade, _ = get_user_meta(user_id)
            ref = (
                db.collection("rooms")
                .document("grade")
                .collection(grade or "未設定")
                .document("messages")
                .collection("items")
                .document(msg_id)
            )
        else:
            ref = db.collection("rooms").document("all").collection("messages").document(msg_id)

        ref.delete()
    except Exception as e:
        print("削除エラー:", e)

# ==================================================
# 🔹 Firestoreへメッセージ送信
# ==================================================
def send_message(user_id: str, sender_role: str, text: str):
    if not text.strip():
        return
    ref = (
        db.collection("rooms")
        .document("personal")
        .collection(user_id)
        .document("messages")
        .collection("items")
    )
    ref.add({
        "text": text.strip(),
        "sender": sender_role,
        "timestamp": datetime.now(timezone.utc),
        "read_by": [sender_role],
    })


# ==================================================
# 🔹 保護者既読処理（個人宛・全体宛いずれも対応）
# ==================================================
def mark_guardian_read(user_id: str, msg: dict):
    """どのスコープでも read_by に student_保護者 を追加"""
    try:
        scope = msg.get("scope")
        msg_id = msg.get("id")

        if scope == "個人":
            ref = (
                db.collection("rooms")
                .document("personal")
                .collection(user_id)
                .document("messages")
                .collection("items")
                .document(msg_id)
            )
        elif scope == "クラス":
            grade, class_name = get_user_meta(user_id)
            ref = (
                db.collection("rooms")
                .document("class")
                .collection(grade or "未設定")
                .document(class_name or "未設定")
                .collection("messages")
                .document(msg_id)
            )
        elif scope == "学年":
            grade, _ = get_user_meta(user_id)
            ref = (
                db.collection("rooms")
                .document("grade")
                .collection(grade or "未設定")
                .document("messages")
                .collection("items")
                .document(msg_id)
            )
        else:  # 全体宛て
            ref = (
                db.collection("rooms")
                .document("all")
                .collection("messages")
                .document(msg_id)
            )

        ref.update({"read_by": firestore.ArrayUnion(["student_保護者"])})
    except Exception as e:
        print("既読処理エラー:", e)


# ==================================================
# 🔹 1件のメッセージ描画（重複回避のため関数化）
# ==================================================
def _render_message(user_id: str, msg: dict):
    sender = msg.get("sender", "")
    text = msg.get("text", "")
    read_by = msg.get("read_by", [])
    ts = msg.get("timestamp")
    ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""

    # --- 自分の送信（生徒/保護者） ---
    if sender.startswith("student"):
        sender_label = "👦 生徒" if sender == "student_生徒" else "👨‍👩‍👧 保護者"
        read_label = "（既読）" if "admin" in read_by else "（未読）"

        col1, col2 = st.columns([9, 1])
        with col1:
            st.markdown(
                f"""<div style="text-align:right;margin:8px 0;">
                <div style="font-size:0.8em;color:#666;">{sender_label}</div>
                <div style="display:inline-block;background-color:#d2e3fc;
                padding:10px 14px;border-radius:12px;max-width:80%;
                word-wrap:break-word;white-space:pre-wrap;color:#111;">{text}</div>
                <div style="font-size:0.8em;color:#666;">{read_label}　{ts_str}</div>
                </div>""",
                unsafe_allow_html=True
            )
        with col2:
            msg_id = msg.get("id")
            if msg_id:
                st.markdown(
                    f"""
                    <style>
                    div[data-testid="stButton"][key="del_user_{msg_id}"] button {{
                        background-color: transparent !important;
                        color: #666 !important;
                        border: none !important;
                        padding: 0 !important;
                        font-size: 0.75em !important;
                        text-decoration: none !important;
                        cursor: pointer !important;
                    }}
                    div[data-testid="stButton"][key="del_user_{msg_id}"] button:hover {{
                        color: #000 !important;
                        text-decoration: underline !important;
                    }}
                    </style>
                    """,
                    unsafe_allow_html=True
                )

                if st.button("🗑️削除", key=f"del_user_{msg_id}", help="このメッセージを削除"):
                    delete_message(user_id, msg)
                    st.rerun()

    # --- 先生からのメッセージ ---
    else:
        guardian_read = "✅ 保護者既読" if "student_保護者" in read_by else ""
        bubble_color = "#ffe5e5" if not guardian_read else "#f1f3f4"
        st.markdown(
            f"""<div style="display:flex;align-items:center;justify-content:flex-start;margin:8px 0;">
            <div style="background-color:{bubble_color};
            padding:10px 14px;border-radius:12px;max-width:80%;
            word-wrap:break-word;white-space:pre-wrap;color:#111;">{text}</div>
            <div style="margin-left:8px;font-size:0.85em;">{guardian_read}</div>
            </div>
            <div style="font-size:0.8em;color:#666;">{ts_str}</div>""",
            unsafe_allow_html=True
        )
        if "student_保護者" not in read_by:
            if st.button("保護者既読", key=f"guardian_read_{msg['id']}", help="このメッセージを既読にする"):
                mark_guardian_read(user_id, msg)
                st.rerun()



# ==================================================
# 🔹 チャットUI
# ==================================================
def show_chat_page(user_id: str, grade: str = None, class_name: str = None):
    st.title("💬 チャット（先生との1対1）")

    st_autorefresh(interval=5000, key="chat_refresh")

    messages = get_all_messages(user_id, grade, class_name)
    if not messages:
        st.info("まだメッセージはありません。")
    else:
        # ✅ 新しい順で来ているので「直近3件」は先頭3件とする（最小修正）
        recent = messages[:3]
        older = messages[3:]

        # 直近3件
        for msg in recent:
            _render_message(user_id, msg)

        # それ以前の履歴は折りたたみ
        if older:
            with st.expander(f"過去の履歴を表示（{len(older)}件）"):
                for msg in older:
                    _render_message(user_id, msg)

    st.markdown("---")

    # --- 送信欄 ---
    st.subheader("📨 メッセージ送信")

    # ✅ 送信後に安全に入力をクリア（ウィジェット生成前に処理）
    if st.session_state.pop("__clear_chat_input__", False):
        st.session_state.pop("chat_input", None)

    sender_role = st.radio(
        "送信者を選択してください",
        ["生徒", "保護者"],
        horizontal=True,
        key="sender_radio"
    )

    text = st.text_area("メッセージを入力", height=80, key="chat_input")

    col3, col4 = st.columns([3, 1])
    with col4:
        if st.button("送信", use_container_width=True):
            if not sender_role:
                st.warning("⚠️ 『生徒』または『保護者』を選択してください。")
            elif not text.strip():
                st.warning("⚠️ メッセージを入力してください。")
            else:
                role_key = f"student_{sender_role}"
                send_message(user_id, role_key, text)
                # ✅ 直接 chat_input をいじらずフラグだけ立てる（最小修正）
                st.session_state["__clear_chat_input__"] = True
                st.rerun()
