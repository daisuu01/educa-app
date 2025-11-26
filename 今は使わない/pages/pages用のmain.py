# # =============================================
# # main.py（ログインだけ → pages へ遷移）
# # =============================================

# import streamlit as st
# import os
# from dotenv import load_dotenv
# import firebase_admin
# from firebase_admin import credentials, firestore
# from firebase_utils import verify_password

# # --- ページ設定 ---
# st.set_page_config(page_title="エデュカアプリログイン", layout="centered")

# # --- CSS（サイドバー完全非表示＋フェード殺し） ---
# st.markdown("""
# <style>
# /* ==== サイドバー完全非表示 ==== */
# [data-testid="stSidebarCollapsedControl"] {
#     display: none !important;
#     visibility: hidden !important;
#     opacity: 0 !important;
#     pointer-events: none !important;
# }

# /* サイドバー本体も非表示 */
# [data-testid="stSidebar"] {
#     display: none !important;
#     visibility: hidden !important;
# }

# /* サイドバーのナビだけ非表示 */
# nav[data-testid="stSidebarNav"] {
#     display: none !important;
# }

# /* サイドバーの三本線メニュー icon/hamburger だけ非表示 */
# svg[data-testid="icon-hamburger"],
# svg[data-testid="icon-chevron-left"],
# svg[data-testid="icon-chevron-right"] {
#     display: none !important;
# }

# /* ！！重要！！：ログインボタンまで消えないように修正 */
# button[aria-label="Menu"],       /* メニューボタンだけ */
# button[title="Menu"] {           /* メニューボタンだけ */
#     display: none !important;
# }

# /* メイン領域を全幅化 */
# div[data-testid="stAppViewContainer"] > section:first-child {
#     margin-left: 0 !important;
#     padding-left: 0 !important;
#     width: 100% !important;
#     max-width: 100% !important;
# }

# /* ==== スピナー非表示 & フェード殺し ==== */
# .stSpinner, div[data-testid="stSpinner"] { display: none !important; }
# [data-testid="stStatusWidget"] { display: none !important; }
# .stApp, .block-container { opacity: 1 !important; transition: none !important; }
# </style>


# """, unsafe_allow_html=True)

# # ================================
# # 🔥 Firebase 初期化（現状のコードを完全継承）
# # ================================
# load_dotenv()

# if not firebase_admin._apps:
#     try:
#         # --- Streamlit Cloud ---
#         if "firebase" in st.secrets:
#             firebase_config = dict(st.secrets["firebase"])
#             cred = credentials.Certificate(firebase_config)
#         else:
#             # --- ローカル ---
#             firebase_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "educa-app-firebase-adminsdk.json")
#             if not os.path.exists(firebase_path):
#                 raise FileNotFoundError(f"Firebase 認証ファイルが見つかりません: {firebase_path}")
#             cred = credentials.Certificate(firebase_path)

#         firebase_admin.initialize_app(cred)
#         db = firestore.client()

#     except Exception as e:
#         st.error(f"❌ Firebase 初期化エラー: {e}")
#         st.stop()
# else:
#     db = firestore.client()

# # ============================
# # Firestore USERS
# # ============================
# USERS = db.collection("users")

# # ============================
# # 🧠 状態
# # ============================
# if "login" not in st.session_state:
#     st.session_state["login"] = False
# if "role" not in st.session_state:
#     st.session_state["role"] = None
# if "member_id" not in st.session_state:
#     st.session_state["member_id"] = None

# # ============================
# # 🔐 ログイン画面
# # ============================
# # ============================
# # 🔐 ログイン画面（Enter 対応）
# # ============================
# if not st.session_state["login"]:

#     st.title("エデュカアプリログイン")

#     with st.form("login_form", clear_on_submit=False):
#         member_id = st.text_input("会員番号")
#         password = st.text_input("パスワード", type="password")
#         submitted = st.form_submit_button("ログイン")

#     if submitted:
#         doc = USERS.document(member_id).get()

#         if not doc.exists:
#             st.error("⚠ ユーザーが見つかりません。")

#         else:
#             user = doc.to_dict()

#             # 🔥 role の値正規化（重要）
#             role = user.get("role", "student")
#             role = str(role).replace('"', '').strip()   # ←←←★ この1行が重要！！

#             if verify_password(password, user):

#                 st.session_state["login"] = True
#                 st.session_state["role"] = role
#                 st.session_state["member_id"] = member_id

#                 st.success("ログイン成功")

#                 if role == "admin":
#                     st.switch_page("pages/1000_admin_menu.py")
#                 else:
#                     st.switch_page("pages/1_user_home.py")

#             else:
#                 st.error("❌ パスワードが違います。")