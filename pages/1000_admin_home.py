import streamlit as st
from firebase_admin import firestore

from admin_chat import show_admin_chat
from admin_inbox import show_admin_inbox, count_unread_messages
from firebase_utils import fetch_all_users, import_students_from_excel_and_csv
from admin_schedule import show_schedule_main
from unread_guardian_list import show_unread_guardian_list


# ---- ページ設定 ----
st.set_page_config(page_title="管理者メニュー", layout="wide")

# ---- CSS & JS（フェード・サイドバー・スピナー完全OFF）----
st.markdown("""<style>
.stApp::before {content: none !important; display:none !important;}
[data-testid="stStatusWidget"] {display:none !important;}
.stApp, .stApp > div, .block-container, div, section, main, header {
    opacity: 1 !important; transition: none !important;
}
[data-testid="stAppViewContainer"] {transition:none !important;}
.stSpinner, div[data-testid="stSpinner"] {display:none !important;}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {
    display:none !important;
}
</style>
<script>
function killOpacity(){
    document.querySelectorAll('*').forEach(el=>{
        const s=window.getComputedStyle(el);
        if(s.opacity && parseFloat(s.opacity)<1){el.style.opacity="1";}
    });
}
new MutationObserver(()=>killOpacity())
    .observe(document.body,{childList:true,subtree:true});
setInterval(killOpacity,200);
</script>
""", unsafe_allow_html=True)



# ---- 権限チェック ----
if not st.session_state.get("login"):
    st.switch_page("main.py")

if st.session_state.get("role") != "admin":
    st.error("⚠ 管理者のみアクセスできます")
    st.stop()

member_id = st.session_state.get("member_id")


# ---- モード管理（A方式の心臓部）----
if "admin_mode" not in st.session_state:
    st.session_state["admin_mode"] = "生徒登録"   # ← 初期画面


# ---- 未読数（リアルタイム）----
unread = count_unread_messages()


# ---- タブの見た目（押したら admin_mode を変えるだけ）----
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "👥 生徒登録",
    "📋 登録済みユーザー一覧",
    "💬 チャット管理",
    f"📥 受信ボックス（{unread}）",
    "⏰ 送信予約",
    "👀 保護者未読一覧",
])


# ---- タブ押されたときに admin_mode を切り替える ----
with tab1: st.session_state["admin_mode"] = "生徒登録"
with tab2: st.session_state["admin_mode"] = "ユーザー一覧"
with tab3: st.session_state["admin_mode"] = "チャット管理"
with tab4: st.session_state["admin_mode"] = "受信ボックス"
with tab5: st.session_state["admin_mode"] = "送信予約"
with tab6: st.session_state["admin_mode"] = "保護者未読"



# ---- 表示本体：admin_mode で中身を切り替える ----
mode = st.session_state["admin_mode"]

st.title(f"📋 管理者メニュー（{member_id}）")
st.markdown("---")


# =========================================
# 🎯 A方式：ここが重要
#     受信BOX → 開く ▶ を押した時の遷移
# =========================================
if st.session_state.get("redirect_to_admin_chat", False):
    st.session_state["admin_mode"] = "チャット管理"
    st.session_state["redirect_to_admin_chat"] = False
    # ここで mode を更新
    mode = "チャット管理"



# =========================================
# 🎯 admin_mode に応じて表示切り替え
# =========================================

# 👥 生徒登録
if mode == "生徒登録":
    excel_file = st.file_uploader("📘 Excel（名簿）", type=["xlsx"])
    csv_file = st.file_uploader("📄 CSV（初期PW）", type=["csv"])
    if excel_file and csv_file:
        st.info("処理中…")
        df = import_students_from_excel_and_csv(excel_file, csv_file)
        if len(df) > 0:
            st.success("Firestoreへ登録が完了しました！")
        else:
            st.warning("登録対象が見つかりませんでした。")
        st.dataframe(df, use_container_width=True)


# 📋 登録済みユーザー一覧
elif mode == "ユーザー一覧":
    st.dataframe(fetch_all_users(), use_container_width=True)


# 💬 チャット管理
elif mode == "チャット管理":
    show_admin_chat(
        initial_student_id=st.session_state.get("selected_student_id")
    )


# 📥 受信ボックス
elif mode == "受信ボックス":
    show_admin_inbox()


# ⏰ 送信予約
elif mode == "送信予約":
    show_schedule_main()


# 👀 保護者未読一覧
elif mode == "保護者未読":
    show_unread_guardian_list()







# # =============================================
# # pages/1000_admin_menu.py（タブ方式：最安定バージョン）
# # =============================================

# import streamlit as st
# from firebase_admin import firestore

# from admin_chat import show_admin_chat
# from admin_inbox import show_admin_inbox, count_unread_messages
# from firebase_utils import fetch_all_users, import_students_from_excel_and_csv
# from admin_schedule import show_schedule_main
# from unread_guardian_list import show_unread_guardian_list

# # ---- ページ設定 ----
# st.set_page_config(page_title="管理者メニュー", layout="wide")

# # ---- サイドバー完全非表示＋Running無効化＋フェード無効化 ----
# st.markdown("""
# <style>
# /* ===========================================
#    ① Streamlit の白フェード overlay を完全 OFF
#    =========================================== */

# /* ページ覆う白い膜 */
# .stApp::before {
#     content: none !important;
#     display: none !important;
#     background: none !important;
# }

# /* status widget も白膜を作るので削除 */
# [data-testid="stStatusWidget"] {
#     display: none !important;
#     visibility: hidden !important;
# }

# /* ===========================================
#    ② rerun 中にかかる 0.33 opacity を強制OFF
#    =========================================== */

# .stApp, .stApp > div, .block-container, div, section, main, header {
#     opacity: 1 !important;
#     transition: none !important;
# }

# /* container への fade-in 防止 */
# [data-testid="stAppViewContainer"] {
#     transition: none !important;
# }

# /* スピナーを完全非表示 */
# .stSpinner, div[data-testid="stSpinner"] {
#     display: none !important;
#     visibility: hidden !important;
# }

# /* サイドバー完全削除 */
# [data-testid="stSidebar"],
# [data-testid="stSidebarCollapsedControl"] {
#     display: none !important;
#     visibility: hidden !important;
# }
# </style>

# <script>
# // ===========================================
# // ③ Streamlit の opacity を JS で強制上書き
# // ===========================================

# function killOpacity() {
#     document.querySelectorAll('*').forEach(el => {
#         const style = window.getComputedStyle(el);
#         if (style.opacity && parseFloat(style.opacity) < 1) {
#             el.style.opacity = "1";
#         }
#     });
# }

# new MutationObserver(() => killOpacity())
#     .observe(document.body, { childList: true, subtree: true });

# setInterval(killOpacity, 200);
# </script>
# """, unsafe_allow_html=True)


# # ---- ログインチェック ----
# if not st.session_state.get("login"):
#     st.switch_page("main.py")

# if st.session_state.get("role") != "admin":
#     st.error("⚠ 管理者のみアクセスできます")
#     st.stop()

# member_id = st.session_state.get("member_id")

# # 🔥 ★追加：タブ切替のための内部状態
# if "_active_tab" not in st.session_state:
#     st.session_state["_active_tab"] = "👥 生徒登録"


# # --------------------------------------------
# # 🎉 管理者メニュー（タブ表示）
# # --------------------------------------------

# st.title(f"📋 管理者メニュー（{member_id}）")
# st.markdown("---")

# # 🔥 未読数（リアルタイム）
# unread = count_unread_messages()


# # 🔥 タブ定義
# tab_labels = [
#     "👥 生徒登録",
#     "📋 登録済みユーザー一覧",
#     "💬 チャット管理",
#     f"📥 受信ボックス（{unread}）",
#     "⏰ 送信予約",
#     "👀 保護者未読一覧"
# ]

# # 🔥 ★ここだけ追加：key を状態に紐付ける
# tabs = st.tabs(tab_labels)



# # ------------------------
# # 👥 生徒登録
# # ------------------------
# with tabs[0]:
#     st.header("👥 生徒登録")
#     excel_file = st.file_uploader("📘 Excel（名簿）", type=["xlsx"])
#     csv_file = st.file_uploader("📄 CSV（初期PW）", type=["csv"])

#     if excel_file and csv_file:
#         st.info("処理中…")
#         df = import_students_from_excel_and_csv(excel_file, csv_file)
#         if len(df) > 0:
#             st.success("Firestoreへ登録が完了しました！")
#         else:
#             st.warning("登録対象が見つかりませんでした。")
#         st.dataframe(df, use_container_width=True)


# # ------------------------
# # 📋 登録済みユーザー一覧
# # ------------------------
# with tabs[1]:
#     st.header("📋 登録済みユーザー一覧")
#     st.dataframe(fetch_all_users(), use_container_width=True)


# # ------------------------
# # 💬 チャット管理
# # ------------------------
# with tabs[2]:

#     # 🔥 受信ボックスから来たときだけ自動遷移
#     if st.session_state.get("redirect_to_admin_chat", False):
#         show_admin_chat(initial_student_id=st.session_state.get("selected_student_id"))
#         st.session_state["redirect_to_admin_chat"] = False
#         st.stop()

#     st.header("💬 チャット管理")
#     show_admin_chat()


# # ------------------------
# # 📥 受信BOX
# # ------------------------
# with tabs[3]:
#     st.header("📥 受信ボックス")
#     show_admin_inbox()


# # ------------------------
# # ⏰ 送信予約
# # ------------------------
# with tabs[4]:
#     st.header("⏰ 送信予約")
#     show_schedule_main()


# # ------------------------
# # 👀 保護者未読一覧
# # ------------------------
# with tabs[5]:
#     st.header("👀 保護者未読一覧")
#     show_unread_guardian_list()






