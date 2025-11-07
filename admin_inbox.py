# =============================================
# admin_inbox.py（管理者用：受信ボックス → 個人チャット遷移対応）
# =============================================

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone
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
# 🔹 生徒一覧を取得
# ==================================================
def get_all_students():
    users_ref = db.collection("users")
    docs = users_ref.stream()
    students = []
    for d in docs:
        user = d.to_dict()
        if user.get("role") == "student":
            students.append({
                "id": d.id,
                "name": f"{user.get('last_name', '')} {user.get('first_name', '')}".strip() or d.id,
                "grade": user.get("grade", ""),
                "class": user.get("class_name", ""),
                "class_code": user.get("class_code", "")
            })
    return students


# ==================================================
# ✅ 未読件数を数える関数（サイドバー表示用）
# ==================================================
def count_unread_messages():
    students = get_all_students()
    unread_count = 0

    for s in students:
        user_id = s["id"]
        ref = (
            db.collection("rooms")
            .document("personal")
            .collection(user_id)
            .document("messages")
            .collection("items")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(1)
        )

        for d in ref.stream():
            msg = d.to_dict()
            if not msg:
                continue
            if msg.get("sender") != "admin":
                read_by = msg.get("read_by", [])
                if "admin" not in read_by:
                    unread_count += 1

    return unread_count


# ==================================================
# 🔹 各生徒の最新受信メッセージを取得
# ==================================================
def get_latest_received_messages():
    students = get_all_students()
    results = []

    for s in students:
        user_id = s["id"]
        ref = (
            db.collection("rooms")
            .document("personal")
            .collection(user_id)
            .document("messages")
            .collection("items")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(1)
        )

        for d in ref.stream():
            msg = d.to_dict()
            if not msg:
                continue

            sender = msg.get("sender", "")
            if sender != "admin":
                read_by = msg.get("read_by", [])
                is_unread = "admin" not in read_by
                results.append({
                    "id": user_id,
                    "name": s["name"],
                    "grade": s["grade"],
                    "class": s["class"],
                    "text": msg.get("message", msg.get("text", "")),
                    "timestamp": msg.get("timestamp"),
                    "is_unread": is_unread,
                    "actor": msg.get("actor"),
                })

    results.sort(key=lambda x: x.get("timestamp", datetime(2000,1,1)), reverse=True)
    return results


# ==================================================
# 🖥️ 管理者用 受信ボックスUI
# ==================================================
def show_admin_inbox():
    st.title("📥 受信ボックス（生徒・保護者からのメッセージ）")
    st.info("最新のメッセージを一覧表示しています。未読は赤色で表示されます。")

    messages = get_latest_received_messages()

    if not messages:
        st.write("📭 現在、受信メッセージはありません。")
        return

    for m in messages:
        name = m["name"]
        grade = m["grade"] or "未設定"
        class_name = m["class"] or "-"
        text = m.get("message", m.get("text", ""))
        ts = m.get("timestamp")
        ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else "日時不明"

        actor = m.get("actor")
        who = "生徒" if actor == "student" else ("保護者" if actor == "guardian" else "生徒/保護者")

        bg_color = "#ffe5e5" if m["is_unread"] else "#f7f7f7"
        border_color = "#ff4d4d" if m["is_unread"] else "#ccc"
        font_weight = "bold" if m["is_unread"] else "normal"

        st.markdown(
            f"""
            <div style="background-color:{bg_color};
                        border-left:6px solid {border_color};
                        padding:10px 14px;
                        border-radius:10px;
                        margin:8px 0;">
                <div style="font-size:1.05em;font-weight:{font_weight};">
                    🧑‍🎓 {name}（{grade}・{class_name}） <span style="font-size:0.9em;color:#666;">— {who} から</span>
                </div>
                <div style="color:#333;margin-top:4px;">{text}</div>
                <div style="font-size:0.85em;color:#666;margin-top:6px;">📅 {ts_str}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("開く ▶", key=f"open_{m['id']}"):
                st.session_state["selected_student_id"] = m["id"]
                st.session_state["selected_student_name"] = m["name"]
                st.session_state["admin_mode"] = "チャット管理"
                st.session_state["just_opened_from_inbox"] = True
                st.rerun()
