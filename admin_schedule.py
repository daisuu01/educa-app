# =============================================
# admin_schedule.py（送信予約＋自動実行）
# =============================================

import streamlit as st
from datetime import datetime, time, timezone
import pytz
from streamlit_autorefresh import st_autorefresh

# ✅ Firebase は共通ユーティリティから利用
from firebase_utils import db


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

    # 📆 日付
    date = st.date_input("送信日")

    # 🕒 時・分（10分刻み）
    col1, col2 = st.columns(2)
    with col1:
        hour = st.selectbox("送信時刻（時）", list(range(0, 24)), index=9)
    with col2:
        minute = st.selectbox("送信時刻（分 / 10分刻み）", [0, 10, 20, 30, 40, 50])

    # JST → UTC 変換
    jst = pytz.timezone("Asia/Tokyo")
    send_at_jst = datetime.combine(date, datetime.min.time()).replace(
        hour=hour, minute=minute
    )
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

# ------------------------------------------------
# 📋 送信予約メール一覧表示（未送信のみ）
# ------------------------------------------------
def show_admin_schedule():
    st.title("⏰ メッセージ送信予約")
    st.write("未来の日時を指定してメッセージを予約送信できます。")

    # --- 送信対象 ---
    target_type = st.radio("送信対象", ["個人", "クラス", "学年", "全員"])
    target_id = None

    if target_type == "個人":
        target_id = st.text_input("生徒の会員番号を入力")
    elif target_type == "クラス":
        target_id = st.text_input("クラスコードを入力（例: 30A）")
    elif target_type == "学年":
        target_id = st.selectbox("学年を選択", ["中1", "中2", "中3", "高1", "高2", "高3"])

    st.write("---")

    # --- メッセージ入力 ---
    text = st.text_area("メッセージ内容", height=80)

    # --- 送信日 ---
    date = st.date_input("送信日")

    # ================================================
    # 🕒 時・分を「枠付きボックス」で入力（number_input）
    # ================================================
    st.write("送信時刻")

    col1, col2 = st.columns([1, 1])

    with col1:
        hour = st.number_input(
            "時",
            min_value=0,
            max_value=23,
            value=9,
            step=1,
            format="%02d"
        )

    with col2:
        minute = st.number_input(
            "分",
            min_value=0,
            max_value=59,
            value=0,
            step=10,
            format="%02d"
        )

    # JST → UTC 変換
    jst = pytz.timezone("Asia/Tokyo")
    send_at_jst = datetime.combine(date, datetime.min.time()).replace(
        hour=int(hour),
        minute=int(minute)
    )
    send_at = jst.localize(send_at_jst).astimezone(timezone.utc)

    # --- 予約ボタン ---
    if st.button("📩 予約する", use_container_width=True):
        if not text.strip():
            st.warning("⚠️ メッセージを入力してください。")
        else:
            save_scheduled_message(target_type, target_id, text, send_at)
            st.success(f"✅ {send_at_jst.strftime('%Y-%m-%d %H:%M')} に送信を予約しました。")
            st.balloons()

    # --- 自動チェック（10秒ごと） ---
    st_autorefresh(interval=10000, key="schedule_refresh")
    process_scheduled_messages()



# =============================================
# メインエントリーポイント（変更なし）
# =============================================
def show_schedule_main():
    tab1, tab2 = st.tabs(["📩 送信予約登録", "📋 予約一覧"])
    with tab1:
        show_admin_schedule()
    with tab2:
        show_scheduled_message_list()
