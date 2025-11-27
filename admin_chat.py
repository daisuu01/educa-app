# =============================================
# admin_chat.py（管理者用：保護者既読＋グループ送信対応・個人画面にも反映・クラスコード＋名称表示）
# =============================================

import streamlit as st
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh
import re
import json
from streamlit.components.v1 import html as components_html
from textwrap import dedent
import pytz
from firebase_admin import firestore
from firebase_utils import db


# --- 読み込み中の白いオーバーレイを完全無効化 ---
st.markdown("""
<style>
/* ===========================================
   ① Streamlit の白フェード overlay を完全 OFF
   =========================================== */

/* ページ覆う白い膜 */
.stApp::before {
    content: none !important;
    display: none !important;
    background: none !important;
}

/* status widget も白膜を作るので削除 */
[data-testid="stStatusWidget"] {
    display: none !important;
    visibility: hidden !important;
}

/* ===========================================
   ② rerun 中にかかる 0.33 opacity を強制OFF
   =========================================== */

.stApp, .stApp > div, .block-container, div, section, main, header {
    opacity: 1 !important;
    transition: none !important;
}

/* container への fade-in 防止 */
[data-testid="stAppViewContainer"] {
    transition: none !important;
}

/* スピナーを完全非表示 */
.stSpinner, div[data-testid="stSpinner"] {
    display: none !important;
    visibility: hidden !important;
}

/* サイドバー完全削除（必要なら） */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
    visibility: hidden !important;
}
</style>

<script>
// ===========================================
// ③ Streamlit の opacity を JS で強制上書き
// ===========================================

function killOpacity() {
    document.querySelectorAll('*').forEach(el => {
        const style = window.getComputedStyle(el);
        if (style.opacity && parseFloat(style.opacity) < 1) {
            el.style.opacity = "1";
        }
    });
}

// DOM 更新が起きた瞬間に即上書き
new MutationObserver(() => killOpacity())
    .observe(document.body, { childList: true, subtree: true });

// 念のため 0.2 秒ごとにも実行
setInterval(killOpacity, 200);
</script>
""", unsafe_allow_html=True)



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
            # Firestoreの name フィールドを最優先で使用
            full_name = user.get("name", "").strip()

            # name が無ければ last_name + first_name をフォールバック
            if not full_name:
                full_name = f"{user.get('last_name', '')} {user.get('first_name', '')}".strip()

            students.append({
                "id": d.id,  # ← 会員番号として利用
                "grade": user.get("grade", ""),
                "class": user.get("class_name", ""),
                "class_code": user.get("class_code", ""),
                "code": user.get("code", ""),
                "name": full_name or d.id,  # ← name を最優先
            })
    return students


# def get_all_students():
#     users_ref = db.collection("users")
#     docs = users_ref.stream()
#     students = []
#     for d in docs:
#         user = d.to_dict()
#         if user.get("role") == "student":
#             students.append({
#                 "id": d.id,  # ← 会員番号として利用
#                 "grade": user.get("grade", ""),
#                 "class": user.get("class_name", ""),
#                 "class_code": user.get("class_code", ""),
#                 "code": user.get("code", ""),
#                 "name": f"{user.get('last_name', '')} {user.get('first_name', '')}".strip() or d.id
#             })
#     return students


# ==================================================
# 🔹 メッセージ取得＋既読処理（個人＋グループ統合）修正版
# ==================================================
def get_messages_and_mark_read(user_id: str, grade: str = None, class_name: str = None, limit: int = 50):
    all_msgs = []

    # 🔑 現在ログイン中の管理者ID
    current_admin_id = st.session_state.get("member_id")

    # --- 個人宛 ---
    personal_ref = (
        db.collection("rooms")
        .document("personal")
        .collection(user_id)
        .document("messages")
        .collection("items")
    )
    for d in personal_ref.order_by("timestamp", direction="DESCENDING").limit(limit).stream():
        m = d.to_dict()
        if not m:
            continue

        # ✅ この管理者がまだ既読にしていなければ read_by に追加
        if current_admin_id and current_admin_id not in m.get("read_by", []):
            personal_ref.document(d.id).update({
                "read_by": firestore.ArrayUnion([current_admin_id])
            })
            m["read_by"] = m.get("read_by", []) + [current_admin_id]
        m["id"] = d.id
        m["_origin"] = "personal"
        all_msgs.append(m)

    # --- クラス宛 ---
    # ✅ 「個人宛の画面」から呼ばれたときは除外（＝user_idが指定されているとき）
    if class_name and not user_id:
        class_ref = (
            db.collection("rooms")
            .document("class")
            .collection(str(class_name))
            .document("messages")
            .collection("items")
        )
        for d in class_ref.order_by("timestamp", direction="DESCENDING").limit(limit).stream():
            m = d.to_dict()
            if m:
                m["id"] = d.id
                m["_origin"] = "class"
                m["_class_name"] = str(class_name)
                all_msgs.append(m)

    # --- 学年宛 ---
    if grade:
        # ✅ 学年キーを正規化（例: "中１" → "中1"）
        def _normalize_grade(g):
            if not g:
                return g
            return g.replace("１", "1").replace("２", "2").replace("３", "3").replace("４", "4").replace("５", "5").replace("６", "6")

        grade_key = _normalize_grade(grade)
        grade_ref = (
            db.collection("rooms")
            .document("grade")
            .collection(grade_key)
            .document("messages")
            .collection("items")
        )
        for d in grade_ref.order_by("timestamp", direction="DESCENDING").limit(limit).stream():
            m = d.to_dict()
            if m:
                m["id"] = d.id
                m["_origin"] = "grade"
                m["_grade"] = grade_key
                all_msgs.append(m)

    # --- 全員宛 ---
    all_ref = db.collection("rooms").document("all").collection("messages")
    for d in all_ref.order_by("timestamp", direction="DESCENDING").limit(limit).stream():
        m = d.to_dict()
        if m:
            m["id"] = d.id
            m["_origin"] = "all"
            all_msgs.append(m)

    # ✅ 表示用：古い順に並べ替え
    all_msgs.sort(key=lambda x: x.get("timestamp", datetime(2000, 1, 1)))
    return all_msgs




# ==================================================
# 🔹 メッセージ送信（個人・学年・クラス・全員対応）
# ==================================================
def send_message(target_type: str, user_id: str = None, grade: str = None, class_name: str = None, text: str = ""):
    if not text.strip():
        return

    data = {
        "message": text.strip(),
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
# 🖥️ 管理者用チャットUI（タブごとに完結）
# ==================================================
def show_admin_chat(initial_student_id=None):
    st.title("💬 チャット管理")

        # ←このすぐ下に追加！！
    if "selected_student_id" in st.session_state and st.session_state["selected_student_id"]:
        initial_student_id = st.session_state["selected_student_id"]
        st.session_state["admin_chat_tab"] = "個人"

    # --- タブの見た目調整CSS（今まで通り） ---
    st.markdown("""
    <style>
    div[role="tablist"] {
        display: flex !important;
        justify-content: space-around !important;
        align-items: center !important;
        width: 100% !important;
    }
    div[role="tab"] {
        flex: 1 !important;
        text-align: center !important;
        padding: 14px 0 !important;
        font-size: 1.05rem !important;
        min-width: 120px !important;
    }
    div[role="tab"][aria-selected="true"] {
        color: #e53935 !important;
        font-weight: 600 !important;
    }
    div[role="tab"][aria-selected="true"]::after {
        content: "";
        display: block;
        height: 3px;
        background: #e53935;
        border-radius: 2px;
        margin-top: 6px;
    }
    </style>
    """, unsafe_allow_html=True)

    # -------------------------
    # 🔸 自動更新（Inbox遷移時は除外）
    # -------------------------
    if not st.session_state.get("just_opened_from_inbox"):
        st_autorefresh(interval=5000, key="admin_chat_refresh")
    else:
        st.session_state["just_opened_from_inbox"] = False

    # -------------------------
    # 🔸 Inbox から引き継いだ ID
    # -------------------------
    if "selected_student_id" in st.session_state and st.session_state["selected_student_id"]:
        initial_student_id = st.session_state["selected_student_id"]

    # -------------------------
    # 🔸 生徒一覧ロード
    # -------------------------
    students = get_all_students()
    if not students:
        st.warning("生徒データが見つかりません。")
        return

    jst = pytz.timezone("Asia/Tokyo")
    pre_selected_id = initial_student_id or ""

    # ---------- タブ ----------
    st.markdown('<div class="admin-chat-tabs">', unsafe_allow_html=True)
    tab_personal, tab_grade, tab_class, tab_all = st.tabs(["個人", "学年", "クラス", "全員"])
    st.markdown('</div>', unsafe_allow_html=True)

    # ============================================================
    # ① 個人タブ
    # ============================================================
    with tab_personal:
        st.session_state["admin_chat_tab"] = "個人"

        selected_id = None
        grade = None
        class_name = None

        st.write("### 🔎 チャット相手を検索（会員番号）")

        search_id = st.text_input(
            "会員番号を入力してください",
            value=pre_selected_id,
            key="search_member_id_personal"
        ).strip()

        if initial_student_id:
            search_id = str(initial_student_id)

        matched = []
        if search_id:
            exact = [s for s in students if s["id"] == search_id]
            matched = exact if exact else [s for s in students if s["id"].startswith(search_id)]

        if matched:
            if len(matched) == 1:
                selected_id = matched[0]["id"]
                st.success(f"選択中：{selected_id}（{matched[0]['name']}）")
            else:
                selected_id = st.selectbox(
                    "候補から選択",
                    [s["id"] for s in matched],
                    key="personal_candidates",
                    format_func=lambda x: f"{x}：{next((s['name'] for s in matched if s['id'] == x), x)}"
                )
        else:
            if search_id:
                st.warning("該当する会員番号が見つかりません。")

        if selected_id:
            u = next((s for s in students if s["id"] == selected_id), None)
            if u:
                grade = u.get("grade")
                class_name = u.get("class_code") or u.get("class")

            # ---- 個人チャット表示 ----
            display_name = selected_id
            if u and u.get("name") and u["name"] != selected_id:
                display_name = f"{selected_id} {u['name']}"

            st.subheader(f"🧑‍🎓 {display_name} さんとのチャット")

            messages = get_messages_and_mark_read(selected_id, grade, class_name)
            messages.sort(key=lambda x: x.get("timestamp", datetime(2000, 1, 1)), reverse=True)

            latest = messages[:3]
            older = messages[3:]

            # 過去履歴
            if older:
                with st.expander(f"📜 過去の履歴を表示（{len(older)}件）"):
                    for msg in older[::-1]:
                        sender = msg.get("sender", "")
                        text = msg.get("message", msg.get("text", ""))
                        ts = msg.get("timestamp")
                        ts_jst = ts.astimezone(jst) if ts else None
                        ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
                        read_by = msg.get("read_by", [])

                        if sender in ["admin", "先生", "講師"]:
                            guardian_read = "✅ 保護者既読" if selected_id in read_by else "❌ 保護者未読"
                            guardian_color = "#1a73e8" if selected_id in read_by else "#d93025"
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
                            label = "👦 生徒" if sender in ["生徒", "student", "student_生徒"] else "👨‍👩‍👧 保護者"
                            st.markdown(
                                f"""
                                <div style="display:flex; justify-content:flex-end; margin:10px 0;">
                                  <div style="display:flex; flex-direction:column; align-items:flex-end; width:fit-content;">
                                    <div style="font-size:0.8em;color:#666;">{label}</div>
                                    <div style="
                                      display:inline-flex;
                                      background-color:#f1f3f4;
                                      padding:8px 12px;
                                      border-radius:12px;
                                      width:auto;
                                      max-width:70%;
                                      word-wrap:break-word;
                                      white-space:pre-wrap;
                                      color:#111;
                                      text-align:left;
                                    ">{text}</div>
                                    <div style="font-size:0.8em;color:#666;text-align:right;">{ts_str}</div>
                                  </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

            # 直近3件
            st.write("### 📌 直近3件")
            for msg in latest[::-1]:
                sender = msg.get("sender", "")
                text = msg.get("message", msg.get("text", ""))
                ts = msg.get("timestamp")
                ts_jst = ts.astimezone(jst) if ts else None
                ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
                read_by = msg.get("read_by", [])

                if sender in ["admin", "先生", "講師"]:
                    guardian_read = "✅ 保護者既読" if selected_id in read_by else "❌ 保護者未読"
                    guardian_color = "#1a73e8" if selected_id in read_by else "#d93025"
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
                    label = "👦 生徒" if sender in ["生徒", "student", "student_生徒"] else "👨‍👩‍👧 保護者"
                    st.markdown(
                        f"""
                        <div style="display:flex; justify-content:flex-end; margin:10px 0;">
                          <div style="display:flex; flex-direction:column; align-items:flex-end; width:fit-content;">
                            <div style="font-size:0.8em;color:#666;">{label}</div>
                            <div style="
                              display:inline-flex;
                              background-color:#f1f3f4;
                              padding:8px 12px;
                              border-radius:12px;
                              width:auto;
                              max-width:70%;
                              word-wrap:break-word;
                              white-space:pre-wrap;
                              color:#111;
                              text-align:left;
                            ">{text}</div>
                            <div style="font-size:0.8em;color:#666;text-align:right;">{ts_str}</div>
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            # 送信欄（個人）
            st.markdown("---")
            st.subheader("📨 メッセージ送信（個人）")
            with st.form("send_form_personal", clear_on_submit=True):
                text = st.text_area("メッセージを入力", height=80)
                send_clicked = st.form_submit_button("送信", use_container_width=True)
            if send_clicked and selected_id:
                send_message("個人", selected_id, grade, class_name, text)
                st.success("送信しました")

    # ============================================================
    # ② 学年タブ
    # ============================================================
    with tab_grade:
        st.session_state["admin_chat_tab"] = "学年"

        st.write("### 🏫 学年を選択")
        grade = st.selectbox("学年", ["中1", "中2", "中3", "高1", "高2", "高3"], key="grade_select")
        class_name = None
        selected_id = None

        st.subheader(f"🏫 {grade} 宛メッセージ履歴")

        ref = (
            db.collection("rooms")
            .document("grade")
            .collection(grade)
            .document("messages")
            .collection("items")
        )

        grade_msgs = []
        for d in ref.order_by("timestamp", direction="DESCENDING").limit(100).stream():
            m = d.to_dict()
            if m:
                grade_msgs.append(m)

        latest = grade_msgs[:3]
        older = grade_msgs[3:]

        if older:
            with st.expander(f"📜 過去の履歴を表示（{len(older)}件）"):
                for m in older[::-1]:
                    ts = m.get("timestamp")
                    ts_jst = ts.astimezone(jst) if ts else None
                    ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
                    text = m.get("message", m.get("text", ""))
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

        st.write("### 📌 直近3件")
        for m in latest[::-1]:
            ts = m.get("timestamp")
            ts_jst = ts.astimezone(jst) if ts else None
            ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
            text = m.get("message", m.get("text", ""))
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

        st.markdown("---")
        st.subheader("📨 メッセージ送信（学年）")
        with st.form("send_form_grade", clear_on_submit=True):
            text = st.text_area("メッセージを入力", height=80)
            send_clicked = st.form_submit_button("送信", use_container_width=True)
        if send_clicked:
            send_message("学年", None, grade, None, text)
            st.success("送信しました")

    # ============================================================
    # ③ クラスタブ
    # ============================================================
    with tab_class:
        st.session_state["admin_chat_tab"] = "クラス"

        st.write("### 👥 クラスを選択")
        class_options = {
            (s.get("class_code") or s.get("class")): s.get("class") or s.get("class_code")
            for s in students
            if s.get("class_code") or s.get("class")
        }

        class_name = None
        if class_options:
            class_code = st.selectbox(
                "クラス（コード＋名称）",
                sorted(class_options.keys()),
                key="class_select",
                format_func=lambda x: f"{x}：{class_options[x]}"
            )
            class_name = class_code
        else:
            st.warning("クラスデータがありません。")

        if class_name:
            st.subheader(f"👥 {class_name} 宛メッセージ履歴")

            ref = (
                db.collection("rooms")
                .document("class")
                .collection(str(class_name))
                .document("messages")
                .collection("items")
            )

            all_msgs = []
            for d in ref.order_by("timestamp", direction="DESCENDING").limit(100).stream():
                m = d.to_dict()
                if m:
                    all_msgs.append(m)

            latest = all_msgs[:3]
            older = all_msgs[3:]

            if older:
                with st.expander(f"📜 過去の履歴を表示（{len(older)}件）"):
                    for m in older[::-1]:
                        ts = m.get("timestamp")
                        ts_jst = ts.astimezone(jst) if ts else None
                        ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
                        text = m.get("message", m.get("text", ""))
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

            st.write("### 📌 直近3件")
            for m in latest[::-1]:
                ts = m.get("timestamp")
                ts_jst = ts.astimezone(jst) if ts else None
                ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
                text = m.get("message", m.get("text", ""))
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

            st.markdown("---")
            st.subheader("📨 メッセージ送信（クラス）")
            with st.form("send_form_class", clear_on_submit=True):
                text = st.text_area("メッセージを入力", height=80)
                send_clicked = st.form_submit_button("送信", use_container_width=True)
            if send_clicked:
                send_message("クラス", None, None, class_name, text)
                st.success("送信しました")

    # ============================================================
    # ④ 全員タブ
    # ============================================================
    with tab_all:
        st.session_state["admin_chat_tab"] = "全員"

        st.subheader("🌏 全員宛メッセージ履歴")

        all_ref = db.collection("rooms").document("all").collection("messages")

        all_msgs = []
        for d in all_ref.order_by("timestamp", direction="DESCENDING").limit(50).stream():
            m = d.to_dict()
            if m:
                all_msgs.append(m)

        latest = all_msgs[:3]
        older = all_msgs[3:]

        if older:
            with st.expander(f"📜 過去の履歴を表示（{len(older)}件）"):
                for m in older[::-1]:
                    ts = m.get("timestamp")
                    ts_jst = ts.astimezone(jst) if ts else None
                    ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
                    text = m.get("message", m.get("text", ""))
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

        st.write("### 📌 直近3件")
        for m in latest[::-1]:
            ts = m.get("timestamp")
            ts_jst = ts.astimezone(jst) if ts else None
            ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
            text = m.get("message", m.get("text", ""))
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

        st.markdown("---")
        st.subheader("📨 メッセージ送信（全員）")
        with st.form("send_form_all", clear_on_submit=True):
            text = st.text_area("メッセージを入力", height=80)
            send_clicked = st.form_submit_button("送信", use_container_width=True)
        if send_clicked:
            send_message("全員", None, None, None, text)
            st.success("送信しました")








# # ==================================================
# # 🖥️ 管理者用チャットUI
# # ==================================================
# def show_admin_chat(initial_student_id=None):
#     st.title("💬 チャット管理")

#     st.markdown("""
#     <style>
#     /* Streamlit の tabs を強制的に横に広くする */

#     /* タブリストを中央寄せ＋均等配置 */
#     div[role="tablist"] {
#         display: flex !important;
#         justify-content: space-around !important;
#         align-items: center !important;
#         width: 100% !important;
#     }

#     /* タブボタンを広げる */
#     div[role="tab"] {
#         flex: 1 !important;          /* 均等幅 */
#         text-align: center !important;
#         padding: 14px 0 !important;
#         font-size: 1.05rem !important;
#         min-width: 120px !important; /* これで横に広がる */
#     }

#     /* 選択中のタブ */
#     div[role="tab"][aria-selected="true"] {
#         color: #e53935 !important;
#         font-weight: 600 !important;
#     }

#     /* 下線 */
#     div[role="tab"][aria-selected="true"]::after {
#         content: "";
#         display: block;
#         height: 3px;
#         background: #e53935;
#         border-radius: 2px;
#         margin-top: 6px;
#     }
#     </style>
#     """, unsafe_allow_html=True)




#     # ---- ダミー input を非表示にする CSS ----
#     st.markdown("""
#     <style>
#     input[id^="dummy_"] {
#         display: none !important;
#     }
#     </style>
#     """, unsafe_allow_html=True)

#     st.markdown('<div class="admin-chat-tabs">', unsafe_allow_html=True)

#     tabs = st.tabs(["個人", "学年", "クラス", "全員"])

#     # 初期化
#     if "admin_chat_tab" not in st.session_state:
#         st.session_state["admin_chat_tab"] = "個人"

#     # ---- 個人 ----
#     with tabs[0]:
#         st.text_input("個人", "個人", key="dummy_personal", label_visibility="collapsed")
#         st.session_state["admin_chat_tab"] = "個人"

#     # ---- 学年 ----
#     with tabs[1]:
#         st.text_input("学年", "学年", key="dummy_grade", label_visibility="collapsed")
#         st.session_state["admin_chat_tab"] = "学年"

#     # ---- クラス ----
#     with tabs[2]:
#         st.text_input("クラス", "クラス", key="dummy_class", label_visibility="collapsed")
#         st.session_state["admin_chat_tab"] = "クラス"

#     # ---- 全員 ----
#     with tabs[3]:
#         st.text_input("全員", "全員", key="dummy_all", label_visibility="collapsed")
#         st.session_state["admin_chat_tab"] = "全員"

#     st.markdown('</div>', unsafe_allow_html=True)

#     # 現在のタブ
#     target_type = st.session_state["admin_chat_tab"]



#     # ----------------------------------------------------

#     # -------------------------
#     # 🔸 自動更新（Inbox遷移時は除外）
#     # -------------------------
#     if not st.session_state.get("just_opened_from_inbox"):
#         st_autorefresh(interval=5000, key="admin_chat_refresh")
#     else:
#         st.session_state["just_opened_from_inbox"] = False

#     # -------------------------
#     # 🔸 Inbox から引き継いだ ID
#     # -------------------------
#     if "selected_student_id" in st.session_state and st.session_state["selected_student_id"]:
#         initial_student_id = st.session_state["selected_student_id"]

#     # -------------------------
#     # 🔸 生徒一覧ロード
#     # -------------------------
#     students = get_all_students()
#     if not students:
#         st.warning("生徒データが見つかりません。")
#         return

#     pre_selected_id = initial_student_id or None

#     selected_id = None
#     grade = None
#     class_name = None

#     # ============================================================
#     # ① 個人タブ（中央に検索欄）
#     # ============================================================
#     if target_type == "個人":
#         grade = None
#         class_name = None

#         st.write("### 🔎 チャット相手を検索（会員番号）")

#         default_value = pre_selected_id or ""
#         search_id = st.text_input(
#             "会員番号を入力してください",
#             value=default_value,
#             key="search_member_id"
#         ).strip()

#         matched = []
#         if search_id:
#             exact = [s for s in students if s["id"] == search_id]
#             matched = exact if exact else [s for s in students if s["id"].startswith(search_id)]

#         if matched:
#             if len(matched) == 1:
#                 selected_id = matched[0]["id"]
#                 st.success(f"選択中：{selected_id}（{matched[0]['name']}）")
#             else:
#                 selected_id = st.selectbox(
#                     "候補から選択",
#                     [s["id"] for s in matched],
#                     format_func=lambda x: f"{x}：{next((s['name'] for s in matched if s['id']==x), x)}"
#                 )
#         else:
#             if search_id:
#                 st.warning("該当する会員番号が見つかりません。")

#         if selected_id:
#             u = next((s for s in students if s["id"] == selected_id), None)
#             if u:
#                 grade = u.get("grade")
#                 class_name = u.get("class_code") or u.get("class")

#     # ============================================================
#     # ② 学年タブ（中央表示）
#     # ============================================================
#     elif target_type == "学年":
#         st.write("### 🏫 学年を選択")
#         grade = st.selectbox("学年", ["中1", "中2", "中3", "高1", "高2", "高3"])
#         class_name = None
#         selected_id = None

#     # ============================================================
#     # ③ クラスタブ（中央表示）
#     # ============================================================
#     elif target_type == "クラス":
#         st.write("### 👥 クラスを選択")

#         class_options = {
#             (s.get("class_code") or s.get("class")): s.get("class") or s.get("class_code")
#             for s in students
#             if s.get("class_code") or s.get("class")
#         }

#         if class_options:
#             class_code = st.selectbox(
#                 "クラス（コード＋名称）",
#                 sorted(class_options.keys()),
#                 format_func=lambda x: f"{x}：{class_options[x]}"
#             )
#             class_name = class_code

#             for s in students:
#                 if s.get("class_code") == class_code or s.get("class") == class_code:
#                     grade = s.get("grade")
#                     break
#         else:
#             st.warning("クラスデータがありません。")
#             class_name = None
#             grade = None

#     # ============================================================
#     # ④ 全員タブ
#     # ============================================================
#     elif target_type == "全員":
#         selected_id = None
#         grade = None
#         class_name = None



#     #################個人宛####################

#     if target_type == "個人" and selected_id:
#         u = next((s for s in students if s["id"] == selected_id), None)
#         if u:
#             # nameが空 or idと同じなら重複回避
#             if not u.get("name") or u["name"] == selected_id:
#                 display_name = selected_id
#             else:
#                 display_name = f"{selected_id} {u['name']}"
#         else:
#             display_name = selected_id

#         st.subheader(f"🧑‍🎓 {display_name} さんとのチャット")

#         messages = get_messages_and_mark_read(selected_id, grade, class_name)
#         messages.sort(key=lambda x: x.get("timestamp", datetime(2000, 1, 1)), reverse=True)

#         latest = messages[:3]
#         older = messages[3:]

#         # ✅ ① 過去履歴（expanderを上）
#         if older:
#             with st.expander(f"📜 過去の履歴を表示（{len(older)}件）"):
#                 for msg in older[::-1]:
#                     sender = msg.get("sender", "")
#                     text = msg.get("message", msg.get("text", ""))
#                     ts = msg.get("timestamp")
#                     jst = pytz.timezone("Asia/Tokyo")
#                     ts_jst = ts.astimezone(jst) if ts else None
#                     ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
#                     read_by = msg.get("read_by", [])

#                     # --- 管理者メッセージ（左側）
#                     if sender in ["admin", "先生", "講師"]:
#                         guardian_read = "✅ 保護者既読" if selected_id in read_by else "❌ 保護者未読"
#                         guardian_color = "#1a73e8" if selected_id in read_by else "#d93025"
#                         st.markdown(
#                             f"""
#                             <div style="display:flex; justify-content:flex-start; margin:10px 0;">
#                                 <div style="
#                                     background:#d2e3fc;
#                                     padding:10px 14px;
#                                     border-radius:12px;
#                                     max-width:80%;
#                                     color:#111;
#                                     display:inline-block;
#                                     word-break:break-word;
#                                     white-space:pre-wrap;
#                                 ">{text}</div>
#                             </div>
#                             <div style="
#                                 margin-left:8px;
#                                 font-size:0.8em;
#                                 color:#666;
#                                 display:flex;
#                                 flex-direction:column;
#                                 align-items:flex-start;
#                             ">
#                                 <span>{ts_str}</span>
#                                 <span style="color:{guardian_color}; margin-top:2px;">{guardian_read}</span>
#                             </div>
#                             """,
#                             unsafe_allow_html=True
#                         )


#                     # --- 生徒または保護者メッセージ（右側）
#                     elif sender in ["生徒", "保護者", "student", "guardian", "student_生徒", "student_保護者"]:
#                         label = "👦 生徒" if sender in ["生徒", "student", "student_生徒"] else "👨‍👩‍👧 保護者"
#                         st.markdown(
#                             f"""
#                             <div style="display:flex; justify-content:flex-end; margin:10px 0;">
#                               <div style="text-align:right;">
#                                 <div style="font-size:0.8em;color:#666;">{label}</div>
#                                 <div style="
#                                   display:inline-block;
#                                   background-color:#f1f3f4;
#                                   padding:8px 12px;
#                                   border-radius:12px;
#                                   width:auto;              /* ← 内容に合わせて縮む */
#                                   max-width:70%;           /* ← 長文だけ折り返し */
#                                   word-wrap:break-word;
#                                   white-space:pre-wrap;
#                                   color:#111;
#                                   text-align:left;         /* ← 吹き出し内は左揃え */
#                                 ">
#                                   {text}
#                                 </div>
#                                 <div style="font-size:0.8em;color:#666;text-align:right;">{ts_str}</div>
#                               </div>
#                             </div>
#                             """,
#                             unsafe_allow_html=True
#                         )


#         # ✅ ② 直近3件（新しいほど下に）
#         st.write("### 📌 直近3件")
#         for msg in latest[::-1]:
#             sender = msg.get("sender", "")
#             text = msg.get("message", msg.get("text", ""))
#             ts = msg.get("timestamp")
#             jst = pytz.timezone("Asia/Tokyo")
#             ts_jst = ts.astimezone(jst) if ts else None
#             ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
#             read_by = msg.get("read_by", [])

#             if sender in ["admin", "先生", "講師"]:
#                 guardian_read = "✅ 保護者既読" if selected_id in read_by else "❌ 保護者未読"
#                 guardian_color = "#1a73e8" if selected_id in read_by else "#d93025"
#                 st.markdown(
#                     f"""
#                     <div style="display:flex; justify-content:flex-start; margin:10px 0;">
#                         <div style="
#                             background:#d2e3fc;
#                             padding:10px 14px;
#                             border-radius:12px;
#                             max-width:80%;
#                             color:#111;
#                             display:inline-block;
#                             word-break:break-word;
#                             white-space:pre-wrap;
#                         ">{text}</div>
#                     </div>
#                     <div style="
#                         margin-left:8px;
#                         font-size:0.8em;
#                         color:#666;
#                         display:flex;
#                         flex-direction:column;
#                         align-items:flex-start;
#                     ">
#                         <span>{ts_str}</span>
#                         <span style="color:{guardian_color}; margin-top:2px;">{guardian_read}</span>
#                     </div>
#                     """,
#                     unsafe_allow_html=True
#                 )


#             elif sender in ["生徒", "保護者", "student", "guardian", "student_生徒", "student_保護者"]:
#                 label = "👦 生徒" if sender in ["生徒", "student", "student_生徒"] else "👨‍👩‍👧 保護者"
#                 st.markdown(
#                     f"""
#                     <div style="display:flex; justify-content:flex-end; margin:10px 0;">
#                       <div style="text-align:right;">
#                         <div style="font-size:0.8em;color:#666;">{label}</div>
#                         <div style="
#                           display:inline-block;
#                           background-color:#f1f3f4;
#                           padding:8px 12px;
#                           border-radius:12px;
#                           width:auto;              /* ← 内容に合わせて縮む */
#                           max-width:70%;           /* ← 長文だけ折り返し */
#                           word-wrap:break-word;
#                           white-space:pre-wrap;
#                           color:#111;
#                           text-align:left;         /* ← 吹き出し内は左揃え */
#                         ">
#                           {text}
#                         </div>
#                         <div style="font-size:0.8em;color:#666;text-align:right;">{ts_str}</div>
#                       </div>
#                     </div>
#                     """,
#                     unsafe_allow_html=True
#                 )



#     # --- 以下（クラス宛、全員宛、学年宛、送信欄）は変更なし ---
#     # （元のコードのままでOK）




#     # --- クラス宛履歴 ---
#     elif target_type == "クラス" and class_name:
#         st.subheader(f"👥 {class_name} 宛メッセージ履歴")

#         # Firestore参照
#         ref = (
#             db.collection("rooms")
#             .document("class")
#             .collection(str(class_name))
#             .document("messages")
#             .collection("items")
#         )

#         # メッセージ取得（最新→古い）
#         all_msgs = []
#         for d in ref.order_by("timestamp", direction="DESCENDING").limit(100).stream():

#             m = d.to_dict()
#             if m:
#                 all_msgs.append(m)

#         # 直近3件 & 過去
#         latest = all_msgs[:3]
#         older = all_msgs[3:]

#         # ✅ ① 過去履歴（expanderを上）
#         if older:
#             with st.expander(f"📜 過去の履歴を表示（{len(older)}件）"):
#                 for m in older[::-1]:  # 古い順
#                     ts = m.get("timestamp")
#                     jst = pytz.timezone("Asia/Tokyo")
#                     ts_jst = ts.astimezone(jst) if ts else None
#                     ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
#                     text = m.get("message", m.get("text", ""))

#                     st.markdown(
#                         f"""
#                         <div style="display:flex; justify-content:flex-start; margin:10px 0;">
#                             <div style="
#                                 background:#f1f3f4;
#                                 padding:10px 14px;
#                                 border-radius:12px;
#                                 max-width:80%;
#                                 display:inline-block;
#                                 color:#111;
#                                 word-break:break-word;
#                             ">
#                                 {text}
#                             </div>
#                         </div>
#                         <div style="font-size:0.8em; color:#666; margin-left:4px;">
#                           {ts_str}
#                         </div>
#                         """,
#                         unsafe_allow_html=True
#                     )

#         # ✅ ② 直近3件（新しいほど下）
#         st.write("### 📌 直近3件")

#         for m in latest[::-1]:  # ← reverse
#             ts = m.get("timestamp")
#             jst = pytz.timezone("Asia/Tokyo")
#             ts_jst = ts.astimezone(jst) if ts else None
#             ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
#             text = m.get("message", m.get("text", ""))

#             st.markdown(
#                 f"""
#                 <div style="display:flex; justify-content:flex-start; margin:10px 0;">
#                     <div style="
#                         background:#f1f3f4;
#                         padding:10px 14px;
#                         border-radius:12px;
#                         max-width:80%;
#                         display:inline-block;
#                         color:#111;
#                         word-break:break-word;
#                     ">
#                         {text}
#                     </div>
#                 </div>
#                 <div style="font-size:0.8em; color:#666; margin-left:4px;">
#                   {ts_str}
#                 </div>
#                 """,
#                 unsafe_allow_html=True
#             )

#         st.divider()



#     # --- 全員宛履歴 ---
#     elif target_type == "全員":
#         st.subheader("🌏 全員宛メッセージ履歴")

#         all_ref = db.collection("rooms").document("all").collection("messages")

#         # メッセージ取得（最新→古い）
#         all_msgs = []
#         for d in all_ref.order_by("timestamp", direction="DESCENDING").limit(50).stream():
#             m = d.to_dict()
#             if m:
#                 all_msgs.append(m)

#         # 直近3件 & 過去
#         latest = all_msgs[:3]
#         older = all_msgs[3:]

#         # 過去履歴
#         if older:
#             with st.expander(f"📜 過去の履歴を表示（{len(older)}件）"):
#                 for m in older[::-1]:
#                     ts = m.get("timestamp")
#                     jst = pytz.timezone("Asia/Tokyo")
#                     ts_jst = ts.astimezone(jst) if ts else None
#                     ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
#                     text = m.get("message", m.get("text", ""))

#                     st.markdown(
#                         f"""
#                         <div style="display:flex; justify-content:flex-start; margin:10px 0;">
#                             <div style="
#                                 background:#f1f3f4;
#                                 padding:10px 14px;
#                                 border-radius:12px;
#                                 max-width:80%;
#                                 display:inline-block;
#                                 color:#111;
#                                 word-break:break-word;
#                             ">
#                                 {text}
#                             </div>
#                         </div>
#                         <div style="font-size:0.8em; color:#666; margin-left:4px;">
#                         {ts_str}
#                         </div>
#                         """,
#                         unsafe_allow_html=True
#                     )

#         # 直近3件
#         st.write("### 📌 直近3件")
#         for m in latest[::-1]:
#             ts = m.get("timestamp")
#             jst = pytz.timezone("Asia/Tokyo")
#             ts_jst = ts.astimezone(jst) if ts else None
#             ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
#             text = m.get("message", m.get("text", ""))

#             st.markdown(
#                 f"""
#                 <div style="display:flex; justify-content:flex-start; margin:10px 0;">
#                     <div style="
#                         background:#f1f3f4;
#                         padding:10px 14px;
#                         border-radius:12px;
#                         max-width:80%;
#                         display:inline-block;
#                         color:#111;
#                         word-break:break-word;
#                     ">
#                         {text}
#                     </div>
#                 </div>
#                 <div style="font-size:0.8em; color:#666; margin-left:4px;">
#                 {ts_str}
#                 </div>
#                 """,
#                 unsafe_allow_html=True
#             )

#         st.divider()




#     ######### 学年宛て ###########
#     elif target_type == "学年" and grade:
#         st.subheader(f"🏫 {grade} 宛メッセージ履歴")

#         ref = (
#             db.collection("rooms")
#             .document("grade")
#             .collection(grade)
#             .document("messages")
#             .collection("items")
#         )

#         # メッセージ取得（最新→古い）
#         grade_msgs = []
#         for d in ref.order_by("timestamp", direction="DESCENDING").limit(100).stream():
#             m = d.to_dict()
#             if m:
#                 grade_msgs.append(m)

#         # 直近3件 & 過去
#         latest = grade_msgs[:3]
#         older = grade_msgs[3:]

#         # ✅ ① 過去履歴（expander上）
#         if older:
#             with st.expander(f"📜 過去の履歴を表示（{len(older)}件）"):
#                 for m in older[::-1]:  # 古い順に表示
#                     ts = m.get("timestamp")
#                     jst = pytz.timezone("Asia/Tokyo")
#                     ts_jst = ts.astimezone(jst) if ts else None
#                     ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
#                     text = m.get("message", m.get("text", ""))

#                     st.markdown(
#                         f"""
#                         <div style="display:flex; justify-content:flex-start; margin:10px 0;">
#                             <div style="
#                                 background:#f1f3f4;
#                                 padding:10px 14px;
#                                 border-radius:12px;
#                                 max-width:80%;
#                                 display:inline-block;
#                                 color:#111;
#                                 word-break:break-word;
#                             ">
#                                 {text}
#                             </div>
#                         </div>
#                         <div style="font-size:0.8em; color:#666; margin-left:4px;">
#                           {ts_str}
#                         </div>
#                         """,
#                         unsafe_allow_html=True
#                     )

#         # ✅ ② 直近3件（新しいほど下）
#         st.write("### 📌 直近3件")

#         for m in latest[::-1]:  # 最新→古い を反転
#             ts = m.get("timestamp")
#             jst = pytz.timezone("Asia/Tokyo")
#             ts_jst = ts.astimezone(jst) if ts else None
#             ts_str = ts_jst.strftime("%Y-%m-%d %H:%M") if ts_jst else ""
#             text = m.get("message", m.get("text", ""))

#             st.markdown(
#                 f"""
#                 <div style="display:flex; justify-content:flex-start; margin:10px 0;">
#                     <div style="
#                         background:#f1f3f4;
#                         padding:10px 14px;
#                         border-radius:12px;
#                         max-width:80%;
#                         display:inline-block;
#                         color:#111;
#                         word-break:break-word;
#                     ">
#                         {text}
#                     </div>
#                 </div>
#                 <div style="font-size:0.8em; color:#666; margin-left:4px;">
#                   {ts_str}
#                 </div>
#                 """,
#                 unsafe_allow_html=True
#             )

#         st.divider()



#     # --- 送信欄 ---
#     st.markdown("---")
#     st.subheader("📨 メッセージ送信")

#     # ✅ フォーム形式に変更（反応率100%・ラグ消滅）
#     with st.form("send_form", clear_on_submit=True):
#         text = st.text_area("メッセージを入力", height=80)
#         send_clicked = st.form_submit_button("送信", use_container_width=True)

#     if send_clicked:
#         send_message(target_type, selected_id, grade, class_name, text)
#         st.success("送信しました")
