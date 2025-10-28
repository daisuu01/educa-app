# =============================================
# backup_rooms.py（Firestore「rooms」バックアップ）
# =============================================

import firebase_admin
from firebase_admin import credentials, firestore
import json, os
from datetime import datetime
from dotenv import load_dotenv

# --- .env の読み込み ---
load_dotenv()
firebase_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

# --- Firebase 初期化 ---
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_path)
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- rooms コレクションの全データを取得 ---
rooms_ref = db.collection("rooms")
docs = rooms_ref.stream()

backup_data = {}
for doc in docs:
    # ドキュメントIDと内容を保存
    backup_data[doc.id] = doc.to_dict()

# --- JSONに保存 ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"rooms_backup_{timestamp}.json"

with open(filename, "w", encoding="utf-8") as f:
    json.dump(backup_data, f, ensure_ascii=False, indent=2)

print(f"✅ Firestoreの「rooms」を {filename} にバックアップしました。")
