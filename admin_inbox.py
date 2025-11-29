# =============================================
# admin_inbox.py（改良版：ページネーション＋チャット機能）
# =============================================

import streamlit as st
from datetime import datetime, timezone
import pytz
from firebase_admin import firestore
import html

# ✅ Firebase は共通モジュールから利用
from firebase_utils import db

# ✅ admin_chat から関数をインポート
from admin_chat import send_message


# ==================================================
# 🔹 メッセージ取得
# ==================================================
def get_messages(user_id: str, limit: int = 50):
    """メッセージを取得"""
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
# 🔹 チェックボックス状態を管理
# ==================================================
def is_checked(user_id: str) -> bool:
    """指定されたユーザーがチェック済みかどうか"""
    return st.session_state.get(f"inbox_checked_{user_id}", False)

def set_checked(user_id: str, checked: bool):
    """指定されたユーザーのチェック状態を設定"""
    st.session_state[f"inbox_checked_{user_id}"] = checked


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
        # ✅ 最新10件取得して、生徒・保護者のメッセージを探す
        ref = (
            db.collection("rooms")
            .document("personal")
            .collection(user_id)
            .document("messages")
            .collection("items")
            .order_by("timestamp", direction="DESCENDING")
            .limit(10)
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
        
        # デバッグ: textの中身を確認
        if "<" in str(text) or ">" in str(text):
            st.warning(f"⚠️ DEBUG: メッセージにHTMLタグが含まれています: {repr(text[:100])}")
        
        ts = m.get("timestamp")
        student_id = m["id"]

        jst = pytz.timezone("Asia/Tokyo")
        ts_jst = ts.astimezone(jst) if ts else None
        ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else "日時不明"

        actor = m.get("actor")
        who = "生徒" if actor == "student" else ("保護者" if actor == "guardian" else "生徒/保護者")

        # ✅ 確認済み状態で色分け（エクスパンダーを開いたら自動的に確認済み）
        checked_status = is_checked(student_id)
        if checked_status:
            bg_color = "#f0f0f0"
            border_color = "#999"
            font_weight = "normal"
            opacity = "0.75"
            status_badge = ""
        else:
            bg_color = "#ffe5e5"
            border_color = "#ff4d4d"
            font_weight = "bold"
            opacity = "1.0"
            status_badge = '<span style="background:#ff4d4d;color:white;padding:2px 8px;border-radius:4px;font-size:0.8em;margin-left:8px;">未確認</span>'

        # 全ての変数をHTMLエスケープ
        name_escaped = html.escape(str(name))
        grade_escaped = html.escape(str(grade))
        class_name_escaped = html.escape(str(class_name))
        who_escaped = html.escape(str(who))
        text_escaped = html.escape(str(text)).replace('\n', '<br>')
        ts_str_escaped = html.escape(str(ts_str))

        st.markdown(
            f"""
            <div style="background-color:{bg_color};
                        border-left:6px solid {border_color};
                        padding:10px 14px;
                        border-radius:10px;
                        margin:8px 0;
                        opacity:{opacity};">
                <div style="font-size:1.05em;font-weight:{font_weight};color:#222;">
                    🧑‍🎓 {name_escaped}（{grade_escaped}・{class_name_escaped}）
                    <span style="font-size:0.9em;color:#555;">— {who_escaped} から</span>
                    {status_badge}
                </div>
                <div style="color:#333;margin-top:4px;white-space:pre-wrap;word-wrap:break-word;">{text_escaped}</div>
                <div style="font-size:0.85em;color:#666;margin-top:6px;">📅 {ts_str_escaped}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # ✅ expanderで折りたたみ式チャット
        with st.expander(f"💬 {name} とのチャット履歴", expanded=False):
            # 確認済みボタンを表示（未確認の場合のみ）
            if not checked_status:
                if st.button("✅ 確認済みにする", key=f"confirm_{student_id}", help="このメッセージを確認済みにします"):
                    set_checked(student_id, True)
                    st.rerun()
                st.markdown("---")
            show_chat_in_inbox(student_id, m["name"])


# ==================================================
# 💬 受信ボックス内でチャット表示＋返信機能（直近3件のみ）
# ==================================================
def show_chat_in_inbox(student_id, student_name):
    st.markdown("---")
    st.subheader(f"💬 {student_name} ({student_id}) とのチャット")

    # ✅ メッセージ取得
    messages = get_messages(student_id)
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
    
    # 送信成功メッセージを表示
    if st.session_state.get(f"message_sent_inbox_{student_id}"):
        st.success("✅ 送信しました")
        st.session_state[f"message_sent_inbox_{student_id}"] = False
    
    # ✅ user_chat.pyのパターン：st.formで送信処理
    with st.form(key=f"inbox_send_form_{student_id}", clear_on_submit=True):
        text = st.text_area("メッセージを入力", height=80, key=f"inbox_chat_input_{student_id}")
        send_clicked = st.form_submit_button("📨 送信", use_container_width=True, type="primary")
    
    if send_clicked:
        if not text or not text.strip():
            st.warning("⚠️ メッセージを入力してください")
        else:
            try:
                send_message("個人", student_id, None, None, text)
                _get_latest_received_messages_cached.clear()
                st.session_state[f"message_sent_inbox_{student_id}"] = True
                st.rerun()
            except Exception as e:
                st.error(f"❌ 送信エラー: {e}")
    
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
    
    # HTMLエスケープ
    text_escaped = html.escape(str(text))
    ts_str_escaped = html.escape(str(ts_str))

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
                ">{text_escaped}</div>
            </div>
            <div style="
                margin-left:8px;
                font-size:0.8em;
                color:#666;
                display:flex;
                flex-direction:column;
                align-items:flex-start;
            ">
                <span>{ts_str_escaped}</span>
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
                ">{text_escaped}</div>
                <div style="font-size:0.8em;color:#666;">{ts_str_escaped}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )
