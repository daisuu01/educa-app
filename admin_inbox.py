# =============================================
# admin_inbox.py（改良版：ページネーション＋チャット機能）
# =============================================

import streamlit as st
from datetime import datetime, timezone
import pytz
from firebase_admin import firestore

# ✅ Firebase は共通モジュールから利用
from firebase_utils import db

# ✅ admin_chat から関数をインポート
from admin_chat import send_message


# ==================================================
# 🔹 チェックボックス状態管理（session_state）
# ==================================================
def is_checked(user_id: str, latest_timestamp=None) -> bool:
    """指定されたユーザーが確認済みかどうかを返す
    
    新しいメッセージが来ていたら、自動的に未確認状態にリセット
    """
    checked_key = f"inbox_checked_{user_id}"
    timestamp_key = f"inbox_timestamp_{user_id}"
    
    # 保存されているチェック状態とタイムスタンプを取得
    is_checked_status = st.session_state.get(checked_key, False)
    saved_timestamp = st.session_state.get(timestamp_key)
    
    # 新しいメッセージが来ていたらチェックをリセット
    if latest_timestamp and saved_timestamp:
        if latest_timestamp > saved_timestamp:
            st.session_state[checked_key] = False
            st.session_state[timestamp_key] = latest_timestamp
            return False
    
    # タイムスタンプが保存されていない場合は保存
    if latest_timestamp and not saved_timestamp:
        st.session_state[timestamp_key] = latest_timestamp
    
    return is_checked_status


def set_checked(user_id: str, checked: bool, latest_timestamp=None):
    """指定されたユーザーの確認状態を設定"""
    checked_key = f"inbox_checked_{user_id}"
    timestamp_key = f"inbox_timestamp_{user_id}"
    
    st.session_state[checked_key] = checked
    
    # チェックを入れた時のタイムスタンプも保存
    if checked and latest_timestamp:
        st.session_state[timestamp_key] = latest_timestamp


# ==================================================
# 🔹 メッセージ取得（既読処理なし）
# ==================================================
def get_messages_no_mark(user_id: str, limit: int = 50):
    """既読処理を行わずにメッセージを取得"""
    all_msgs = []
    
    personal_ref = (
        db.collection("rooms")
        .document("personal")
        .collection(user_id)
        .document("messages")
        .collection("items")
    )
    
    for d in personal_ref.order_by("timestamp", direction="DESCENDING").limit(limit).stream():
        m = d.to_dict()
        if m:
            m["id"] = d.id
            m["_origin"] = "personal"
            all_msgs.append(m)
    
    # 表示用：古い順に並べ替え
    all_msgs.sort(key=lambda x: x.get("timestamp", datetime(2000, 1, 1)))
    return all_msgs


# ==================================================
# 🔹 既読処理のみを行う関数
# ==================================================
def mark_messages_as_read(user_id: str):
    """指定されたユーザーの未読メッセージを既読にする"""
    current_admin_id = st.session_state.get("member_id")
    if not current_admin_id:
        return
    
    personal_ref = (
        db.collection("rooms")
        .document("personal")
        .collection(user_id)
        .document("messages")
        .collection("items")
    )
    
    # 最新50件を取得して既読処理
    for d in personal_ref.order_by("timestamp", direction="DESCENDING").limit(50).stream():
        m = d.to_dict()
        if not m:
            continue
        
        # この管理者がまだ既読にしていなければ read_by に追加
        if current_admin_id not in m.get("read_by", []):
            personal_ref.document(d.id).update({
                "read_by": firestore.ArrayUnion([current_admin_id])
            })


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
            .order_by("timestamp", direction="DESCENDING")
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
# ✅ キャッシュで高速化（5秒間保持）
# ==================================================
@st.cache_data(ttl=5, show_spinner=False)
def _get_latest_received_messages_cached(admin_id: str):
    """キャッシュ用の内部関数（admin_idを引数で渡す）"""
    students = get_all_students()
    results = []

    for s in students:
        user_id = s["id"]
        # ✅ 最新50件取得して、生徒・保護者のメッセージを探す
        ref = (
            db.collection("rooms")
            .document("personal")
            .collection(user_id)
            .document("messages")
            .collection("items")
            .order_by("timestamp", direction="DESCENDING")
            .limit(50)
        )

        for d in ref.stream():
            msg = d.to_dict()
            if not msg:
                continue

            sender = msg.get("sender", "")
            if sender in ["student", "生徒", "guardian", "保護者", "student_生徒", "student_保護者"]:
                read_by = msg.get("read_by", [])
                is_unread = admin_id not in read_by if admin_id else False
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
                break

    results.sort(key=lambda x: x.get("timestamp", datetime(2000,1,1)), reverse=True)
    return results


def get_latest_received_messages():
    """外部から呼ばれる関数（session_stateを使う）"""
    current_admin_id = st.session_state.get("member_id")
    return _get_latest_received_messages_cached(current_admin_id or "")


# ==================================================
# 🖥️ 管理者用 受信ボックスUI（ページネーション対応）
# ==================================================
def show_admin_inbox():
    st.title("📥 受信ボックス（生徒・保護者からのメッセージ）")
    st.caption("未読は赤色、既読はグレーで表示されます。")

    # ✅ ページネーション用のステート初期化
    if "inbox_page" not in st.session_state:
        st.session_state["inbox_page"] = 0

    messages = get_latest_received_messages()

    if not messages:
        st.info("📭 現在、受信メッセージはありません。")
        return

    # ✅ ページネーション設定
    per_page = 10
    total_pages = (len(messages) + per_page - 1) // per_page
    current_page = st.session_state["inbox_page"]

    # ページ範囲の調整
    if current_page >= total_pages:
        current_page = max(0, total_pages - 1)
        st.session_state["inbox_page"] = current_page

    start_idx = current_page * per_page
    end_idx = start_idx + per_page
    page_messages = messages[start_idx:end_idx]

    # ✅ ページネーションボタン
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if current_page > 0:
            if st.button("◀ 前へ", key="prev_page"):
                st.session_state["inbox_page"] = current_page - 1
                st.rerun()
    with col2:
        st.markdown(f"<div style='text-align:center;'>ページ {current_page + 1} / {total_pages} （全{len(messages)}件）</div>", unsafe_allow_html=True)
    with col3:
        if current_page < total_pages - 1:
            if st.button("次へ ▶", key="next_page"):
                st.session_state["inbox_page"] = current_page + 1
                st.rerun()

    st.markdown("---")

    # ✅ 現在のページのメッセージを表示
    for m in page_messages:
        name = m["name"]
        grade = m["grade"] or "未設定"
        class_name = m["class"] or "-"
        text = m.get("text", "")
        ts = m.get("timestamp")
        student_id = m["id"]

        jst = pytz.timezone("Asia/Tokyo")
        ts_jst = ts.astimezone(jst) if ts else None
        ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else "日時不明"

        actor = m.get("actor")
        who = "生徒" if actor == "student" else ("保護者" if actor == "guardian" else "生徒/保護者")

        # ✅ チェックボックスの状態を確認（タイムスタンプを渡して新着チェック）
        checked_status = is_checked(student_id, ts)
        
        # ✅ チェック済みなら既読スタイル、未チェックなら未読スタイル
        if checked_status:
            bg_color = "#f0f0f0"
            border_color = "#999"
            font_weight = "normal"
            opacity = "0.75"
        else:
            bg_color = "#ffe5e5"
            border_color = "#ff4d4d"
            font_weight = "bold"
            opacity = "1.0"

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

        # ✅ チェックボックスで確認状態を管理
        checked = st.checkbox(
            "✅ 確認済み",
            value=checked_status,
            key=f"check_{student_id}",
            help="確認したらチェックを入れてください"
        )
        
        # チェック状態が変わったら保存してリロード
        if checked != checked_status:
            set_checked(student_id, checked, ts)
            st.rerun()

        # ✅ expanderで折りたたみ式チャット（デフォルトは閉じた状態）
        with st.expander(f"💬 {name} とのチャット履歴", expanded=False):
            show_chat_in_inbox(student_id, m["name"])


# ==================================================
# 💬 受信ボックス内でチャット表示＋返信機能（直近3件のみ）
# ==================================================
def show_chat_in_inbox(student_id, student_name):
    st.markdown("---")
    st.subheader(f"💬 {student_name} ({student_id}) とのチャット")

    # ✅ 既読処理なしでメッセージ取得
    messages = get_messages_no_mark(student_id)
    messages.sort(key=lambda x: x.get("timestamp", datetime(2000, 1, 1)), reverse=True)

    jst = pytz.timezone("Asia/Tokyo")

    # ✅ 直近3件のみ表示
    latest = messages[:3]

    st.write("### 📌 直近3件")
    for msg in latest[::-1]:
        render_message(msg, student_id, jst)

    # 送信欄
    st.markdown("---")
    st.subheader("📨 返信する")
    
    # ✅ user_chat.pyのパターン：st.formで送信処理
    with st.form(key=f"inbox_send_form_{student_id}", clear_on_submit=True):
        text = st.text_area("メッセージを入力", height=80, key=f"inbox_chat_input_{student_id}")
        send_clicked = st.form_submit_button("📨 送信", use_container_width=True, type="primary")
    
    if send_clicked:
        if not text.strip():
            st.warning("⚠️ メッセージを入力してください")
        else:
            send_message("個人", student_id, None, None, text)
            _get_latest_received_messages_cached.clear()
            st.success("✅ 送信しました")
            st.rerun()
    
    st.markdown("---")


# ==================================================
# 🔹 メッセージ1件をレンダリング
# ==================================================
def render_message(msg, student_id, jst):
    sender = msg.get("sender", "")
    text = msg.get("message", msg.get("text", ""))
    ts = msg.get("timestamp")
    ts_jst = ts.astimezone(jst) if ts else None
    ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
    read_by = msg.get("read_by", [])

    if sender in ["admin", "先生", "講師"]:
        # 管理者メッセージ（左側）
        guardian_read = "✅ 保護者既読" if student_id in read_by else "❌ 保護者未読"
        guardian_color = "#1a73e8" if student_id in read_by else "#d93025"
        st.markdown(
            f"""
            <div style="display:flex; justify-content:flex-start; margin:10px 0;">
                <div style="
                    background:#d2e3fc;
                    padding:10px 14px;
                    border-radius:12px;
                    max-width:80%;
                    color:#111;
                    display:inline-block;
                    word-break:break-word;
                    white-space:pre-wrap;
                ">{text}</div>
            </div>
            <div style="
                margin-left:8px;
                font-size:0.8em;
                color:#666;
                display:flex;
                flex-direction:column;
                align-items:flex-start;
            ">
                <span>{ts_str}</span>
                <span style="color:{guardian_color}; margin-top:2px;">{guardian_read}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif sender in ["生徒", "保護者", "student", "guardian", "student_生徒", "student_保護者"]:
        # 生徒・保護者メッセージ（右側）
        label = "👦 生徒" if sender in ["生徒", "student", "student_生徒"] else "👨‍👩‍👧 保護者"
        st.markdown(
            f"""
            <div style="display:flex; justify-content:flex-end; margin:10px 0;">
              <div style="max-width:80%; text-align:right;">
                <div style="font-size:0.8em;color:#666;">{label}</div>
                <div style="
                  display:inline-block;
                  background-color:#f1f3f4;
                  padding:8px 12px;
                  border-radius:12px;
                  word-wrap:break-word;
                  white-space:pre-wrap;
                  color:#111;
                  text-align:left;
                ">{text}</div>
                <div style="font-size:0.8em;color:#666;">{ts_str}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )
