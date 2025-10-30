# =============================================
# main.py（英作文＋チャット機能統合版・個人チャット遷移対応）
# =============================================

import streamlit as st

# --- ページ設定 ---
st.set_page_config(page_title="エデュカアプリログイン", layout="centered")



from firebase_utils import (
    verify_password,
    update_user_password,
    import_students_from_excel_and_csv,
    fetch_all_users,
    USERS,
)
from english_corrector import show_essay_corrector
from user_chat import show_chat_page, get_user_meta
from admin_chat import show_admin_chat
from admin_inbox import show_admin_inbox
from firebase_admin import firestore



# --- 状態管理 ---
if "login" not in st.session_state:
    st.session_state["login"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "member_id" not in st.session_state:
    st.session_state["member_id"] = None
if "student_page" not in st.session_state:
    st.session_state["student_page"] = "menu"
if "admin_mode" not in st.session_state:   # ← 管理者モードの保持
    st.session_state["admin_mode"] = "生徒登録"

db = firestore.client()

# =====================================================
# 🔹 共通：戻るボタン
# =====================================================
def show_back_button_top(key: str):
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("⬅️ 戻る", key=key, use_container_width=True):
            st.session_state["student_page"] = "menu"
            st.rerun()

def show_back_button_bottom(key: str):
    st.markdown("<br><br><hr>", unsafe_allow_html=True)
    if st.button("⬅️ 戻る", key=key, use_container_width=True):
        st.session_state["student_page"] = "menu"
        st.rerun()

# =====================================================
# 🔸 未読メッセージチェック
# =====================================================
def has_unread_messages(user_id: str) -> bool:
    """管理者からの未読メッセージがあるか確認"""
    ref = (
        db.collection("rooms")
        .document("personal")
        .collection(user_id)
        .document("messages")
        .collection("items")
    )
    docs = ref.where("sender", "==", "admin").limit(50).stream()
    for d in docs:
        m = d.to_dict()
        if m and "student" not in m.get("read_by", []):
            return True
    return False


# ===============================
# 🔐 ログイン画面
# ===============================
if not st.session_state["login"]:
    st.title("エデュカアプリログイン")

    member_id = st.text_input("会員番号")
    password = st.text_input("パスワード", type="password")

    if st.button("ログイン"):
        if member_id == "1001" and password == "educa123":
            st.session_state.update({"login": True, "role": "admin"})
            st.session_state["admin_mode"] = "生徒登録"
            st.rerun()
        else:
            doc = USERS.document(member_id).get()
            if not doc.exists:
                st.error("⚠️ ユーザーが見つかりません。")
            else:
                user = doc.to_dict()
                if verify_password(password, user):
                    st.session_state.update({
                        "login": True,
                        "role": user.get("role", "student"),
                        "member_id": member_id
                    })
                    st.rerun()
                else:
                    st.error("❌ パスワードが違います。")


# ===============================
# 🧭 管理者画面
# ===============================
elif st.session_state["role"] == "admin":
    st.sidebar.title("📋 管理者メニュー")

    # ✅ admin_mode を維持（rerun時も保持される）
    st.session_state["admin_mode"] = st.sidebar.radio(
        "モードを選択してください",
        ["生徒登録", "登録済みユーザー一覧", "チャット管理", "受信ボックス"],
        index=["生徒登録", "登録済みユーザー一覧", "チャット管理", "受信ボックス"].index(
            st.session_state.get("admin_mode", "生徒登録")
        )
    )

    mode = st.session_state["admin_mode"]

    # ---- 各モード処理 ----
    if mode == "生徒登録":
        st.markdown("#### 🔽 生徒情報と初期PW対応表をアップロード")
        excel_file = st.file_uploader("📘 Excelファイル", type=["xlsx"])
        csv_file = st.file_uploader("📄 CSVファイル", type=["csv"])
        if excel_file and csv_file:
            st.info("アップロードされたファイルを確認中...")
            result = import_students_from_excel_and_csv(excel_file, csv_file)
            if len(result) > 0:
                st.success("Firestoreへ登録が完了しました ✅")
                st.dataframe(result, use_container_width=True)
            else:
                st.warning("⚠ 登録対象が見つかりません。")

    elif mode == "登録済みユーザー一覧":
        st.markdown("#### 👥 Firestore 登録済みユーザー一覧")
        df_users = fetch_all_users()
        st.dataframe(df_users, use_container_width=True)

    elif mode == "チャット管理":
        # ★ 受信ボックスで選択された生徒がある場合、その生徒を初期表示
        if "selected_student_id" in st.session_state:
            target_id = st.session_state["selected_student_id"]
            target_name = st.session_state.get("selected_student_name", "")
            st.markdown(f"### 🧑‍🎓 {target_name}（ID: {target_id}）とのチャット")
            show_admin_chat(initial_student_id=target_id)  # ★ 引数追加対応版
            # 一度開いたら選択情報をクリア
            del st.session_state["selected_student_id"]
            if "selected_student_name" in st.session_state:
                del st.session_state["selected_student_name"]
        else:
            show_admin_chat()

        if "open_mode" in st.session_state and st.session_state["open_mode"] == "admin_chat":
            st.session_state["open_mode"] = None

    elif mode == "受信ボックス":
        show_admin_inbox()
        if "open_mode" in st.session_state and st.session_state["open_mode"] == "admin_chat":
            st.session_state["open_mode"] = None
            st.session_state["admin_mode"] = "チャット管理"  # ✅ ← チャットモードへ変更
            st.session_state["just_opened_from_inbox"] = True
            st.rerun()  # ✅ ← これで確実に遷移！

    st.sidebar.markdown("---")
    if st.sidebar.button("ログアウト"):
        st.session_state["login"] = False
        st.rerun()


# ===============================
# 🎓 生徒ページ
# ===============================
elif st.session_state["role"] == "student":
    member_id = st.session_state["member_id"]
    doc = USERS.document(member_id).get()

    if not doc.exists:
        st.error("⚠️ ユーザーデータが見つかりません。")
    else:
        if st.session_state["student_page"] == "menu":
            st.title("🎓 学習メニュー")
            st.markdown("以下から利用する機能を選択してください。")

            new_flag = has_unread_messages(member_id)

            col1, col2, col3 = st.columns(3)
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
                            animation: pulse 1.5s infinite;
                        ">💬 チャット　　　　<br>（未読あり）</button>
                        <span style="position:absolute;top:2px;right:2px;
                            background:red;color:white;font-size:12px;
                            padding:2px 6px;border-radius:50%;">●</span>
                    </div>

                    <style>
                    @keyframes pulse {
                        0% { box-shadow: 0 0 5px #1E90FF; }
                        50% { box-shadow: 0 0 25px #00BFFF; }
                        100% { box-shadow: 0 0 5px #1E90FF; }
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    if st.button("▶ 開く", use_container_width=True, key="btn_chat_new"):
                        st.session_state["student_page"] = "chat"
                        st.rerun()
                else:
                    if st.button("💬 チャット", use_container_width=True, key="btn_chat"):
                        st.session_state["student_page"] = "chat"
                        st.rerun()

            with col2:
                if st.button("📝 英作文添削", use_container_width=True, key="btn_essay"):
                    st.session_state["student_page"] = "essay"
                    st.rerun()
            with col3:
                if st.button("🔑 パスワード変更", use_container_width=True, key="btn_password"):
                    st.session_state["student_page"] = "password"
                    st.rerun()

            st.markdown("---")
            if st.button("🚪 ログアウト", key="btn_logout"):
                st.session_state["login"] = False
                st.session_state["student_page"] = "menu"
                st.rerun()

        elif st.session_state["student_page"] == "chat":
            show_back_button_top("back_chat_top")
            grade, class_name = get_user_meta(member_id)
            grade = grade or "未設定"
            class_name = class_name or "未設定"
            show_chat_page(member_id, grade, class_name)
            show_back_button_bottom("back_chat_bottom")

        elif st.session_state["student_page"] == "essay":
            show_back_button_top("back_essay_top")
            show_essay_corrector(member_id)
            show_back_button_bottom("back_essay_bottom")

        elif st.session_state["student_page"] == "password":
            show_back_button_top("back_pw_top")
            st.title("🔑 パスワード変更")
            new_pw = st.text_input("新しいパスワード", type="password")
            confirm_pw = st.text_input("新しいパスワード（確認）", type="password")
            if st.button("変更を保存", key="save_password"):
                if not new_pw or not confirm_pw:
                    st.warning("⚠ 両方の欄を入力してください。")
                elif new_pw != confirm_pw:
                    st.error("❌ パスワードが一致しません。")
                else:
                    update_user_password(member_id, new_pw)
                    st.success("✅ パスワードを変更しました。")
            show_back_button_bottom("back_pw_bottom")
