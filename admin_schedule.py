# =============================================
# admin_schedule.py（送信予約＋自動実行）
# =============================================

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, time, timezone
from dotenv import load_dotenv
import os
import pytz
from streamlit_autorefresh import st_autorefresh

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


# ------------------------------------------------
# 🔧 Firestoreに送信予約を保存
# ------------------------------------------------
def save_scheduled_message(target_type, target_id, text, send_at):
    doc = {
        "target_type": target_type,
        "target_id": target_id,
        "text": text,
        "scheduled_at": send_at,
        "sent": False,
        "created_at": datetime.now(timezone.utc),
    }
    db.collection("scheduled_messages").add(doc)


# ------------------------------------------------
# ⏱ Firestoreを定期チェックして予約を送信
# ------------------------------------------------
def process_scheduled_messages():
    """予約メッセージをチェックし、送信時刻が過ぎたら送信実行"""
    now = datetime.now(timezone.utc)
    query = db.collection("scheduled_messages").where("sent", "==", False)
    for doc in query.stream():
        data = doc.to_dict() or {}
        send_at = data.get("scheduled_at")
        if not send_at or send_at > now:
            continue

        try:
            # 🔁 循環import対策：関数内で遅延インポート
            from admin_chat import send_message

            target_type = data.get("target_type")
            target_id = data.get("target_id")
            text = data.get("text", "").strip()
            if not text:
                continue

            # --- 実際の送信処理（履歴に反映される）---
            if target_type == "個人" and target_id:
                send_message("個人", user_id=target_id, text=text)
            elif target_type == "クラス" and target_id:
                send_message("クラス", class_name=target_id, text=text)
            elif target_type == "学年" and target_id:
                send_message("学年", grade=target_id, text=text)
            elif target_type == "全員":
                send_message("全員", text=text)

            # ✅ 送信済み更新（再送防止）
            db.collection("scheduled_messages").document(doc.id).update({
                "sent": True,
                "sent_at": now
            })
            st.info(f"✅ {target_type}宛『{text[:20]}...』を送信しました。")

        except Exception as e:
            st.error(f"送信処理エラー: {e}")


# ------------------------------------------------
# 📅 予約送信画面UI
# ------------------------------------------------
def show_admin_schedule():
    st.title("⏰ メッセージ送信予約")
    st.write("未来の日時を指定してメッセージを予約送信できます。")

    target_type = st.radio("送信対象", ["個人", "クラス", "学年", "全員"])
    target_id = None

    if target_type == "個人":
        target_id = st.text_input("生徒の会員番号を入力")
    elif target_type == "クラス":
        target_id = st.text_input("クラスコードを入力（例: 30A）")
    elif target_type == "学年":
        target_id = st.selectbox("学年を選択", ["中1", "中2", "中3", "高1", "高2", "高3"])

    st.write("---")

    text = st.text_area("メッセージ内容", height=80)

    # 📆 日付・時刻選択（1分刻み）
    date = st.date_input("送信日")
    send_time = st.time_input("送信時刻", value=time(9, 0), step=60)

    # JST → UTC 変換
    jst = pytz.timezone("Asia/Tokyo")
    send_at_jst = datetime.combine(date, send_time)
    send_at = jst.localize(send_at_jst).astimezone(timezone.utc)

    if st.button("📩 予約する", use_container_width=True):
        if not text.strip():
            st.warning("⚠️ メッセージを入力してください。")
        else:
            save_scheduled_message(target_type, target_id, text, send_at)
            st.success(f"✅ {send_at_jst.strftime('%Y-%m-%d %H:%M')} に送信を予約しました。")
            st.balloons()

    # 🔁 定期チェック（10秒ごとに送信判定）
    st_autorefresh(interval=10000, key="schedule_refresh")
    process_scheduled_messages()
