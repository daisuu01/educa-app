# =============================================
# admin_schedule.py（管理者用：メッセージ送信予約）
# =============================================

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, time, timezone
from dotenv import load_dotenv
import os

# --- Firebase 初期化 ---
load_dotenv()
firebase_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

if not firebase_admin._apps:
    if not firebase_path or not os.path.exists(firebase_path):
        st.error("Firebase認証ファイルが見つかりません。")
        st.stop()
    cred = credentials.Certificate(firebase_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()


# ------------------------------------------------
# 🔧 Firestoreに送信予約を保存
# ------------------------------------------------
def save_scheduled_message(target_type, target_id, text, send_at):
    doc = {
        "target_type": target_type,      # 個人 / クラス / 学年 / 全員
        "target_id": target_id,          # user_id or class_code or None
        "text": text,                    # ← 修正 (message → text)
        "scheduled_at": send_at,         # ← 修正 (send_at → scheduled_at)
        "sent": False,
        "created_at": datetime.now(timezone.utc),
    }
    db.collection("scheduled_messages").add(doc)


# ------------------------------------------------
# 📅 予約送信画面UI
# ------------------------------------------------
def show_admin_schedule():
    st.title("⏰ メッセージ送信予約")

    st.write("未来の日時を指定してメッセージを予約送信できます。")

    # 対象選択
    target_type = st.radio("送信対象", ["個人", "クラス", "学年", "全員"])

    target_id = None

    # 個人向け
    if target_type == "個人":
        target_id = st.text_input("生徒の会員番号を入力")

    # クラス向け
    elif target_type == "クラス":
        target_id = st.text_input("クラスコードを入力（例: 30A）")

    # 学年向け
    elif target_type == "学年":
        target_id = st.selectbox("学年を選択", ["中1", "中2", "中3", "高1", "高2", "高3"])

    st.write("---")

    text = st.text_area("メッセージ内容", height=80)

    # 日付・時刻入力
    date = st.date_input("送信日")
    send_time = st.time_input("送信時刻", value=time(9, 0))

    # JST → UTC に変換
    import pytz
    jst = pytz.timezone("Asia/Tokyo")
    send_at = jst.localize(datetime.combine(date, send_time)).astimezone(timezone.utc)

    # 日時を結合
    send_at = datetime.combine(date, send_time, tzinfo=timezone.utc)

    if st.button("📩 予約する", use_container_width=True):
        if not text.strip():
            st.warning("メッセージを入力してください。")
        else:
            save_scheduled_message(target_type, target_id, text, send_at)
            st.success("送信予約を登録しました。")
            st.balloons()
