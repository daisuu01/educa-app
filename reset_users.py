from firebase_utils import db  # ✅ Cloud / ローカル 両対応の共通接続
import sys


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
