# =============================================
# 🎓 educa-app.py（Firebase + Streamlit Cloud + 自動更新対応版）
# =============================================

import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------
# 1️⃣ 自動更新設定（5秒ごとに再読み込み）
# ---------------------------------------------------
# interval はミリ秒。5000 = 5秒間隔で再実行。
count = st_autorefresh(interval=5000, limit=None, key="chat_refresh")

# ---------------------------------------------------
# 2️⃣ Firebase 初期化（Secrets対応）
# ---------------------------------------------------
if not firebase_admin._apps:
    try:
        firebase_json = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
        cred = credentials.Certificate(firebase_json)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Firebase接続エラー: {e}")
        st.stop()

# Firestore クライアント作成
db = firestore.client()

# ---------------------------------------------------
# 3️⃣ ページ設定
# ---------------------------------------------------
st.set_page_config(page_title="Educa Chat", layout="wide")
st.title("💬 Educa Chat（塾内チャットアプリ）")
st.caption("Firebase Firestoreと連携したリアルタイムチャット")

# ---------------------------------------------------
# 4️⃣ メッセージ送信エリア
# ---------------------------------------------------
st.subheader("✉️ メッセージ送信")

col1, col2 = st.columns([1, 3])
with col1:
    sender = st.selectbox("送信者", ["生徒", "講師"])
with col2:
    message = st.text_input("メッセージを入力してください")

if st.button("送信", use_container_width=True):
    if message.strip():
        try:
            doc_ref = db.collection("messages").document()
            doc_ref.set({
                "sender": sender,
                "message": message,
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            st.success("メッセージを送信しました！")
        except Exception as e:
            st.error(f"Firestore書き込みエラー: {e}")
    else:
        st.warning("メッセージを入力してください。")

# ---------------------------------------------------
# 5️⃣ チャット履歴表示（最新順）
# ---------------------------------------------------
st.subheader("📨 チャット履歴（自動更新中）")

try:
    messages_ref = db.collection("messages").order_by(
        "timestamp", direction=firestore.Query.DESCENDING
    )
    messages = messages_ref.stream()

    for msg in messages:
        data = msg.to_dict()
        sender = data.get("sender", "不明")
        text = data.get("message", "")
        # --- 表示をわかりやすく整形 ---
        if sender == "講師":
            st.markdown(f"🧑‍🏫 **{sender}**：<span style='color:#1565C0'>{text}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"🎓 **{sender}**：<span style='color:#2E7D32'>{text}</span>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Firestore読み込みエラー: {e}")

# ---------------------------------------------------
# 6️⃣ 注意書き
# ---------------------------------------------------
st.caption("💡 チャットはFirebase Firestoreに保存され、5秒ごとに自動更新されます。")
