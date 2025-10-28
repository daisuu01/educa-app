# =============================================
# rebuild_rooms_structure.py
# Firestore「rooms」コレクションを削除→正しい構造で再構築
# =============================================

import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import os
from google.cloud.firestore_v1.base_document import DocumentSnapshot

# --- Firebase 初期化 ---
load_dotenv()
firebase_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

if not firebase_admin._apps:
    if not firebase_path or not os.path.exists(firebase_path):
        raise FileNotFoundError("❌ Firebase認証ファイルが見つかりません。")
    cred = credentials.Certificate(firebase_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()


# ==================================================
# 🔹 Firestore のコレクションを再帰的に削除
# ==================================================
def delete_collection(coll_ref, batch_size=50):
    docs = list(coll_ref.limit(batch_size).stream())
    deleted_count = 0

    for doc in docs:
        # サブコレクションも削除
        subcollections = doc.reference.collections()
        for subcoll in subcollections:
            delete_collection(subcoll, batch_size)

        doc.reference.delete()
        deleted_count += 1

    if deleted_count >= batch_size:
        return delete_collection(coll_ref, batch_size)


def delete_rooms():
    rooms_ref = db.collection("rooms")
    print("⚠️ Firestore: rooms コレクションを削除中...")
    delete_collection(rooms_ref)
    print("✅ rooms コレクションを削除しました。")


# ==================================================
# 🔹 新しい構造を再構築
# ==================================================
def rebuild_rooms():
    structure = {
        "class": {
            "10000": {},
            "10001": {},
        },
        "grade": {
            "中1": {},
            "中2": {},
            "中3": {},
            "高1": {},
            "高2": {},
            "高3": {},
        },
        "all": {},
        "personal": {},
    }

    rooms_ref = db.collection("rooms")

    for key, val in structure.items():
        print(f"▶ {key} を作成中...")
        key_doc = rooms_ref.document(key)
        key_doc.set({"initialized": True})

        if isinstance(val, dict) and val:
            for sub_key in val.keys():
                print(f"   ┗ {sub_key} を作成")
                sub_doc = key_doc.collection(sub_key).document("messages")
                sub_doc.set({"initialized": True})
                sub_doc.collection("items").document("_example").set({
                    "text": f"{key} - {sub_key} の初期メッセージ構造",
                    "sender": "system",
                })

    print("\n✅ Firestore「rooms」構造を再構築しました。")


# ==================================================
# 🔹 メイン処理
# ==================================================
if __name__ == "__main__":
    confirm = input("⚠️ Firestoreの「rooms」コレクションを削除して再構築します。よろしいですか？ (yes/no): ")
    if confirm.lower() == "yes":
        delete_rooms()
        rebuild_rooms()
    else:
        print("キャンセルしました。")
