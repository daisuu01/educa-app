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
import json
from streamlit.components.v1 import html as components_html

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
    for d in personal_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream():
        m = d.to_dict()
        if m:
            m["scope"] = "個人"
            m["id"] = d.id
            all_msgs.append(m)

    # ✅ クラス宛て（管理者側の保存パスに合わせる）
    if class_name:
        class_ref = (
            db.collection("rooms")
            .document("class")
            .collection(str(class_name))
            .document("messages")
            .collection("items")
        )
        for d in personal_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream():
            m = d.to_dict()
            if m:
                m["scope"] = "クラス"
                m["_class_name"] = str(class_name)  # ✅ 既読更新で使う
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
        for d in grade_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream():
            m = d.to_dict()
            if m:
                m["scope"] = "学年"
                m["id"] = d.id
                all_msgs.append(m)

    # 全体宛て
    all_ref = db.collection("rooms").document("all").collection("messages")
    for d in all_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream():
        m = d.to_dict()
        if m:
            m["scope"] = "全体"
            m["id"] = d.id
            all_msgs.append(m)

    # タイムスタンプでソート（新しい順）
    all_msgs.sort(key=lambda x: x.get("timestamp", datetime(2000, 1, 1)), reverse=True)
    return all_msgs


# ==================================================
# 🔹 Firestoreへメッセージ送信
# ==================================================
def send_message(user_id: str, actor: str, text: str):
    """
    actor: 'student' or 'guardian' （UIのラジオから決定）
    Firestore保存は sender=user_id, read_by=[user_id] に統一
    """
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
        "message": text.strip(),
        "sender": actor,                     # ✅ 固定ID
        "user_id": user_id,                       # ✅ 表示用（'student'|'guardian'）
        "timestamp": datetime.now(timezone.utc),
        "read_by": [user_id],                  # ✅ 送信者は既読
    })


# ==================================================
# 🔹 既読処理（ユーザー＝このスレのmember_idで統一）
# ==================================================
def mark_user_read(user_id: str, msg: dict):
    """どのスコープでも read_by に user_id を追加"""
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
            # ✅ 管理者側の保存パスに合わせる（class_nameのみ）
            class_name = (class_name_for_display := msg.get("_class_name")) or (class_name_for_display := None)
            # class_nameは取得時に付けていない場合があるため、必要なら引数でもらう設計にしても良い
            # ここでは class_name が無いケースはスキップ
            if not class_name_for_display:
                return
            ref = (
                db.collection("rooms")
                .document("class")
                .collection(str(class_name_for_display))
                .document("messages")
                .collection("items")
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

        ref.update({"read_by": firestore.ArrayUnion([user_id])})  # ✅ user_id を追加
    except Exception as e:
        print("既読処理エラー:", e)


# ==================================================
# 🔹 1件のメッセージ描画（重複回避のため関数化）
# ==================================================
def _render_message(user_id: str, msg: dict):
    sender = msg.get("sender", "")
    actor = msg.get("actor")
    text = msg.get("message", msg.get("text", ""))
    read_by = msg.get("read_by", [])
    ts = msg.get("timestamp")
    ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""

    # ✅ 新旧データ両対応：自分のメッセージ判定を拡張
    self_message = (msg.get("user_id") == user_id)
    

    if self_message:
        sender_label = "👦 生徒" if msg.get("sender") == "student" else "👨‍👩‍👧 保護者"
        admin_read_label = "（既読）" if "admin" in read_by else "（未読）"

        col1, col2 = st.columns([9, 1])
        with col1:
            st.markdown(
                f"""<div style="text-align:right;margin:8px 0;">
                <div style="font-size:0.8em;color:#666;">{sender_label}</div>
                <div style="display:inline-block;background-color:#d2e3fc;
                padding:10px 14px;border-radius:12px;max-width:80%;
                word-wrap:break-word;white-space:pre-wrap;color:#111;">{text}</div>
                <div style="font-size:0.8em;color:#666;">{admin_read_label}　{ts_str}</div>
                </div>""",
                unsafe_allow_html=True
            )
        with col2:
            pass

    # --- 先生（管理者）からのメッセージ（sender=='admin'） ---
    else:
        user_read = (user_id in read_by)
        user_read_label = "✅ 既読" if user_read else ""
        bubble_color = "#f1f3f4" if user_read else "#ffe5e5"
        st.markdown(
            f"""<div style="display:flex;align-items:center;justify-content:flex-start;margin:8px 0;">
            <div style="background-color:{bubble_color};
            padding:10px 14px;border-radius:12px;max-width:80%;
            word-wrap:break-word;white-space:pre-wrap;color:#111;">{text}</div>
            <div style="margin-left:8px;font-size:0.85em;">{user_read_label}</div>
            </div>
            <div style="font-size:0.8em;color:#666;">{ts_str}</div>""",
            unsafe_allow_html=True
        )
        if not user_read:
            if st.button(
                "保護者既読ボタン",
                key=f"user_read_{msg.get('scope','unknown')}_{msg['id']}",
                help="このメッセージを既読にします"
            ):
                mark_user_read(user_id, msg)
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
        recent = messages[:3]      # 新しい3件
        older = messages[3:]       # それ以前

        # ✅ 過去履歴を上部へ
        if older:
            with st.expander(f"📜 過去の履歴を表示（{len(older)}件）"):
                for msg in reversed(older):
                    _render_message(user_id, msg)

        st.markdown("### 📌 直近3件")

        # ✅ 直近3件は「古い→新しい」順で下に新しいメッセージが来るように逆順表示
        for msg in reversed(recent):
            _render_message(user_id, msg)

    st.markdown("---")

    # --- 送信欄 ---
    st.subheader("📨 メッセージ送信")

    # ✅ 送信後の入力クリア処理
    if st.session_state.pop("__clear_chat_input__", False):
        st.session_state.pop("chat_input", None)

    ui_choice = st.radio(
        "送信者を選択してください",
        ["生徒", "保護者"],
        horizontal=True,
        key="sender_radio"
    )

    # ✅ actor に変換
    actor = "student" if ui_choice == "生徒" else "guardian"

    text = st.text_area("メッセージを入力", height=80, key="chat_input")

    col3, col4 = st.columns([3, 1])
    with col4:
        if st.button("送信", use_container_width=True):
            if not text.strip():
                st.warning("⚠️ メッセージを入力してください。")
            else:
                # ✅ Firestore へ user_id と actor を渡す
                send_message(user_id, actor, text)
                st.session_state["__clear_chat_input__"] = True
                st.rerun()

