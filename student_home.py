# =============================================
# student_home.py（生徒メニュー完全版）
# =============================================

import streamlit as st
import firebase_admin
from firebase_admin import firestore

# --- Firestore は main.py で初期化済み ---
db = firestore.client()
USERS = db.collection("users")

# --- 必要関数 ---
from firebase_utils import update_user_password, USERS
from user_chat import show_chat_page, get_user_meta
from english_corrector import show_essay_corrector
from english_conversation import show_english_conversation


# ===========================
# 🔐 ログイン前のアクセス防止
# ===========================
if not st.session_state.get("login"):
    st.error("⚠️ ログインが必要です。main.py からアクセスしてください。")
    st.stop()

if st.session_state.get("role") != "student":
    st.error("⚠️ 生徒専用ページです。")
    st.stop()


# ===========================
# 受信未読チェック（生徒用）
# ===========================
def has_unread_messages(user_id: str) -> bool:
    doc = USERS.document(user_id).get()
    u = doc.to_dict() if doc.exists else {}
    grade = u.get("grade")
    class_name = u.get("class_name")

    def check_ref(ref):
        docs = ref.where("sender", "==", "admin").stream()
        for d in docs:
            m = d.to_dict()
            if user_id not in m.get("read_by", []):
                return True
        return False

    # 個人
    personal = (
        db.collection("rooms")
        .document("personal")
        .collection(user_id)
        .document("messages")
        .collection("items")
    )
    if check_ref(personal):
        return True

    # クラス
    if class_name:
        class_ref = (
            db.collection("rooms")
            .document("class")
            .collection(str(class_name))
            .document("messages")
            .collection("items")
        )
        if check_ref(class_ref):
            return True

    # 学年
    if grade:
        grade_ref = (
            db.collection("rooms")
            .document("grade")
            .collection(str(grade))
            .document("messages")
            .collection("items")
        )
        if check_ref(grade_ref):
            return True

    # 全体
    all_ref = db.collection("rooms").document("all").collection("messages")
    if check_ref(all_ref):
        return True

    return False


# ===========================
# 🔙 共通の戻るボタン
# ===========================
def back_to_menu(key):
    st.markdown("<br><hr>", unsafe_allow_html=True)
    if st.button("⬅️ メニューに戻る", key=key, use_container_width=True):
        st.session_state["student_page"] = "menu"
        st.rerun()


# ===========================
# 🎓 初期化
# ===========================
if "student_page" not in st.session_state:
    st.session_state["student_page"] = "menu"

member_id = st.session_state["member_id"]
doc = USERS.document(member_id).get()

if not doc.exists:
    st.error("⚠️ ユーザーデータが見つかりません。")
    st.stop()


# ===========================
# 🎓 メニュー画面
# ===========================
if st.session_state["student_page"] == "menu":

    st.title("🎓 学習メニュー")
    st.markdown("利用する機能を選択してください。")

    unread = has_unread_messages(member_id)

    # --- 1段目：チャット / 英作文 / パスワード ---
    col1, col2, col3 = st.columns(3)

    # 💬 チャット
    with col1:
        if unread:
            st.markdown(
                """
                <div style="position:relative; display:inline-block;">
                    <button style="
                        background-color:#1E90FF;
                        color:white;
                        font-size:18px;
                        font-weight:bold;
                        padding:14px 20px;
                        border:none;
                        border-radius:10px;
                        box-shadow:0 0 20px #1E90FF;
                        animation:pulse 1.5s infinite;
                    ">💬 チャット（未読）</button>
                    <span style="
                        position:absolute;
                        top:0; right:0;
                        background:red;
                        color:white;
                        font-size:12px;
                        padding:2px 6px;
                        border-radius:50%;
                    ">●</span>
                </div>
                <style>
                @keyframes pulse {
                    0% { box-shadow:0 0 5px #1E90FF; }
                    50% { box-shadow:0 0 25px #00BFFF; }
                    100% { box-shadow:0 0 5px #1E90FF; }
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            if st.button("▶ 開く", use_container_width=True, key="go_chat_new"):
                st.session_state["student_page"] = "chat"
                st.rerun()
        else:
            if st.button("💬 チャット", use_container_width=True, key="go_chat"):
                st.session_state["student_page"] = "chat"
                st.rerun()

    # 📝 英作文添削
    with col2:
        if st.button("📝 英作文添削", use_container_width=True):
            st.session_state["student_page"] = "essay"
            st.rerun()

    # 🔑 パスワード変更
    with col3:
        if st.button("🔑 パスワード変更", use_container_width=True):
            st.session_state["student_page"] = "password"
            st.rerun()

    # --- 2段目：英会話 ---
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🎧 英会話トレーナー", use_container_width=True):
        st.session_state["student_page"] = "conversation"
        st.rerun()

    # 🔚 ログアウト
    st.markdown("---")
    if st.button("🚪 ログアウト"):
        st.session_state.clear()
        st.rerun()


# ===========================
# 💬 チャットページ
# ===========================
elif st.session_state["student_page"] == "chat":
    st.title("💬 チャット")
    grade, class_name = get_user_meta(member_id)
    show_chat_page(member_id, grade or "未設定", class_name or "未設定")
    back_to_menu("back_chat")


# ===========================
# 📝 英作文添削ページ
# ===========================
elif st.session_state["student_page"] == "essay":
    st.title("📝 英作文添削")
    show_essay_corrector(member_id)
    back_to_menu("back_essay")


# ===========================
# 🎧 英会話トレーナー
# ===========================
elif st.session_state["student_page"] == "conversation":
    st.title("🎧 英会話トレーナー")
    show_english_conversation()
    back_to_menu("back_conversation")


# ===========================
# 🔑 パスワード変更ページ
# ===========================
elif st.session_state["student_page"] == "password":
    st.title("🔑 パスワード変更")

    new_pw = st.text_input("新しいパスワード", type="password")
    confirm_pw = st.text_input("（確認）", type="password")

    if st.button("変更を保存"):
        if not new_pw or not confirm_pw:
            st.warning("⚠ すべて入力してください")
        elif new_pw != confirm_pw:
            st.error("❌ パスワードが一致しません")
        else:
            update_user_password(member_id, new_pw)
            st.success("✅ パスワードを変更しました")

    back_to_menu("back_pw")
