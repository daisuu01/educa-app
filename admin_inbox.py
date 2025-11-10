# =============================================
# admin_inbox.py（改良版：既読も一覧に残るメール型受信ボックス）
# =============================================

import streamlit as st
from datetime import datetime, timezone
import pytz

# ✅ Firebase は共通モジュールから利用
from firebase_utils import db


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

    # ✅ 現在ログインしている管理者のIDを取得
    current_admin_id = st.session_state.get("member_id")

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
                # ✅ 固定文字 "admin" → 現在の管理者ID で判定
                if current_admin_id and current_admin_id not in read_by:
                    unread_count += 1

    return unread_count



# ==================================================
# 🔹 各生徒の最新メッセージ（既読・未読どちらも）を取得
# ==================================================
def get_latest_received_messages():
    students = get_all_students()
    current_admin_id = st.session_state.get("member_id")
    results = []

    for s in students:
        user_id = s["id"]
        # 最新50件くらい取る（未読＋既読含む）
        ref = (
            db.collection("rooms")
            .document("personal")
            .collection(user_id)
            .document("messages")
            .collection("items")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(50)
        )

        for d in ref.stream():
            msg = d.to_dict()
            if not msg:
                continue

            sender = msg.get("sender", "")
            if sender in ["student", "生徒", "guardian", "保護者"]:
                read_by = msg.get("read_by", [])
                current_admin_id = st.session_state.get("member_id")
                is_unread = current_admin_id not in read_by if current_admin_id else False
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
                # ✅ 最新1件だけ採用（生徒・保護者別けずに最後のメッセージ）
                break

    # ✅ 最新順でソート
    results.sort(key=lambda x: x.get("timestamp", datetime(2000,1,1)), reverse=True)
    return results


# ==================================================
# 🖥️ 管理者用 受信ボックスUI（既読も残る）
# ==================================================
def show_admin_inbox():
    st.title("📥 受信ボックス（生徒・保護者からのメッセージ）")
    st.caption("未読は赤色、既読はグレーで表示されます。")

    messages = get_latest_received_messages()

    if not messages:
        st.info("📭 現在、受信メッセージはありません。")
        return

    for m in messages:
        name = m["name"]
        grade = m["grade"] or "未設定"
        class_name = m["class"] or "-"
        text = m.get("text", "")
        ts = m.get("timestamp")

        jst = pytz.timezone("Asia/Tokyo")
        ts_jst = ts.astimezone(jst) if ts else None
        ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else "日時不明"

        actor = m.get("actor")
        who = "生徒" if actor == "student" else ("保護者" if actor == "guardian" else "生徒/保護者")

        # ✅ 未読／既読でスタイル分け
        if m["is_unread"]:
            bg_color = "#ffe5e5"
            border_color = "#ff4d4d"
            font_weight = "bold"
            opacity = "1.0"
        else:
            bg_color = "#f0f0f0"
            border_color = "#999"
            font_weight = "normal"
            opacity = "0.75"

        st.markdown(
            f"""
            <div style="background-color:{bg_color};
                        border-left:6px solid {border_color};
                        padding:10px 14px;
                        border-radius:10px;
                        margin:8px 0;
                        opacity:{opacity};">
                <div style="font-size:1.05em;font-weight:{font_weight};color:#222;">
                    🧑‍🎓 {name}（{grade}・{class_name}）
                    <span style="font-size:0.9em;color:#555;">— {who} から</span>
                </div>
                <div style="color:#333;margin-top:4px;">{text}</div>
                <div style="font-size:0.85em;color:#666;margin-top:6px;">📅 {ts_str}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 開くボタン
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("開く ▶", key=f"open_{m['id']}"):
                # ✅ 開いても削除せず残す仕様
                st.session_state["selected_student_id"] = m["id"]
                st.session_state["selected_student_name"] = m["name"]
                st.session_state["admin_mode"] = "チャット管理"
                st.session_state["just_opened_from_inbox"] = True
                st.rerun()
