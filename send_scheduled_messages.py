# =============================================
# send_scheduled_messages.py
# 予約送信スクリプト（5分おきチェック）
# =============================================

from datetime import datetime, timezone
from firebase_utils import db  # ✅ Cloud/ローカル共通の初期化
from admin_chat import send_message


# --- send_message() の読み込み（admin_chat.pyから）
from admin_chat import send_message


def process_scheduled_messages():
    now = datetime.now(timezone.utc)

    # sent=False かつ scheduled_at <= now の予約を取得
    docs = (
        db.collection("scheduled_messages")
        .where("sent", "==", False)
        .stream()
    )

    for d in docs:
        data = d.to_dict()

        # 予定時刻を過ぎていなければスキップ
        scheduled_at = data.get("scheduled_at")
        if not scheduled_at or scheduled_at > now:
            continue

        # 送信対象
        text = data.get("message", data.get("text", ""))
        target_type = data.get("target_type", "")
        target_id = data.get("target_id", None)
        grade = data.get("grade", None)
        class_name = data.get("class_name", None)

        print(f"送信対象: {target_type} / {target_id} / {text}")

        # 送信実行
        send_message(
            target_type,
            user_id=target_id,
            grade=grade,
            class_name=class_name,
            text=text
        )

        # 送信済みに更新
        db.collection("scheduled_messages").document(d.id).update({
            "sent": True,
            "sent_at": now,
        })

        print("送信完了 ✅")

    print("チェック完了 ✔", datetime.now())


if __name__ == "__main__":
    process_scheduled_messages()
