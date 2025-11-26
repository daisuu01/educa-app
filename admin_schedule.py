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
def show_scheduled_message_list():
    st.title("📋 未送信の送信予約一覧")

    st.write("以下は、まだ送信されていない予約メッセージのみを表示しています。")

    # 🔹 sent=False のみ取得（送信済みは除外）
    query = (
        db.collection("scheduled_messages")
        .where("sent", "==", False)
        .order_by("scheduled_at")
    )
    docs = list(query.stream())

    if not docs:
        st.info("現在、未送信の予約はありません。")
        return

    import pytz
    jst = pytz.timezone("Asia/Tokyo")

    def to_jst_str(dt):
        if not dt:
            return "-"
        return dt.astimezone(jst).strftime("%Y-%m-%d %H:%M")

    # 🔹 テーブル見出しの文言も変更
    st.markdown("""
    | 宛先タイプ | 宛先ID | メッセージ内容 | 送信予定日時 | 登録日時 | 操作 |
    |-------------|---------|----------------|----------------|------------|------|
    """, unsafe_allow_html=True)

    for d in docs:
        data = d.to_dict()
        doc_id = d.id
        target_type = data.get("target_type", "")
        target_id = data.get("target_id", "")
        text = data.get("text", "").replace("\n", " ")
        send_at = data.get("scheduled_at")
        created = data.get("created_at")

        send_at_str = to_jst_str(send_at)
        created_str = to_jst_str(created)

        # 🔹 未送信のみなので背景色は統一
        row_color = "#e0f7fa"

        st.markdown(
            f"""
            <div style="background-color:{row_color}; padding:8px; margin-bottom:4px; border-radius:6px;">
                <b>{target_type}</b>：{target_id or '-'}<br>
                📨 <span style="color:#333;">{text[:80]}{"..." if len(text)>80 else ""}</span><br>
                ⏰ 送信予定：<b>{send_at_str}</b><br>
                🗓 登録日時：{created_str}
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("🗑 削除", key=f"delete_{doc_id}"):
                db.collection("scheduled_messages").document(doc_id).delete()
                st.success("削除しました。")
                st.rerun()

    st.write("---")
    st.caption("※ この一覧には送信済みの予約は表示されません。未送信のみが対象です。")


# =============================================
# メインエントリーポイント（変更なし）
# =============================================
def show_schedule_main():
    tab1, tab2 = st.tabs(["📩 送信予約登録", "📋 予約一覧"])
    with tab1:
        show_admin_schedule()
    with tab2:
        show_scheduled_message_list()
