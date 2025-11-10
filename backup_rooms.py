# =============================================
# backup_rooms.py（Firestore「rooms」バックアップ）
# =============================================

import json
from datetime import datetime
from firebase_utils import db  # ✅ Firebase共通化
import os

# --- rooms コレクションの全データを取得 ---
rooms_ref = db.collection("rooms")
docs = rooms_ref.stream()

backup_data = {}
for doc in docs:
    backup_data[doc.id] = doc.to_dict()

# --- バックアップ保存先 ---
os.makedirs("backups", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = os.path.join("backups", f"rooms_backup_{timestamp}.json")

# --- JSON保存 ---
with open(filename, "w", encoding="utf-8") as f:
    json.dump(backup_data, f, ensure_ascii=False, indent=2)

print(f"✅ Firestore『rooms』を {filename} にバックアップしました。")
