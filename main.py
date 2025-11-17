# =============================================
# main.py（Pages版：ログイン＋メインメニュー専用）
# =============================================

import streamlit as st

# --- ページ設定 ---
st.set_page_config(page_title="エデュカアプリログイン", layout="centered")

# --- 見た目系（スピナー/フェード抑制：今までのやつを簡略版で維持） ---
st.markdown("""
<style>
.stSpinner, div[data-testid="stSpinner"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
.stApp, .block-container {
    transition: none !important;
    opacity: 1 !important;
}
</style>
""", unsafe_allow_html=True)

from firebase_utils import (
    verify_password,
    USERS,
    db,
)

# ==============================
# 🔹 状態初期化
# ==============================
if "login" not in st.session_state:
    st.session_state["login"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "member_id" not in st.session_state:
    st.session_state["member_id"] = None

# 互換用（古いコードが参照していても壊れないようにしておく）
if "student_page" not in st.session_state:
    st.session_state["student_page"] = "menu"
if "admin_mode" not in st.session_state:
    st.session_state["admin_mode"] = "生徒登録"


# ==============================
# 🔸 未読メッセージチェック（ユーザー用メニューのバッジ）
# ==============================
def has_unread_messages(user_id: str) -> bool:
    """管理者からの未読メッセージがあるか（個人・クラス・学年・全体対応）"""

    doc = USERS.document(user_id).get()
    u = doc.to_dict() if doc.exists else {}
    grade = u.get("grade")
    class_name = u.get("class_name")

    def check_ref(ref):
        docs = ref.where("sender", "==", "admin").stream()
        for d in docs:
            m = d.to_dict()
            read_by = m.get("read_by", [])
            if user_id not in read_by:
                return True
        return False

    # 個人宛
    personal_ref = (
        db.collection("rooms")
        .document("personal")
        .collection(user_id)
        .document("messages")
        .collection("items")
    )
    if check_ref(personal_ref):
        return True

    # クラス宛
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

    # 学年宛
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

    # 全体宛
    all_ref = (
        db.collection("rooms")
        .document("all")
        .collection("messages")
    )
    if check_ref(all_ref):
        return True

    return False


# ==============================
# 🔐 ログイン画面
# ==============================
st.title("エデュカアプリログイン")

if not st.session_state["login"]:
    member_id = st.text_input("会員番号")
    password = st.text_input("パスワード", type="password")

    if st.button("ログイン"):
        doc = USERS.document(member_id).get()

        if not doc.exists:
            st.error("⚠️ ユーザーが見つかりません。")
        else:
            user = doc.to_dict()
            role = user.get("role", "student")

            if verify_password(password, user):
                st.session_state["login"] = True
                st.session_state["role"] = role
                st.session_state["member_id"] = member_id
                st.session_state["admin_name"] = user.get("name") if role == "admin" else None
                st.success(f"✅ ログインしました（{role}）")
                st.experimental_rerun()
            else:
                st.error("❌ パスワードが違います。")

else:
    role = st.session_state["role"]
    member_id = st.session_state["member_id"]

    # ==============================
    # 🎓 生徒メニュー
    # ==============================
    if role == "student":
        st.title("🎓 学習メニュー")
        st.markdown("以下から利用する機能を選択してください。")

        # 未読バッジ判定
        new_flag = has_unread_messages(member_id)

        # --- メニューリンク ---
        if new_flag:
            st.page_link(
                "pages/1_ユーザー_チャット.py",
                label="💬 チャット（未読あり）",
                icon="💬",
            )
        else:
            st.page_link(
                "pages/1_ユーザー_チャット.py",
                label="💬 チャット",
                icon="💬",
            )

        st.page_link(
            "pages/10_ユーザー_英作文添削.py",
            label="📝 英作文添削",
            icon="📝",
        )
        st.page_link(
            "pages/20_ユーザー_英会話トレーナー.py",
            label="🎧 英会話トレーナー",
            icon="🎧",
        )
        st.page_link(
            "pages/30_ユーザー_パスワード変更.py",
            label="🔑 パスワード変更",
            icon="🔑",
        )

        st.markdown("---")
        if st.button("🚪 ログアウト"):
            st.session_state.clear()
            st.experimental_rerun()

    # ==============================
    # 👨‍🏫 管理者メニュー
    # ==============================
    elif role == "admin":
        st.title("📋 管理者メニュー")

        st.page_link(
            "pages/1000_管理者_生徒登録.py",
            label="生徒登録",
        )
        st.page_link(
            "pages/1010_管理者_登録済みユーザー一覧.py",
            label="登録済みユーザー一覧",
        )
        st.page_link(
            "pages/1020_管理者_チャット管理.py",
            label="チャット管理",
        )
        st.page_link(
            "pages/1030_管理者_受信BOX.py",
            label="受信BOX",
        )
        st.page_link(
            "pages/1040_管理者_送信予約.py",
            label="送信予約",
        )
        st.page_link(
            "pages/1050_管理者_保護者未読一覧.py",
            label="保護者未読一覧",
        )

        st.markdown("---")
        if st.button("🚪 ログアウト"):
            st.session_state.clear()
            st.experimental_rerun()
















# # =============================================
# # main.py（英作文＋チャット機能統合版・個人チャット遷移対応・Firebase安全初期化対応）
# # =============================================

# import streamlit as st

# # --- ページ設定 ---
# st.set_page_config(page_title="エデュカアプリログイン", layout="centered")

# st.markdown("""
# <style>
# /* スピナー非表示 */
# .stSpinner, div[data-testid="stSpinner"] {
#     display: none !important;
# }

# /* Running 表示削除 */
# [data-testid="stStatusWidget"] {
#     display: none !important;
# }

# /* 通常のフェードを上書きするための保険 */
# .stApp, .block-container {
#     transition: none !important;
#     opacity: 1 !important;
# }
# </style>

# <script>
# // =============================
# // 透明フェード（opacity 0.33）を強制無効化
# // =============================
# function forceFullOpacity() {
#     const elements = document.querySelectorAll('div, section, main, header');
#     elements.forEach(el => {
#         if (el.style.opacity && el.style.opacity < 1) {
#             el.style.opacity = "1";   // 強制上書き
#         }
#     });
# }

# // Streamlit の DOM 変化を常に監視
# const observer = new MutationObserver(() => {
#     forceFullOpacity();
# });

# // body 全体を監視
# observer.observe(document.body, { childList: true, subtree: true });

# // 0.2 秒に1回、保険で実行
# setInterval(forceFullOpacity, 200);
# </script>
# """, unsafe_allow_html=True)

# from dotenv import load_dotenv
# import os
# import firebase_admin
# from firebase_admin import credentials, firestore
# from english_conversation import show_english_conversation


# # --- Firebase 初期化（Streamlit Cloud／ローカル両対応・安全版）---
# import json
# load_dotenv()

# if not firebase_admin._apps:
#     try:
#         # ✅ ① Streamlit Cloud 環境（secrets.toml に [firebase] がある場合）
#         if "firebase" in st.secrets:
#             firebase_config = dict(st.secrets["firebase"])  # ← これだけでOK
#             cred = credentials.Certificate(firebase_config)
#         else:
#             # ✅ ② ローカル環境（.env のパスを使う場合）
#             firebase_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "educa-app-firebase-adminsdk.json")
#             if not firebase_path or not os.path.exists(firebase_path):
#                 raise FileNotFoundError(f"Firebase認証ファイルが見つかりません: {firebase_path}")
#             cred = credentials.Certificate(firebase_path)

#         firebase_admin.initialize_app(cred)
#         db = firestore.client()

#     except Exception as e:
#         st.error(f"❌ Firebase初期化エラー: {e}")
#         st.stop()
# else:
#     db = firestore.client()



# # --- 状態管理 ---
# if "login" not in st.session_state:
#     st.session_state["login"] = False
# if "role" not in st.session_state:
#     st.session_state["role"] = None
# if "member_id" not in st.session_state:
#     st.session_state["member_id"] = None
# if "student_page" not in st.session_state:
#     st.session_state["student_page"] = "menu"
# if "admin_mode" not in st.session_state:  # ← 管理者モードの保持
#     st.session_state["admin_mode"] = "生徒登録"

# # --- role を正規化（"admin" → admin に統一）---
# if st.session_state["role"] is not None:
#     st.session_state["role"] = str(st.session_state["role"]).strip('"')

# # --- 必要モジュール読込 ---
# from firebase_utils import (
#     verify_password,
#     update_user_password,
#     import_students_from_excel_and_csv,
#     fetch_all_users,
#     USERS,
# )
# from english_corrector import show_essay_corrector
# from user_chat import show_chat_page, get_user_meta
# from admin_inbox import show_admin_inbox, count_unread_messages
# from admin_chat import show_admin_chat
# from admin_schedule import show_schedule_main
# from unread_guardian_list import show_unread_guardian_list

# db = firestore.client()


# # =====================================================
# # 🔹 共通：戻るボタン
# # =====================================================
# def show_back_button_top(key: str):
#     col1, col2 = st.columns([5, 1])
#     with col2:
#         if st.button("⬅️ 戻る", key=key, use_container_width=True):
#             st.session_state["student_page"] = "menu"
#             st.rerun()


# def show_back_button_bottom(key: str):
#     st.markdown("<br><br><hr>", unsafe_allow_html=True)
#     if st.button("⬅️ 戻る", key=key, use_container_width=True):
#         st.session_state["student_page"] = "menu"
#         st.rerun()

# # ===== 受信ボックスからの遷移処理 =====
# if "selected_student_id" in st.session_state:
#     initial_student_id = st.session_state["selected_student_id"]
# else:
#     initial_student_id = None

# # =====================================================
# # 🔸 未読メッセージチェック
# # =====================================================
# def has_unread_messages(user_id: str) -> bool:
#     """管理者からの未読メッセージがあるか（個人・クラス・学年・全体対応）"""

#     # ユーザー情報取得
#     doc = USERS.document(user_id).get()
#     u = doc.to_dict() if doc.exists else {}
#     grade = u.get("grade")
#     class_name = u.get("class_name")

#     def check_ref(ref):
#         docs = ref.where("sender", "==", "admin").stream()
#         for d in docs:
#             m = d.to_dict()
#             read_by = m.get("read_by", [])
#             if user_id not in read_by:
#                 return True
#         return False

#     # ✅ 個人宛
#     personal_ref = (
#         db.collection("rooms")
#         .document("personal")
#         .collection(user_id)
#         .document("messages")
#         .collection("items")
#     )
#     if check_ref(personal_ref):
#         return True

#     # ✅ クラス宛
#     if class_name:
#         class_ref = (
#             db.collection("rooms")
#             .document("class")
#             .collection(str(class_name))
#             .document("messages")
#             .collection("items")
#         )
#         if check_ref(class_ref):
#             return True

#     # ✅ 学年宛
#     if grade:
#         grade_ref = (
#             db.collection("rooms")
#             .document("grade")
#             .collection(str(grade))
#             .document("messages")
#             .collection("items")
#         )
#         if check_ref(grade_ref):
#             return True

#     # ✅ 全体宛（items 無し）
#     all_ref = (
#         db.collection("rooms")
#         .document("all")
#         .collection("messages")
#     )
#     if check_ref(all_ref):
#         return True

#     return False

# # ===============================
# # 🔐 ログイン画面（複数管理者対応版）
# # ===============================
# if not st.session_state["login"]:
#     st.title("エデュカアプリログイン")
#     member_id = st.text_input("会員番号")
#     password = st.text_input("パスワード", type="password")

#     if st.button("ログイン"):
#         # --- Firestore からユーザー情報を取得 ---
#         doc = USERS.document(member_id).get()

#         if not doc.exists:
#             st.error("⚠️ ユーザーが見つかりません。")
#         else:
#             user = doc.to_dict()
#             role = user.get("role", "student")

#             # --- パスワード検証 ---
#             if verify_password(password, user):
#                 st.session_state.update(
#                     {
#                         "login": True,
#                         "role": role,
#                         "member_id": member_id,
#                         "admin_name": user.get("name") if role == "admin" else None,
#                     }
#                 )
#                 st.success(f"✅ ログインしました（{role}）")
#                 st.rerun()
#             else:
#                 st.error("❌ パスワードが違います。")

# # ===============================
# # 🧭 管理者画面
# # ===============================
# elif st.session_state["login"] and st.session_state["role"] == "admin":
#     st.sidebar.title("📋 管理者メニュー")

#     # ✅ 未読数
#     unread = count_unread_messages()
#     inbox_label = f"受信ボックス（{unread}）" if unread > 0 else "受信ボックス"

#     options = ["生徒登録", "登録済みユーザー一覧", "チャット管理", inbox_label, "送信予約", "保護者未読一覧"]

#     # ✅ 前回選択状態復元
#     current = st.session_state.get("admin_mode", "生徒登録")
#     if isinstance(current, str) and current.startswith("受信ボックス"):
#         default_index = 3
#     else:
#         base_modes = ["生徒登録", "登録済みユーザー一覧", "チャット管理"]
#         default_index = base_modes.index(current) if current in base_modes else 0

#     selected_label = st.sidebar.radio("モードを選択してください", options, index=default_index)
#     mode = "受信ボックス" if selected_label.startswith("受信ボックス") else selected_label
#     st.session_state["admin_mode"] = mode

#     # -------------------------------
#     # 📂 生徒登録
#     # -------------------------------
#     if mode == "生徒登録":
#         st.markdown("#### 🔽 生徒情報と初期PW対応表をアップロード")
#         excel_file = st.file_uploader("📘 Excelファイル", type=["xlsx"])
#         csv_file = st.file_uploader("📄 CSVファイル", type=["csv"])
#         if excel_file and csv_file:
#             st.info("アップロードされたファイルを確認中...")
#             result = import_students_from_excel_and_csv(excel_file, csv_file)
#             if len(result) > 0:
#                 st.success("Firestoreへ登録が完了しました ✅")
#                 st.dataframe(result, use_container_width=True)
#             else:
#                 st.warning("⚠ 登録対象が見つかりません。")

#     # -------------------------------
#     # 📋 登録済みユーザー一覧
#     # -------------------------------
#     elif mode == "登録済みユーザー一覧":
#         st.markdown("#### 👥 Firestore 登録済みユーザー一覧")
#         df = fetch_all_users()
#         st.dataframe(df, use_container_width=True)

#     # -------------------------------
#     # 💬 チャット管理
#     # -------------------------------
#     elif mode == "チャット管理":
#         # 📩 受信BOXから遷移した場合
#         if st.session_state.get("just_opened_from_inbox", False):

#             target_id = st.session_state.get("selected_student_id")
#             target_name = st.session_state.get("selected_student_name", "")

#             if target_id:
#                 # ✅ 個人チャット用ステート固定
#                 st.session_state["target_type"] = "個人"
#                 st.session_state["target_student_id"] = target_id
#                 st.session_state["selected_student_id"] = target_id

#                 # ✅ 先にフラグを消して再描画
#                 st.session_state["just_opened_from_inbox"] = False
#                 st.session_state["admin_mode"] = "チャット管理"
#                 st.rerun()

#         # ✅ ここに来た時点で target_student_id がセット済み
#         selected_id = st.session_state.get("target_student_id")

#         if selected_id:
#             show_admin_chat(initial_student_id=selected_id)
#         else:
#             show_admin_chat()

#         # ✅ 余計な open_mode が残っている時の除去
#         if "open_mode" in st.session_state and st.session_state["open_mode"] == "admin_chat":
#             st.session_state["open_mode"] = None

#     # -------------------------------
#     # 📥 受信BOX
#     # -------------------------------

#     elif mode == "受信ボックス":
#         show_admin_inbox()

#         # 📌 受信BOX→チャット遷移（クリック1回で自動遷移）
#         if st.session_state.get("just_opened_from_inbox", False):
#             target_id = st.session_state.get("selected_student_id")
#             target_name = st.session_state.get("selected_student_name", "")

#             if target_id:
#                 # ✅ 個人チャット用ステート設定
#                 st.session_state["target_type"] = "個人"
#                 st.session_state["target_student_id"] = target_id
#                 st.session_state["admin_mode"] = "チャット管理"

#                 # ✅ 遷移フラグ解除して再描画
#                 st.session_state["just_opened_from_inbox"] = False
#                 st.rerun()


#     # elif mode == "受信ボックス":
#     #     show_admin_inbox()
#     #     # 📌 受信BOX→チャット遷移
#     #     if "open_mode" in st.session_state and st.session_state["open_mode"] == "admin_chat":
#     #         st.session_state["open_mode"] = None
#     #         st.session_state["admin_mode"] = "チャット管理"
#     #         st.session_state["just_opened_from_inbox"] = True
#     #         st.rerun()

#     # -------------------------------
#     # ⏰ 送信予約
#     # -------------------------------

#     elif mode == "送信予約":
#         show_schedule_main()

#     # -------------------------------
#     #  保護者未読一覧
#     # -------------------------------

#     elif mode == "保護者未読一覧":
#         show_unread_guardian_list() 


#     # -------------------------------
#     # 🚪 ログアウト
#     # -------------------------------
#     st.sidebar.markdown("---")
#     if st.sidebar.button("ログアウト"):
#         st.session_state["login"] = False
#         st.rerun()


# # ===============================
# # 🎓 生徒ページ
# # ===============================
# elif st.session_state["role"] == "student":
#     member_id = st.session_state["member_id"]
#     doc = USERS.document(member_id).get()
#     if not doc.exists:
#         st.error("⚠️ ユーザーデータが見つかりません。")
#     else:
#         # ===============================
#         # 🎓 生徒メニュー画面
#         # ===============================
#         if st.session_state["student_page"] == "menu":
#             st.title("🎓 学習メニュー")
#             st.markdown("以下から利用する機能を選択してください。")

#             new_flag = has_unread_messages(member_id)

#             # === 1行目：チャット・英作文・パスワード ===
#             col1, col2, col3 = st.columns(3)
#             with col1:
#                 if new_flag:
#                     st.markdown(
#                         """
#                         <div style="position:relative; display:inline-block;">
#                             <button style="
#                                 background-color:#1E90FF;
#                                 color:white;
#                                 font-size:18px;
#                                 font-weight:bold;
#                                 padding:12px 24px;
#                                 border:none;
#                                 border-radius:10px;
#                                 box-shadow:0 0 20px #1E90FF;
#                                 animation: pulse 1.5s infinite;
#                             ">💬 チャット　　　　<br>（未読あり）</button>
#                             <span style="
#                                 position:absolute;
#                                 top:2px;right:2px;
#                                 background:red;
#                                 color:white;
#                                 font-size:12px;
#                                 padding:2px 6px;
#                                 border-radius:50%;
#                             ">●</span>
#                         </div>
#                         <style>
#                         @keyframes pulse {
#                             0% { box-shadow: 0 0 5px #1E90FF; }
#                             50% { box-shadow: 0 0 25px #00BFFF; }
#                             100% { box-shadow: 0 0 5px #1E90FF; }
#                         }
#                         </style>
#                         """,
#                         unsafe_allow_html=True,
#                     )
#                     if st.button("▶ 開く", use_container_width=True, key="btn_chat_new"):
#                         st.session_state["student_page"] = "chat"
#                         st.rerun()
#                 else:
#                     if st.button("💬 チャット", use_container_width=True, key="btn_chat"):
#                         st.session_state["student_page"] = "chat"
#                         st.rerun()

#             with col2:
#                 if st.button("📝 英作文添削", use_container_width=True, key="btn_essay"):
#                     st.session_state["student_page"] = "essay"
#                     st.rerun()

#             with col3:
#                 if st.button("🔑 パスワード変更", use_container_width=True, key="btn_password"):
#                     st.session_state["student_page"] = "password"
#                     st.rerun()

#             # === 2行目：英会話トレーナー（全幅） ===
#             st.markdown("<br>", unsafe_allow_html=True)
#             if st.button("🎧 英会話トレーナー", use_container_width=True, key="btn_conversation"):
#                 st.session_state["student_page"] = "conversation"
#                 st.rerun()

#             # === 区切り線＋ログアウト ===
#             st.markdown("---")
#             if st.button("🚪 ログアウト", key="btn_logout"):
#                 st.session_state["login"] = False
#                 st.session_state["student_page"] = "menu"
#                 st.rerun()

#         # ===============================
#         # 💬 チャットページ
#         # ===============================
#         elif st.session_state["student_page"] == "chat":
#             show_back_button_top("back_chat_top")
#             grade, class_name = get_user_meta(member_id)
#             grade = grade or "未設定"
#             class_name = class_name or "未設定"
#             show_chat_page(member_id, grade, class_name)
#             show_back_button_bottom("back_chat_bottom")

#         # ===============================
#         # 📝 英作文添削ページ
#         # ===============================
#         elif st.session_state["student_page"] == "essay":
#             show_back_button_top("back_essay_top")
#             show_essay_corrector(member_id)
#             show_back_button_bottom("back_essay_bottom")

#         # ===============================
#         # 🎧 英会話トレーナーページ
#         # ===============================
#         elif st.session_state["student_page"] == "conversation":
#             show_back_button_top("back_conversation_top")
#             show_english_conversation()
#             show_back_button_bottom("back_conversation_bottom")

#         # ===============================
#         # 🔑 パスワード変更ページ
#         # ===============================
#         elif st.session_state["student_page"] == "password":
#             show_back_button_top("back_pw_top")
#             st.title("🔑 パスワード変更")
#             new_pw = st.text_input("新しいパスワード", type="password")
#             confirm_pw = st.text_input("新しいパスワード（確認）", type="password")

#             if st.button("変更を保存", key="save_password"):
#                 if not new_pw or not confirm_pw:
#                     st.warning("⚠ 両方の欄を入力してください。")
#                 elif new_pw != confirm_pw:
#                     st.error("❌ パスワードが一致しません。")
#                 else:
#                     update_user_password(member_id, new_pw)
#                     st.success("✅ パスワードを変更しました。")

#             show_back_button_bottom("back_pw_bottom")

