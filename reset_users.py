import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

# --- Firebase 初期化 ---
load_dotenv()
firebase_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "educa-app-firebase-adminsdk.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- users コレクションを初期化 ---
def reset_users_collection():
    users_ref = db.collection("users")
    docs = users_ref.stream()
    count = 0
    for doc in docs:
        doc.reference.delete()
        count += 1
    print(f"✅ 削除完了: {count} 件のユーザーを削除しました。")

if __name__ == "__main__":
    confirm = input("⚠️ 本当に 'users' コレクションを初期化しますか？(y/n): ")
    if confirm.lower() == "y":
        reset_users_collection()
    else:
        print("キャンセルしました。")
