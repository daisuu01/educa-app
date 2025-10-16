# =============================================
# 🎓 educa-app.py（Firebase + Streamlit Cloud対応版）
# =============================================

import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials, firestore

# ---------------------------------------------------
# 1️⃣ Firebase 初期化（Secrets対応）
# ---------------------------------------------------
if not firebase_admin._apps:
    try:
        # Secrets から JSON 認証情報を読み込み（Streamlit Cloud対応）
        firebase_json = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
        cred = credentials.Certificate(firebase_json)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Firebase接続エラー: {e}")
        st.stop()

# Firestore クライアントを作成
db = firestore.client()

# ---------------------------------------------------
# 2️⃣ Streamlit ページ設定
# ---------------------------------------------------
st.set_page_config(page_title="Educa Chat", layout="wide")

st.title("💬 Educa Chat（塾内チャットアプリ）")
st.caption("Firebase Firestoreと連携したリアルタイムチャット")

# ---------------------------------------------------
# 3️⃣ Firestore メッセージ送信処理
# ---------------------------------------------------
st.subheader("メッセージを送信")

sender = st.selectbox("送信者", ["生徒", "講師"])
message = st.text_area("メッセージを入力してください")

if st.button("送信"):
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
# 4️⃣ Firestore メッセージ表示処理
# ---------------------------------------------------
st.subheader("📨 チャット履歴")

try:
    messages_ref = db.collection("messages").order_by("timestamp", direction=firestore.Query.DESCENDING)
    messages = messages_ref.stream()

    for msg in messages:
        data = msg.to_dict()
        sender = data.get("sender", "不明")
        text = data.get("message", "")
        st.write(f"**{sender}**：{text}")

except Exception as e:
    st.error(f"Firestore読み込みエラー: {e}")

# ---------------------------------------------------
# 5️⃣ 注意書き
# ---------------------------------------------------
st.caption("💡 データはFirebase Firestoreに保存されます。")
