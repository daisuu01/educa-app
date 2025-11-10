# =============================================
# unread_guardian_list.py（保護者未読一覧）
# =============================================
import streamlit as st
from firebase_utils import db  # ✅ Cloud／ローカル共通の初期化
from datetime import datetime, timezone
import pytz



# ==================================================
# 👨‍👩‍👧 保護者未読一覧のメイン関数
# ==================================================
def show_unread_guardian_list():
    st.title("👨‍👩‍👧 保護者未読一覧")

    users_ref = db.collection("users").where("role", "==", "student")
    students = {d.id: d.to_dict() for d in users_ref.stream()}

    unread_list = []

    for user_id, user in students.items():
        # 各ユーザーの個人チャットを参照
        msg_ref = (
            db.collection("rooms")
            .document("personal")
            .collection(user_id)
            .document("messages")
            .collection("items")
        )

        # 最新の管理者メッセージのみ取得
        msgs = (
            msg_ref.where("sender", "==", "admin")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )

        for d in msgs:
            m = d.to_dict()
            if not m:
                continue
            read_by = m.get("read_by", [])
            if user_id not in read_by:  # ✅ 未読判定
                unread_list.append({
                    "id": user_id,
                    "name": user.get("name", ""),
                    "class": user.get("class_name", user.get("class_code", "")),
                    "last_message": m.get("message", ""),
                    "timestamp": m.get("timestamp"),
                })

    # --- 結果表示 ---
    if not unread_list:
        st.success("🎉 すべての保護者が既読済みです！")
        return

    jst = pytz.timezone("Asia/Tokyo")

    for u in unread_list:
        ts = u["timestamp"]
        ts_str = ts.astimezone(jst).strftime("%Y-%m-%d %H:%M") if ts else "日時不明"
        st.markdown(
            f"""
            <div style="background:#fff3e0; padding:10px; margin-bottom:6px; border-radius:8px;">
                <b>{u["id"]} {u["name"]}</b>（{u["class"]}）<br>
                🕒 最終送信: {ts_str}<br>
                💬 <i>{u["last_message"][:50]}{'...' if len(u["last_message"])>50 else ''}</i>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.info(f"未読ユーザー数：{len(unread_list)} 名")
