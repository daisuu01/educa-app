# =============================================
# pages/1_ユーザー_ホーム.py（生徒ホーム）
# =============================================

import streamlit as st
from firebase_admin import firestore
from firebase_utils import USERS
from english_corrector import show_essay_corrector
from user_chat import show_chat_page, get_user_meta
from english_conversation import show_english_conversation

# --- ページ設定 ---
st.set_page_config(page_title="ユーザーホーム", layout="centered")

# --- サイドバー完全非表示（ログイン後も非表示にする） ---
st.markdown("""
<style>
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stSidebarCollapsedControl"] { display: none !important; }

/* メイン幅最大化 */
div[data-testid="stAppViewContainer"] > section:first-child {
    width: 100% !important;
    max-width: 100% !important;
    margin-left: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# --- ログインチェック ---
if not st.session_state.get("login"):
    st.session_state["login"] = False
    st.session_state["role"] = None
    st.session_state["member_id"] = None
    st.rerun()

member_id = st.session_state.get("member_id")

# --- Firestore クライアント ---
db = firestore.client()

# ===============================
# 🔍 未読メッセージチェック
# ===============================
def has_unread_messages(user_id: str) -> bool:

    doc = USERS.document(user_id).get()
    u = doc.to_dict() if doc.exists else {}
    grade = u.get("grade")
    class_name = u.get("class_name")

    def check_ref(ref):
        for d in ref.stream():
            m = d.to_dict()
            if m.get("sender") == "admin" and user_id not in m.get("read_by", []):
                return True
        return False

    # 個人
    personal_ref = (
        db.collection("rooms")
        .document("personal")
        .collection(user_id)
        .document("messages")
        .collection("items")
    )
    if check_ref(personal_ref):
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
    all_ref = (
        db.collection("rooms")
        .document("all")
        .collection("messages")
    )
    if check_ref(all_ref):
        return True

    return False


# ===============================
# 🎓 ホーム UI
# ===============================
st.title("🎓 学習メニュー")
st.markdown("利用する機能を選択してください。")

new_flag = has_unread_messages(member_id)

# === 1行目：チャット・英作文・パスワード ===
col1, col2, col3 = st.columns(3)

# -------------------------
# 💬 チャット
# -------------------------
with col1:
    if new_flag:
        st.markdown("""
        <div style="position:relative; display:inline-block;">
            <button style="
                background-color:#1E90FF;
                color:white;
                font-size:18px;
                font-weight:bold;
                padding:12px 24px;
                border:none;
                border-radius:10px;
                box-shadow:0 0 20px #1E90FF;
                animation: pulse 1.5s infinite;">
                💬 チャット　　　　<br>（未読あり）
            </button>
            <span style="
                position:absolute;
                top:2px;right:2px;
                background:red;
                color:white;
                font-size:12px;
                padding:2px 6px;
                border-radius:50%;">
                ●
            </span>
        </div>

        <style>
        @keyframes pulse {
            0% { box-shadow: 0 0 5px #1E90FF; }
            50% { box-shadow: 0 0 25px #00BFFF; }
            100% { box-shadow: 0 0 5px #1E90FF; }
        }
        </style>
        """, unsafe_allow_html=True)

        if st.button("▶ 開く", use_container_width=True, key="go_chat_new"):
            st.switch_page("10_ユーザー_チャット.py")

    else:
        if st.button("💬 チャット", use_container_width=True):
            st.switch_page("10_ユーザー_チャット.py")

# -------------------------
# 📝 英作文添削
# -------------------------
with col2:
    if st.button("📝 英作文添削", use_container_width=True):
        st.switch_page("20_ユーザー_英作文添削.py")

# -------------------------
# 🔑 パスワード変更
# -------------------------
with col3:
    if st.button("🔑 パスワード変更", use_container_width=True):
        st.switch_page("40_ユーザー_パスワード変更.py")

# === 2行目：英会話トレーナー（全幅） ===
st.markdown("<br>", unsafe_allow_html=True)

if st.button("🎧 英会話トレーナー", use_container_width=True):
    st.switch_page("30_ユーザー_英会話トレーナー.py")

# === ログアウト ===
st.markdown("---")
if st.button("🚪 ログアウト"):
    for key in ["login", "member_id", "role"]:
        st.session_state[key] = None
    st.rerun()
