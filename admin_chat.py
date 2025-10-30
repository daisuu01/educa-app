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

# --- 削除ボタン ---

DOTS_BUTTON_STYLE = """
<style>
div[data-testid^="stButton"][key^="dots_"] button {
  background: transparent !important;
  color: #888 !important;
  border: none !important;
  padding: 0 !important;
  font-size: 18px !important;
  line-height: 1 !important;
  cursor: pointer !important;
}
div[data-testid^="stButton"][key^="dots_"] button:hover {
  color: #444 !important;
}
</style>
"""
st.markdown(DOTS_BUTTON_STYLE, unsafe_allow_html=True)

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
        if "admin" not in m.get("read_by", []) and m.get("sender", "").startswith("student"):
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
# 🔹 メッセージ送信（個人・グループ対応）
# ==================================================
def send_message(target_type: str, user_id: str = None, grade: str = None, class_name: str = None, text: str = ""):
    if not text.strip():
        return

    data = {
        "text": text.strip(),
        "sender": "admin",
        "timestamp": datetime.now(timezone.utc),
        "read_by": ["admin"],
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
        ref = (
            db.collection("rooms")
            .document("grade")
            .collection(grade)
            .document("messages")
            .collection("items")
        )
        ref.add(data)

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
        ref = (
            db.collection("rooms")
            .document("class")
            .collection(str(class_name))
            .document("messages")
            .collection("items")
        )
        ref.add(data)


# ==================================================
# 🖥️ 管理者用チャットUI
# ==================================================
def show_admin_chat(initial_student_id=None):
    st.title("💬 管理者チャット管理")

    # --- URLクエリでの操作（削除）を先に処理 ---
    params = st.query_params
    if params.get("act") == "del":
        mid = params.get("mid")
        uid = params.get("uid")
        org = params.get("org", "personal")
        if mid and uid:
            delete_message({"id": mid, "_origin": org}, uid)
        # クエリを消して画面をきれいに戻す
        st.query_params.clear()
        st.rerun()

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

        for msg in messages:
            sender = msg.get("sender", "")
            text = msg.get("text", "")
            ts = msg.get("timestamp")
            ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
            read_by = msg.get("read_by", [])
            msg_id = msg.get("id")

            # --------------------------------------------------------
            # 🔹 管理者メッセージ（吹き出し＋三点リーダー）
            # --------------------------------------------------------
            if sender == "admin":
                guardian_read = "✅ 保護者既読" if "student_保護者" in read_by else "❌ 保護者未読"
                guardian_color = "#1a73e8" if "student_保護者" in read_by else "#d93025"

                bubble = f"""
<div style="display:flex; align-items:flex-start; gap:6px; margin:10px 0;">

  <!-- 吹き出し：テキストのみ -->
  <div style="
    background:#d2e3fc;
    padding:10px 14px;
    border-radius:12px;
    max-width:80%;
    display:inline-block;
    color:#111;
    word-break:break-word;
  ">
    {text}
  </div>

  <!-- 三点リーダー -->
  <div style="position:relative; flex-shrink:0;">
    <button id="dots_{msg_id}" style="
      background:#fff; border:1px solid #ccc; border-radius:8px;
      width:28px; height:28px; font-size:16px; cursor:pointer;">
      ⋯
    </button>

    <div id="menu_{msg_id}" style="
      display:none; position:absolute; top:0; left:34px; z-index:2000;
      background:#fff; border:1px solid #ddd; border-radius:8px; padding:6px;
      min-width:120px; box-shadow:0 4px 10px rgba(0,0,0,0.08);">

      <button onclick="navigator.clipboard.writeText({json.dumps(text)}); alert('コピーしました');"
        style="width:100%; text-align:left; background:#fff; border:none; padding:8px; cursor:pointer;">
        📋 コピー
      </button>

      <a href='?act=del&mid={msg_id}&uid={selected_id}&org=personal'
        style="display:block; text-decoration:none; color:#c00; padding:8px;">
        🗑️ 削除
      </a>
    </div>
  </div>
</div>

<!-- 🔹 吹き出し外：時刻＋既読 -->
<div style="font-size:0.8em; color:#666; margin-left:4px; margin-top:-4px;">
  {ts_str}
  <span style="color:{guardian_color}; margin-left:6px;">{guardian_read}</span>
</div>

<script>
(function(){{  
  const b = document.getElementById("dots_{msg_id}");
  const m = document.getElementById("menu_{msg_id}");
  if (b && m){{  
    b.onclick = (e)=>{{  
      e.stopPropagation();
      m.style.display = (m.style.display === "block") ? "none" : "block";
    }};
    document.addEventListener("click",(ev)=>{{  
      if(!m.contains(ev.target) && ev.target !== b) m.style.display="none";
    }});
  }}
}})();
</script>
"""
                components_html(bubble, height=400, scrolling=False)


            # --------------------------------------------------------
            # 🔹 ユーザー側（右寄せ）
            # --------------------------------------------------------
            else:
                sender_label = "👦 生徒" if sender == "student_生徒" else "👨‍👩‍👧 保護者"
                st.markdown(
                    f"""
                    <div style="text-align:right;margin:10px 0;">
                        <div style="font-size:0.8em;color:#666;">{sender_label}</div>
                        <div style="display:inline-block;background-color:#f1f3f4;
                                    padding:10px 14px;border-radius:12px;
                                    max-width:80%;color:#111;">{text}</div>
                        <div style="font-size:0.8em;color:#666;">{ts_str}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )






        # --- 過去履歴 ---
        if older:
            with st.expander(f"📜 過去の履歴を表示（{len(older)}件）"):
                for msg in older:
                    sender = msg.get("sender", "")
                    text = msg.get("text", "")
                    ts = msg.get("timestamp")
                    ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
                    read_by = msg.get("read_by", [])
                    msg_id = msg.get("id")

                    if sender == "admin":
                        guardian_read = "✅ 保護者既読" if "student_保護者" in read_by else "❌ 保護者未読"
                        guardian_color = "#1a73e8" if "student_保護者" in read_by else "#d93025"

                        col1, col2 = st.columns([9, 1])
                        with col1:
                            st.markdown(
                                f"""
                                <div style="position: relative; text-align:right; margin:8px 0;">
                                  <div style="display:inline-block; background-color:#d2e3fc;
                                              padding:10px 14px; border-radius:12px;
                                              max-width:80%; color:#111; position:relative;">
                                    {text}
                                  </div>
                                  <div style="font-size:0.8em; color:#666; margin-top:3px;">{ts_str}</div>
                                  <div style="font-size:0.85em; margin-top:2px; color:{guardian_color};">{guardian_read}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        with col2:
                            if msg_id:
                                st.markdown(
                                    f"""
                                    <style>
                                    .dots-button-old-{msg_id} {{
                                        position: relative;
                                        margin-top: -10px;
                                        background: #f8f9fa;
                                        border: 1px solid #ddd;
                                        border-radius: 6px;
                                        font-size: 13px;
                                        padding: 2px 6px;
                                        cursor: pointer;
                                    }}
                                    </style>
                                    """,
                                    unsafe_allow_html=True
                                )

                                toggle_key = f"show_menu_old_{msg_id}"
                                if toggle_key not in st.session_state:
                                    st.session_state[toggle_key] = False

                                if st.button("⋯", key=f"dots_old_{msg_id}", help="操作メニューを開く"):
                                    st.session_state[toggle_key] = not st.session_state[toggle_key]

                                if st.session_state[toggle_key]:
                                    col_a, col_b = st.columns(2)
                                    with col_a:
                                        if st.button("📋 コピー", key=f"copy_old_{msg_id}"):
                                            import pyperclip
                                            pyperclip.copy(text)
                                            st.toast("メッセージをコピーしました。")
                                            st.session_state[toggle_key] = False
                                    with col_b:
                                        if st.button("🗑️ 削除", key=f"del_old_{msg_id}"):
                                            delete_message(msg, selected_id)
                                            st.session_state[toggle_key] = False
                                            st.rerun()
                            else:
                                st.markdown("<div style='font-size:0.72em;color:#bbb;text-align:center;'>—</div>", unsafe_allow_html=True)







    # --- 以下（クラス宛、全員宛、学年宛、送信欄）は変更なし ---
    # （元のコードのままでOK）




    # --- クラス宛履歴 ---
    elif target_type == "クラス" and class_name:
        st.subheader(f"👥 {class_name} 宛メッセージ履歴")

        # 直近3件
        ref = (
            db.collection("rooms")
            .document("class")
            .collection(str(class_name))
            .document("messages")
            .collection("items")
        )

        for d in ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(3).stream():
            m = d.to_dict()
            if not m:
                continue
            msg_id = d.id
            ts = m.get("timestamp")
            ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
            text = m.get("text", "")

            col1, col2 = st.columns([9, 1])
            with col1:
                st.markdown(
                    f"""<div style="margin:6px 0;background-color:#f1f3f4;
                    padding:10px 14px;border-radius:12px;">{text}
                    <div style="font-size:0.8em;color:#666;">{ts_str}</div></div>""",
                    unsafe_allow_html=True
                )

            # 🔹 三点リーダーボタン（⋯）右上メニュー
            with col2:
                if msg_id:
                    if st.button("⋯", key=f"dots_class_{msg_id}", help="操作メニューを開く"):
                        with st.popover(f"menu_class_{msg_id}", use_container_width=True):
                            if st.button("📋 コピー", key=f"copy_class_{msg_id}"):
                                import pyperclip
                                pyperclip.copy(text)
                                st.toast("メッセージをコピーしました。")
                            if st.button("🗑️ 削除", key=f"del_class_{msg_id}"):
                                msg_data = {"id": msg_id, "_origin": "class", "_class_name": class_name}
                                delete_message(msg_data, selected_id)
                                st.rerun()
                else:
                    st.markdown("<div style='font-size:0.72em;color:#bbb;text-align:center;'>—</div>", unsafe_allow_html=True)

        # 過去履歴
        with st.expander("📜 過去の履歴を表示"):
            for d in ref.order_by("timestamp", direction=firestore.Query.DESCENDING).stream():
                m = d.to_dict()
                if not m:
                    continue
                msg_id = d.id
                ts = m.get("timestamp")
                ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
                text = m.get("text", "")

                col1, col2 = st.columns([9, 1])
                with col1:
                    st.markdown(
                        f"""<div style="margin:6px 0;background-color:#f1f3f4;
                        padding:10px 14px;border-radius:12px;">{text}
                        <div style="font-size:0.8em;color:#666;">{ts_str}</div></div>""",
                        unsafe_allow_html=True
                    )

                with col2:
                    if msg_id:
                        if st.button("⋯", key=f"dots_class_old_{msg_id}", help="操作メニューを開く"):
                            with st.popover(f"menu_class_old_{msg_id}", use_container_width=True):
                                if st.button("📋 コピー", key=f"copy_class_old_{msg_id}"):
                                    import pyperclip
                                    pyperclip.copy(text)
                                    st.toast("メッセージをコピーしました。")
                                if st.button("🗑️ 削除", key=f"del_class_old_{msg_id}"):
                                    msg_data = {"id": msg_id, "_origin": "class", "_class_name": class_name}
                                    delete_message(msg_data, selected_id)
                                    st.rerun()
                    else:
                        st.markdown("<div style='font-size:0.72em;color:#bbb;text-align:center;'>—</div>", unsafe_allow_html=True)

    # --- 全員宛履歴 ---
    elif target_type == "全員":
        st.subheader("🌏 全員宛メッセージ履歴")

        all_ref = db.collection("rooms").document("all").collection("messages")

        # 直近3件
        for d in all_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(3).stream():
            m = d.to_dict()
            if not m:
                continue
            msg_id = d.id
            ts = m.get("timestamp")
            ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
            text = m.get("text", "")

            col1, col2 = st.columns([9, 1])
            with col1:
                st.markdown(
                    f"""<div style="margin:6px 0;background-color:#f1f3f4;
                    padding:10px 14px;border-radius:12px;">{text}
                    <div style="font-size:0.8em;color:#666;">{ts_str}</div></div>""",
                    unsafe_allow_html=True
                )

            # 🔹 三点リーダーボタン（⋯）
            with col2:
                if msg_id:
                    if st.button("⋯", key=f"dots_all_{msg_id}", help="操作メニューを開く"):
                        with st.popover(f"menu_all_{msg_id}", use_container_width=True):
                            if st.button("📋 コピー", key=f"copy_all_{msg_id}"):
                                import pyperclip
                                pyperclip.copy(text)
                                st.toast("メッセージをコピーしました。")
                            if st.button("🗑️ 削除", key=f"del_all_{msg_id}"):
                                msg_data = {"id": msg_id, "_origin": "all"}
                                delete_message(msg_data, selected_id)
                                st.rerun()
                else:
                    st.markdown("<div style='font-size:0.72em;color:#bbb;text-align:center;'>—</div>", unsafe_allow_html=True)

        # 📜 過去履歴
        with st.expander("📜 過去の履歴を表示"):
            for d in all_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).stream():
                m = d.to_dict()
                if not m:
                    continue
                msg_id = d.id
                ts = m.get("timestamp")
                ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
                text = m.get("text", "")

                col1, col2 = st.columns([9, 1])
                with col1:
                    st.markdown(
                        f"""<div style="margin:6px 0;background-color:#f1f3f4;
                        padding:10px 14px;border-radius:12px;">{text}
                        <div style="font-size:0.8em;color:#666;">{ts_str}</div></div>""",
                        unsafe_allow_html=True
                    )

                with col2:
                    if msg_id:
                        if st.button("⋯", key=f"dots_all_old_{msg_id}", help="操作メニューを開く"):
                            with st.popover(f"menu_all_old_{msg_id}", use_container_width=True):
                                if st.button("📋 コピー", key=f"copy_all_old_{msg_id}"):
                                    import pyperclip
                                    pyperclip.copy(text)
                                    st.toast("メッセージをコピーしました。")
                                if st.button("🗑️ 削除", key=f"del_all_old_{msg_id}"):
                                    msg_data = {"id": msg_id, "_origin": "all"}
                                    delete_message(msg_data, selected_id)
                                    st.rerun()
                    else:
                        st.markdown("<div style='font-size:0.72em;color:#bbb;text-align:center;'>—</div>", unsafe_allow_html=True)


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

        # 直近3件
        for d in ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(3).stream():
            m = d.to_dict()
            if not m:
                continue
            msg_id = d.id
            ts = m.get("timestamp")
            ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
            text = m.get("text", "")

            col1, col2 = st.columns([9, 1])
            with col1:
                st.markdown(
                    f"""<div style="margin:6px 0;background-color:#f1f3f4;
                    padding:10px 14px;border-radius:12px;">{text}
                    <div style="font-size:0.8em;color:#666;">{ts_str}</div></div>""",
                    unsafe_allow_html=True
                )

            # 🔹 三点リーダーボタン（⋯）右上メニュー
            with col2:
                if msg_id:
                    if st.button("⋯", key=f"dots_grade_{msg_id}", help="操作メニューを開く"):
                        with st.popover(f"menu_grade_{msg_id}", use_container_width=True):
                            if st.button("📋 コピー", key=f"copy_grade_{msg_id}"):
                                import pyperclip
                                pyperclip.copy(text)
                                st.toast("メッセージをコピーしました。")
                            if st.button("🗑️ 削除", key=f"del_grade_{msg_id}"):
                                msg_data = {"id": msg_id, "_origin": "grade", "_grade": grade}
                                delete_message(msg_data, selected_id)
                                st.rerun()
                else:
                    st.markdown("<div style='font-size:0.72em;color:#bbb;text-align:center;'>—</div>", unsafe_allow_html=True)

        # 📜 過去履歴
        with st.expander("📜 過去の履歴を表示"):
            for d in ref.order_by("timestamp", direction=firestore.Query.DESCENDING).stream():
                m = d.to_dict()
                if not m:
                    continue
                msg_id = d.id
                ts = m.get("timestamp")
                ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
                text = m.get("text", "")

                col1, col2 = st.columns([9, 1])
                with col1:
                    st.markdown(
                        f"""<div style="margin:6px 0;background-color:#f1f3f4;
                        padding:10px 14px;border-radius:12px;">{text}
                        <div style="font-size:0.8em;color:#666;">{ts_str}</div></div>""",
                        unsafe_allow_html=True
                    )

                with col2:
                    if msg_id:
                        if st.button("⋯", key=f"dots_grade_old_{msg_id}", help="操作メニューを開く"):
                            with st.popover(f"menu_grade_old_{msg_id}", use_container_width=True):
                                if st.button("📋 コピー", key=f"copy_grade_old_{msg_id}"):
                                    import pyperclip
                                    pyperclip.copy(text)
                                    st.toast("メッセージをコピーしました。")
                                if st.button("🗑️ 削除", key=f"del_grade_old_{msg_id}"):
                                    msg_data = {"id": msg_id, "_origin": "grade", "_grade": grade}
                                    delete_message(msg_data, selected_id)
                                    st.rerun()
                    else:
                        st.markdown("<div style='font-size:0.72em;color:#bbb;text-align:center;'>—</div>", unsafe_allow_html=True)



    # --- 送信欄 ---
    st.markdown("---")
    st.subheader("📨 メッセージ送信")
    text = st.text_area("メッセージを入力", height=80, key="admin_chat_input")
    if st.button("送信", use_container_width=True):
        send_message(target_type, selected_id, grade, class_name, text)
        st.rerun()
