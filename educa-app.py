# ==========================================
# 🎓 塾チャットアプリ（Step 2：Firebase連携・安全版）
# ==========================================

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os

# --- Streamlit基本設定 ---
st.set_page_config(page_title="塾チャット", page_icon="🎓", layout="wide")
st.title("🎓 塾チャット（リアルタイム版）")

# --- Firebase秘密鍵の安全読込 ---
# 🔹 秘密鍵（JSONファイル）をアプリと同じフォルダに保存してください。
# 🔹 例： educa-app2-firebase-adminsdk-fbsvc-13377f7678.json
# 🔹 ファイル名を以下に正確に指定：
SERVICE_ACCOUNT_FILE = "educa-app2-firebase-adminsdk-fbsvc-13377f7678.json"

# --- Firebase初期化 ---
if not firebase_admin._apps:
    # ファイルが存在しない場合のチェック
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        st.error(f"Firebase秘密鍵が見つかりません: {SERVICE_ACCOUNT_FILE}")
        st.stop()
    cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- Firestoreコレクション設定 ---
CHAT_COLLECTION = "messages"

# --- メッセージ送信エリア ---
st.subheader("💬 メッセージ送信")
col1, col2 = st.columns([4, 1])
with col1:
    text = st.text_input("メッセージを入力してください")
with col2:
    role = st.selectbox("送信者", ["生徒", "先生"])

if st.button("送信"):
    if text.strip():
        db.collection(CHAT_COLLECTION).add({
            "role": role,
            "text": text,
            "timestamp": datetime.utcnow()
        })
        st.success("✅ メッセージを送信しました。")
        st.rerun()

# --- チャット履歴（最新順） ---
st.subheader("📜 チャット履歴（最新順）")
messages = db.collection(CHAT_COLLECTION).order_by(
    "timestamp", direction=firestore.Query.DESCENDING
).limit(50).stream()

for m in messages:
    msg = m.to_dict()
    ts = msg["timestamp"].strftime("%Y-%m-%d %H:%M:%S") if msg.get("timestamp") else ""
    icon = "🧑‍🏫" if msg.get("role") == "先生" else "👩‍🎓"
    st.markdown(f"{icon} **{msg.get('role')} ({ts})**：{msg.get('text')}")
