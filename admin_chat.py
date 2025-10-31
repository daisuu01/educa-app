# =============================================
# admin_chat.py（管理者用：保護者既読＋グループ送信対応・個人画面にも反映・クラスコード＋名称表示）
# =============================================

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh
from dotenv import load_dotenv
import os
import re
import json
from streamlit.components.v1 import html as components_html
from textwrap import dedent

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

# ==================================================
# 🔹 メッセージ削除関数（個人・学年・クラス・全員対応）
# ==================================================
def delete_message(msg: dict, user_id: str):
    """Firestore上の特定メッセージを削除（送信元に応じて自動判定）"""
    msg_id = msg.get("id")
    origin = msg.get("_origin", "personal")  # どの種類のメッセージか

    if not msg_id:
        return

    try:
        if origin == "personal":
            ref = (
                db.collection("rooms")
                .document("personal")
                .collection(user_id)
                .document("messages")
                .collection("items")
                .document(msg_id)
            )

        elif origin == "class":
            class_name = msg.get("_class_name")
            ref = (
                db.collection("rooms")
                .document("class")
                .collection(str(class_name))
                .document("messages")
                .collection("items")
                .document(msg_id)
            )

        elif origin == "grade":
            grade = msg.get("_grade")
            ref = (
                db.collection("rooms")
                .document("grade")
                .collection(str(grade))
                .document("messages")
                .collection("items")
                .document(msg_id)
            )

        elif origin == "all":
            ref = (
                db.collection("rooms")
                .document("all")
                .collection("messages")
                .document(msg_id)
            )

        else:
            st.warning(f"⚠️ 未対応のメッセージ種別: {origin}")
            return

        ref.delete()
        st.success("✅ メッセージを削除しました。")

    except Exception as e:
        st.error(f"❌ 削除中にエラー: {e}")



# 🔸 学年表記ゆれを吸収（最小限の正規化）
def _normalize_grade(s: str) -> str:
    if not s:
        return ""
    t = str(s)
    trans = str.maketrans("０１２３４５６７８９", "0123456789")
    t = t.translate(trans)
    t = t.replace("　", "").replace(" ", "")
    t = t.replace("中学", "中").replace("高校", "高")
    t = t.replace("学年", "").replace("年", "")
    m = re.match(r"^(中|高)\s*([1-3])$", t)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    if re.match(r"^(中|高)[1-3]$", t):
        return t
    return t


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
                "id": d.id,  # ← 会員番号として利用
                "grade": user.get("grade", ""),
                "class": user.get("class_name", ""),
                "class_code": user.get("class_code", ""),
                "code": user.get("code", ""),
                "name": f"{user.get('last_name', '')} {user.get('first_name', '')}".strip() or d.id
            })
    return students


# ==================================================
# 🔹 メッセージ取得＋既読処理（個人＋グループ統合）
# ==================================================
def get_messages_and_mark_read(user_id: str, grade: str = None, class_name: str = None, limit: int = 50):
    all_msgs = []

    # --- 個人宛 ---
    personal_ref = (
        db.collection("rooms")
        .document("personal")
        .collection(user_id)
        .document("messages")
        .collection("items")
    )
    for d in personal_ref.order_by("timestamp", direction=firestore.Query.ASCENDING).limit(limit).stream():
        m = d.to_dict()
        if not m:
            continue
        if "admin" not in m.get("read_by", []) and m.get("sender") != "admin":
            personal_ref.document(d.id).update({"read_by": firestore.ArrayUnion(["admin"])})
            m["read_by"] = m.get("read_by", []) + ["admin"]
        m["id"] = d.id  # ★ 削除用にドキュメントIDを保持
        m["_origin"] = "personal"
        all_msgs.append(m)

    # --- クラス宛 ---
    if class_name:
        class_ref = (
            db.collection("rooms")
            .document("class")
            .collection(str(class_name))
            .document("messages")
            .collection("items")
        )
        for d in class_ref.order_by("timestamp", direction=firestore.Query.ASCENDING).limit(limit).stream():
            m = d.to_dict()
            if m:
                m["id"] = d.id  # ★ 削除用にドキュメントIDを保持（これが重要！）
                m["_origin"] = "class"
                m["_class_name"] = str(class_name)
                all_msgs.append(m)

    # --- 学年宛 ---
    if grade:
        grade_ref = (
            db.collection("rooms")
            .document("grade")
            .collection(grade)
            .document("messages")
            .collection("items")
        )
        for d in grade_ref.order_by("timestamp", direction=firestore.Query.ASCENDING).limit(limit).stream():
            m = d.to_dict()
            if m:
                m["id"] = d.id  # ★ 追加
                m["_origin"] = "grade"
                m["_grade"] = str(grade)
                all_msgs.append(m)

    # --- 全員宛 ---
    all_ref = db.collection("rooms").document("all").collection("messages")
    for d in all_ref.order_by("timestamp", direction=firestore.Query.ASCENDING).limit(limit).stream():
        m = d.to_dict()
        if m:
            m["id"] = d.id  # ★ 追加
            m["_origin"] = "all"
            all_msgs.append(m)

    all_msgs.sort(key=lambda x: x.get("timestamp", datetime(2000, 1, 1)))
    return all_msgs



# ==================================================
# 🔹 メッセージ送信（個人・学年・クラス・全員対応）
# ==================================================
def send_message(target_type: str, user_id: str = None, grade: str = None, class_name: str = None, text: str = ""):
    if not text.strip():
        return

    data = {
        "text": text.strip(),
        "sender": "admin",
        "timestamp": datetime.now(timezone.utc),
        "read_by": ["admin"],  # 管理者は既読
    }

    # --- 個人宛 ---
    if target_type == "個人" and user_id:
        ref = (
            db.collection("rooms")
            .document("personal")
            .collection(user_id)
            .document("messages")
            .collection("items")
        )
        ref.add(data)

    # --- 全員宛 ---
    elif target_type == "全員":
        ref = db.collection("rooms").document("all").collection("messages")
        ref.add(data)

    # --- 学年宛 ---
    elif target_type == "学年" and grade:
        # 学年掲示板
        grade_ref = (
            db.collection("rooms")
            .document("grade")
            .collection(grade)
            .document("messages")
            .collection("items")
        )
        grade_ref.add(data)

        # 学年メンバー全員に personal 複製
        grade_prefix_map = {"中1": "1", "中2": "2", "中3": "3", "高1": "4", "高2": "5", "高3": "6"}
        prefix = grade_prefix_map.get(grade)
        target_norm = _normalize_grade(grade)

        users_ref = db.collection("users").where("role", "==", "student")
        for u in users_ref.stream():
            ud = u.to_dict() or {}
            code_str = str(ud.get("code") or ud.get("class_code") or "")
            match_prefix = bool(prefix) and code_str.startswith(prefix)
            match_grade = _normalize_grade(ud.get("grade")) == target_norm
            if match_prefix or match_grade:
                personal_ref = (
                    db.collection("rooms")
                    .document("personal")
                    .collection(u.id)
                    .document("messages")
                    .collection("items")
                )
                personal_ref.add(data)

    # --- クラス宛 ---
    elif target_type == "クラス" and class_name:
        # ① クラス掲示板に保存
        class_ref = (
            db.collection("rooms")
            .document("class")
            .collection(str(class_name))
            .document("messages")
            .collection("items")
        )
        class_ref.add(data)

        # ② 同クラスの全生徒へ personal にも複製
        #    class_code == class_name と class == class_name の両方をケア
        seen_ids = set()

        # class_code マッチ
        q1 = db.collection("users").where("role", "==", "student").where("class_code", "==", class_name)
        for u in q1.stream():
            seen_ids.add(u.id)
            personal_ref = (
                db.collection("rooms")
                .document("personal")
                .collection(u.id)
                .document("messages")
                .collection("items")
            )
            personal_ref.add(data)

        # class（名称）マッチ（重複はスキップ）
        q2 = db.collection("users").where("role", "==", "student").where("class", "==", class_name)
        for u in q2.stream():
            if u.id in seen_ids:
                continue
            personal_ref = (
                db.collection("rooms")
                .document("personal")
                .collection(u.id)
                .document("messages")
                .collection("items")
            )
            personal_ref.add(data)



# ==================================================
# 🖥️ 管理者用チャットUI
# ==================================================
def show_admin_chat(initial_student_id=None):
    st.title("💬 管理者チャット管理")

    if not st.session_state.get("just_opened_from_inbox"):
        st_autorefresh(interval=5000, key="admin_chat_refresh")
    else:
        st.session_state["just_opened_from_inbox"] = False

    students = get_all_students()
    if not students:
        st.warning("生徒データが見つかりません。")
        return

    pre_selected_id = initial_student_id if initial_student_id else None

    st.sidebar.markdown("### 📤 送信先設定")
    target_type = st.sidebar.radio("送信先タイプを選択", ["個人", "全員", "学年", "クラス"], horizontal=False)

    selected_id = None
    grade = None
    class_name = None

    if target_type == "個人":
        default_value = pre_selected_id if pre_selected_id else ""
        search_id = st.sidebar.text_input("🔎 チャット相手を検索（会員番号）", value=default_value, key="search_member_id").strip()

        matched = []
        if search_id:
            exact = [s for s in students if s["id"] == search_id]
            matched = exact if exact else [s for s in students if s["id"].startswith(search_id)]

        if matched:
            if len(matched) == 1:
                selected_id = matched[0]["id"]
                st.sidebar.success(f"選択中：{selected_id}（{matched[0]['name']}）")
            else:
                selected_id = st.sidebar.selectbox(
                    "候補から選択",
                    [s["id"] for s in matched],
                    format_func=lambda x: f"{x}：{next((s['name'] for s in matched if s['id']==x), x)}"
                )
        else:
            if search_id:
                st.sidebar.warning("該当する会員番号が見つかりません。")

        if selected_id:
            u = next((s for s in students if s["id"] == selected_id), None)
            grade = u["grade"] if u else None
            class_name = (u.get("class_code") or u.get("class")) if u else None

    elif target_type == "学年":
        grade = st.sidebar.selectbox("学年を選択", ["中1", "中2", "中3", "高1", "高2", "高3"])

    elif target_type == "クラス":
        class_options = {
            (s.get("class_code") or s.get("class")): s.get("class") or s.get("class_code")
            for s in students
            if s.get("class_code") or s.get("class")
        }
        if class_options:
            class_code = st.sidebar.selectbox(
                "クラスを選択（コード＋名称）",
                sorted(class_options.keys()),
                format_func=lambda x: f"{x}：{class_options[x]}"
            )
            class_name = class_code
            for s in students:
                if s.get("class_code") == class_code or s.get("class") == class_code:
                    grade = s.get("grade")
                    break

    #################個人宛####################

    if target_type == "個人" and selected_id:
        st.subheader(f"🧑‍🎓 {next((s['name'] for s in students if s['id'] == selected_id), selected_id)} さんとのチャット")

        messages = get_messages_and_mark_read(selected_id, grade, class_name)
        messages.sort(key=lambda x: x.get("timestamp", datetime(2000, 1, 1)), reverse=True)

        # 過去と直近に分割
        latest = messages[:3]
        older = messages[3:]

        # ✅ ① 過去履歴（expanderを上）
        if older:
            with st.expander(f"📜 過去の履歴を表示（{len(older)}件）"):
                for msg in older[::-1]:  # 古い順に
                    sender = msg.get("sender", "")
                    text = msg.get("text", "")
                    ts = msg.get("timestamp")
                    ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
                    read_by = msg.get("read_by", [])

                    if sender == "admin":
                        guardian_read = "✅ 保護者既読" if "student_保護者" in read_by else "❌ 保護者未読"
                        guardian_color = "#1a73e8" if "student_保護者" in read_by else "#d93025"
                        st.markdown(
                            f"""
                            <div style="display:flex; justify-content:flex-start; margin:10px 0;">
                                <div style="background:#d2e3fc;padding:10px 14px;border-radius:12px;max-width:80%;color:#111;">
                                    {text}
                                </div>
                            </div>
                            <div style="font-size:0.8em;color:#666;margin-left:4px;">
                              {ts_str}
                              <span style="color:{guardian_color};margin-left:6px;">{guardian_read}</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        label = "👦 生徒" if sender == "student_生徒" else "👨‍👩‍👧 保護者"
                        st.markdown(
                            f"""
                            <div style="text-align:right;margin:10px 0;">
                                <div style="font-size:0.8em;color:#666;">{label}</div>
                                <div style="display:inline-block;background-color:#f1f3f4;padding:10px 14px;border-radius:12px;max-width:80%;color:#111;">
                                    {text}
                                </div>
                                <div style="font-size:0.8em;color:#666;">{ts_str}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

        # ✅ ② 直近3件（新しいほど下に）
        st.write("### 📌 直近3件")
        for msg in latest[::-1]:  # ← reverse!
            sender = msg.get("sender", "")
            text = msg.get("text", "")
            ts = msg.get("timestamp")
            ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
            read_by = msg.get("read_by", [])

            if sender == "admin":
                guardian_read = "✅ 保護者既読" if selected_id in read_by else "❌ 保護者未読"
                guardian_color = "#1a73e8" if selected_id in read_by else "#d93025"
                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:flex-start; margin:10px 0;">
                        <div style="background:#d2e3fc;padding:10px 14px;border-radius:12px;max-width:80%;color:#111;">
                            {text}
                        </div>
                    </div>
                    <div style="font-size:0.8em;color:#666;margin-left:4px;">
                      {ts_str}
                      <span style="color:{guardian_color};margin-left:6px;">{guardian_read}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                label = "👦 生徒" if sender == "student_生徒" else "👨‍👩‍👧 保護者"
                st.markdown(
                    f"""
                    <div style="text-align:right;margin:10px 0;">
                        <div style="font-size:0.8em;color:#666;">{label}</div>
                        <div style="display:inline-block;background-color:#f1f3f4;padding:10px 14px;border-radius:12px;max-width:80%;color:#111;">
                            {text}
                        </div>
                        <div style="font-size:0.8em;color:#666;">{ts_str}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # --- 以下（クラス宛、全員宛、学年宛、送信欄）は変更なし ---
    # （元のコードのままでOK）




    # --- クラス宛履歴 ---
    elif target_type == "クラス" and class_name:
        st.subheader(f"👥 {class_name} 宛メッセージ履歴")

        # Firestore参照
        ref = (
            db.collection("rooms")
            .document("class")
            .collection(str(class_name))
            .document("messages")
            .collection("items")
        )

        # メッセージ取得（最新→古い）
        all_msgs = []
        for d in ref.order_by("timestamp", direction=firestore.Query.DESCENDING).stream():
            m = d.to_dict()
            if m:
                all_msgs.append(m)

        # 直近3件 & 過去
        latest = all_msgs[:3]
        older = all_msgs[3:]

        # ✅ ① 過去履歴（expanderを上）
        if older:
            with st.expander(f"📜 過去の履歴を表示（{len(older)}件）"):
                for m in older[::-1]:  # 古い順
                    ts = m.get("timestamp")
                    ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
                    text = m.get("text", "")

                    st.markdown(
                        f"""
                        <div style="display:flex; justify-content:flex-start; margin:10px 0;">
                            <div style="
                                background:#f1f3f4;
                                padding:10px 14px;
                                border-radius:12px;
                                max-width:80%;
                                display:inline-block;
                                color:#111;
                                word-break:break-word;
                            ">
                                {text}
                            </div>
                        </div>
                        <div style="font-size:0.8em; color:#666; margin-left:4px;">
                          {ts_str}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        # ✅ ② 直近3件（新しいほど下）
        st.write("### 📌 直近3件")

        for m in latest[::-1]:  # ← reverse
            ts = m.get("timestamp")
            ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
            text = m.get("text", "")

            st.markdown(
                f"""
                <div style="display:flex; justify-content:flex-start; margin:10px 0;">
                    <div style="
                        background:#f1f3f4;
                        padding:10px 14px;
                        border-radius:12px;
                        max-width:80%;
                        display:inline-block;
                        color:#111;
                        word-break:break-word;
                    ">
                        {text}
                    </div>
                </div>
                <div style="font-size:0.8em; color:#666; margin-left:4px;">
                  {ts_str}
                </div>
                """,
                unsafe_allow_html=True
            )

        st.divider()



    # --- 全員宛履歴 ---
    elif target_type == "全員":
        st.subheader("🌏 全員宛メッセージ履歴")

        all_ref = db.collection("rooms").document("all").collection("messages")

        # メッセージ取得（最新→古い）
        all_msgs = []
        for d in all_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).stream():
            m = d.to_dict()
            if m:
                all_msgs.append(m)

        # 直近3件 & 過去
        latest = all_msgs[:3]
        older = all_msgs[3:]

        # ✅ ① 過去履歴（expanderを上）
        if older:
            with st.expander(f"📜 過去の履歴を表示（{len(older)}件）"):
                for m in older[::-1]:  # 古い順
                    ts = m.get("timestamp")
                    ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
                    text = m.get("text", "")

                    st.markdown(
                        f"""
                        <div style="display:flex; justify-content:flex-start; margin:10px 0;">
                            <div style="
                                background:#f1f3f4;
                                padding:10px 14px;
                                border-radius:12px;
                                max-width:80%;
                                display:inline-block;
                                color:#111;
                                word-break:break-word;
                            ">
                                {text}
                            </div>
                        </div>
                        <div style="font-size:0.8em; color:#666; margin-left:4px;">
                          {ts_str}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        # ✅ ② 直近3件（新しいほど下）
        st.write("### 📌 直近3件")

        for m in latest[::-1]:  # ← reverse
            ts = m.get("timestamp")
            ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
            text = m.get("text", "")

            st.markdown(
                f"""
                <div style="display:flex; justify-content:flex-start; margin:10px 0;">
                    <div style="
                        background:#f1f3f4;
                        padding:10px 14px;
                        border-radius:12px;
                        max-width:80%;
                        display:inline-block;
                        color:#111;
                        word-break:break-word;
                    ">
                        {text}
                    </div>
                </div>
                <div style="font-size:0.8em; color:#666; margin-left:4px;">
                  {ts_str}
                </div>
                """,
                unsafe_allow_html=True
            )

        st.divider()



    ######### 学年宛て ###########
    elif target_type == "学年" and grade:
        st.subheader(f"🏫 {grade} 宛メッセージ履歴")

        ref = (
            db.collection("rooms")
            .document("grade")
            .collection(grade)
            .document("messages")
            .collection("items")
        )

        # メッセージ取得（最新→古い）
        grade_msgs = []
        for d in ref.order_by("timestamp", direction=firestore.Query.DESCENDING).stream():
            m = d.to_dict()
            if m:
                grade_msgs.append(m)

        # 直近3件 & 過去
        latest = grade_msgs[:3]
        older = grade_msgs[3:]

        # ✅ ① 過去履歴（expander上）
        if older:
            with st.expander(f"📜 過去の履歴を表示（{len(older)}件）"):
                for m in older[::-1]:  # 古い順に表示
                    ts = m.get("timestamp")
                    ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
                    text = m.get("text", "")

                    st.markdown(
                        f"""
                        <div style="display:flex; justify-content:flex-start; margin:10px 0;">
                            <div style="
                                background:#f1f3f4;
                                padding:10px 14px;
                                border-radius:12px;
                                max-width:80%;
                                display:inline-block;
                                color:#111;
                                word-break:break-word;
                            ">
                                {text}
                            </div>
                        </div>
                        <div style="font-size:0.8em; color:#666; margin-left:4px;">
                          {ts_str}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        # ✅ ② 直近3件（新しいほど下）
        st.write("### 📌 直近3件")

        for m in latest[::-1]:  # 最新→古い を反転
            ts = m.get("timestamp")
            ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
            text = m.get("text", "")

            st.markdown(
                f"""
                <div style="display:flex; justify-content:flex-start; margin:10px 0;">
                    <div style="
                        background:#f1f3f4;
                        padding:10px 14px;
                        border-radius:12px;
                        max-width:80%;
                        display:inline-block;
                        color:#111;
                        word-break:break-word;
                    ">
                        {text}
                    </div>
                </div>
                <div style="font-size:0.8em; color:#666; margin-left:4px;">
                  {ts_str}
                </div>
                """,
                unsafe_allow_html=True
            )

        st.divider()



    # --- 送信欄 ---
    st.markdown("---")
    st.subheader("📨 メッセージ送信")
    text = st.text_area("メッセージを入力", height=80, key="admin_chat_input")
    if st.button("送信", use_container_width=True):
        send_message(target_type, selected_id, grade, class_name, text)
        st.rerun()
