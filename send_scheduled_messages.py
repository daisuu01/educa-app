# =============================================
# send_scheduled_messages.py
# 予約送信スクリプト（5分おきチェック）
# =============================================

from datetime import datetime, timezone
from firebase_utils import db  # Cloud/ローカル共通
from admin_chat import send_message


def process_scheduled_messages():
    now = datetime.now(timezone.utc)

    # sent=False の予約を取得（全部）
    docs = (
        db.collection("scheduled_messages")
        .where("sent", "==", False)
        .stream()
    )

    for d in docs:
        data = d.to_dict()
        scheduled_at = data.get("scheduled_at")

        # Firestore に datetime で保存されていないケース防止
        if not isinstance(scheduled_at, datetime):
            print(f"⚠️ scheduled_at が datetime ではない: {scheduled_at}")
            continue

        # 予定時刻をまだ過ぎていない → スキップ
        if scheduled_at > now:
            continue

        # ------------------------
        # 送信対象の抽出
        # ------------------------
        text = data.get("message") or data.get("text") or ""
        target_type = data.get("target_type", "")
        target_id = data.get("target_id")
        grade = data.get("grade")
        class_name = data.get("class_name")

        print(f"📨 送信対象: {target_type} / {target_id} / {text}")

        # ------------------------
        # 送信実行
        # ------------------------
        send_message(
            target_type,
            user_id=target_id,
            grade=grade,
            class_name=class_name,
            text=text
        )

        # ------------------------
        # 送信済みに更新
        # ------------------------
        db.collection("scheduled_messages").document(d.id).update({
            "sent": True,
            "sent_at": now,
        })

        print("✅ 送信完了")

    print("✔ チェック完了", datetime.now())


if __name__ == "__main__":
    process_scheduled_messages()